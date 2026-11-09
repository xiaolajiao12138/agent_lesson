"""
DAY 13 实战源码：脱离框架！纯原生手写 ReAct 智能体引擎
==============================================================================
【文件导读】：
    很多初学者一上来就学 LangChain，导致完全搞不清底层究竟是怎么调用工具的。
    本文件不使用任何第三方 Agent 封装库，只用 OpenAI 原生异步客户端 + Pydantic，
    手写 Thought（思考） -> Action（行动/调工具） -> Observation（观察结果）的闭环控制流。

【ReAct 核心架构与底层逻辑】：
    1. 什么是 ReAct？
       ReAct = Reasoning（推理） + Acting（行动）。
       大模型不仅仅是问答机器人，而是一个“决策大脑”：
       - 它看到用户问题 -> 发现缺少信息 -> 决定调用工具 (Action)；
       - 我们在后端执行该工具，把真实结果传回大模型 (Observation)；
       - 大模型看到结果后再次思考 (Thought)，如果还需要工具就继续调，直到得出结论。

    2. OpenAI Function Calling 的协议规范：
       - 注册阶段：我们向大模型传入 tools 参数（由 Pydantic 生成的 JSON Schema）；
       - 决策阶段：大模型返回 message.tool_calls，携带函数名和入参 JSON；
       - 反馈阶段：后端执行函数后，必须以 role="tool" 且携带 tool_call_id 把结果追加回上下文！
         大模型正是通过这个 tool_call_id 将工具结果与之前的调用请求进行一一对应的。

【运行要求】：
    pip install openai pydantic
    python day13_native_react_agent.py
==============================================================================
"""

import json
import os
import asyncio
from typing import List, Dict, Any, Callable
from pydantic import BaseModel, Field

# ==============================================================================
# 第一步：定义外部工具（Tools）入参模型
# ==============================================================================
# 使用 Pydantic 定义每个工具函数需要的参数规范，大模型会根据字段的 description 自动生成正确的实参

class WeatherQueryArgs(BaseModel):
    """【查询天气工具的入参规范】"""
    city: str = Field(description="城市名称，例如：'北京', '杭州'")
    unit: str = Field(default="celsius", description="温度单位：celsius(摄氏度) 或 fahrenheit(华氏度)")

class CalculatorArgs(BaseModel):
    """【数学计算器工具的入参规范】"""
    expression: str = Field(description="合法的数学算式字符串，例如：'(24 * 9 / 5) + 32'")

# 实际执行工具函数（模拟外部微服务 API）
async def get_weather(city: str, unit: str = "celsius") -> str:
    """模拟外部天气微服务接口调用"""
    await asyncio.sleep(0.3) # 模拟网络 I/O 延迟
    return json.dumps({
        "city": city,
        "temperature": "25",
        "unit": unit,
        "condition": "晴转多云",
        "humidity": "45%"
    }, ensure_ascii=False)

async def calculate(expression: str) -> str:
    """数学计算执行器（避免大模型直接算数出现的幻觉和低级计算错误）"""
    try:
        # 在受限命名空间中安全执行基本算术计算
        result = eval(expression, {"__builtins__": None}, {})
        return json.dumps({"expression": expression, "result": result}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"计算表达式失败: {str(e)}"}, ensure_ascii=False)

# ==============================================================================
# 第二步：将本地函数注册进工具字典，并自动提取 JSON Schema 规范
# ==============================================================================

# 工具注册表：键为函数名，值为本地执行指针与传给大模型的规范描述
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "get_weather": {
        "func": get_weather,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取特定城市的当前实时气象与温度信息",
                # 核心：使用 Pydantic 的 model_json_schema() 自动生成 OpenAPI 规范参数描述
                "parameters": WeatherQueryArgs.model_json_schema()
            }
        }
    },
    "calculate": {
        "func": calculate,
        "schema": {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "进行精确的算术运算（如加减乘除、乘方、单位换算）",
                "parameters": CalculatorArgs.model_json_schema()
            }
        }
    }
}

# ==============================================================================
# 第三步：手写 ReAct 调度器循环 (Agent Engine)
# ==============================================================================

class NativeReActAgent:
    """纯手写原生 ReAct 智能体引擎"""

    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        # 严谨的 System Prompt 指引大模型按步骤思考并决策工具调用
        self.system_prompt = (
            "你是一个高智商、讲求事实依据的 AI 智能体。\n"
            "在面对用户的复合问题时，请遵循 ReAct 范式：\n"
            "1. 思考（Thought）：分析目前掌握的信息是否充足，还需要什么数据；\n"
            "2. 行动（Action）：主动调用提供的工具去获取外部客观真实数据；\n"
            "3. 观察（Observation）：根据工具返回的数据再次思考，直到能推导出最终结论；\n"
            "严禁凭空猜测事实数据，当工具返回结果后，请综合所有信息给用户简洁清晰的最终答复。"
        )

    async def execute_task(self, user_query: str, max_turns: int = 6) -> str:
        """
        核心调度逻辑：
        维护一个 messages 会话上下文列表，在 while/for 循环中与大模型交替通信。
        max_turns 用于安全熔断，防止 Agent 陷入死循环耗尽 Token。
        """
        from openai import AsyncOpenAI
        client = AsyncOpenAI()

        # 初始化会话历史记录
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query}
        ]

        # 提取全部注册工具的 JSON Schema 定义
        tools_spec = [item["schema"] for item in TOOL_REGISTRY.values()]

        print("\n" + "=" * 60)
        print(f"[任务启动] 用户提出需求: {user_query}")
        print("=" * 60)

        # 进入 ReAct 推理-行动多轮循环
        for turn in range(1, max_turns + 1):
            print(f"\n--- [第 {turn} 轮思考与推理] ---")

            # 1. 携带完整历史与工具描述，请求大模型进行决策
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools_spec,
                tool_choice="auto" # 模型自主判断：是需要调工具，还是直接输出结果
            )

            assistant_msg = response.choices[0].message
            # 将模型的本轮回复压入历史上下文
            messages.append(assistant_msg.model_dump(exclude_none=True))

            # 2. 判断模型是否发起了外部工具调用 (Action)
            if assistant_msg.tool_calls:
                for call in assistant_msg.tool_calls:
                    fn_name = call.function.name
                    fn_args = json.loads(call.function.arguments)
                    call_id = call.id

                    print(f"[Agent 决定调用工具]: {fn_name}")
                    print(f"   传入参数: {fn_args}")

                    # 3. 在本地工具注册表中找到对应函数并执行
                    if fn_name in TOOL_REGISTRY:
                        executor = TOOL_REGISTRY[fn_name]["func"]
                        observation = await executor(**fn_args)
                    else:
                        observation = json.dumps({"error": f"未找到名为 {fn_name} 的工具"})

                    print(f"[外部工具返回/Observation]: {observation}")

                    # 4. 【关键步骤】：将工具执行结果包装成 role='tool' 追加回上下文
                    # 必须携带对应的 tool_call_id，这样大模型才能知道这条结果属于哪一次调用
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": observation
                    })

                # 工具执行完毕，继续进入下一轮循环，让模型根据 Observation 进行后续推导
                continue

            # 5. 如果没有发起 tool_calls，说明大模型认为已收集到全部必要信息，输出最终答复
            print(f"\n[Agent 推理完成，输出最终答复]:")
            return assistant_msg.content or "任务已完成。"

        return "[警告] 已达到最大允许思考步数（6轮），触发保护性熔断退出。"


# ==============================================================================
# 本地运行与演示测试
# ==============================================================================

async def simulate_demo():
    """在无 API KEY 时的离线模拟演示流程"""
    print("\n[离线模拟演示] 模拟 ReAct Agent 执行全链路流转：")
    print("----------------------------------------------------------------------")
    print("【第一轮】：用户询问杭州当前气温并换算华氏度")
    print("  -> Agent 思考：我不知道当前实时温度，必须先查天气。")
    print("  -> Agent 决策工具调用：get_weather(city='杭州')")
    obs1 = await get_weather("杭州")
    print(f"  -> 外部工具返回 (Observation): {obs1}")
    
    print("\n【第二轮】：大模型收到气温数据 25°C")
    print("  -> Agent 思考：得到温度 25 度，现在需要利用计算公式 (25 * 9 / 5) + 32 计算华氏度。")
    print("  -> Agent 决策工具调用：calculate(expression='(25 * 9 / 5) + 32')")
    obs2 = await calculate("(25 * 9 / 5) + 32")
    print(f"  -> 外部工具返回 (Observation): {obs2}")

    print("\n【第三轮】：大模型收到计算结果 77.0")
    print("  -> Agent 思考：全部事实数据齐备，整合回复用户。")
    print("  -> 最终交付答案：杭州当前气温为 25°C，按公式换算后对应为 77°F。")
    print("----------------------------------------------------------------------")

if __name__ == "__main__":
    test_question = "请帮我查一下杭州现在的气温，并利用计算器算出如果换算成华氏度是多少？公式：(摄氏度 * 9 / 5) + 32"

    if not os.getenv("OPENAI_API_KEY"):
        print("\n" + "=" * 60)
        print("[提示] 检测到当前系统未设置 OPENAI_API_KEY 环境变量。")
        print("为了让你彻底看懂 ReAct 的每一步流转，现启动离线模拟链路：")
        print("=" * 60)
        asyncio.run(simulate_demo())
    else:
        try:
            agent = NativeReActAgent()
            final_answer = asyncio.run(agent.execute_task(test_question))
            print(f"\n最终交付结果:\n{final_answer}")
        except Exception as e:
            print(f"[执行异常]: {e}")
