"""
DAY 13 实战源码：脱离框架！纯原生手写 ReAct 智能体引擎
文件说明：
    很多初学者一上来就学 LangChain，导致完全搞不清底层是怎么调工具的。
    本文件不使用任何三方 Agent 框架，只用 OpenAI 原生异步客户端 + Pydantic，
    手写 Thought -> Action -> Observation 的闭环控制流。
运行要求：
    pip install openai pydantic
    python day13_native_react_agent.py
"""

import json
import asyncio
from typing import List, Dict, Any, Callable
from pydantic import BaseModel, Field
from openai import AsyncOpenAI

# ==============================================================================
# 第一步：定义外部工具（Tools）入参模型
# ==============================================================================

class WeatherQueryArgs(BaseModel):
    """查询天气工具的入参规范"""
    city: str = Field(description="城市名称，例如：'北京', '杭州'")
    unit: str = Field(default="celsius", description="温度单位：celsius(摄氏度) 或 fahrenheit(华氏度)")

class CalculatorArgs(BaseModel):
    """数学计算器工具的入参规范"""
    expression: str = Field(description="合法的数学算式字符串，例如：'(24 * 9 / 5) + 32'")

# 实际执行工具函数（模拟外部真实服务）
async def get_weather(city: str, unit: str = "celsius") -> str:
    """模拟外部天气微服务"""
    # 模拟网络异步耗时
    await asyncio.sleep(0.3)
    return json.dumps({
        "city": city,
        "temperature": "25",
        "unit": unit,
        "condition": "晴转多云",
        "humidity": "45%"
    }, ensure_ascii=False)

async def calculate(expression: str) -> str:
    """数学计算执行器"""
    try:
        # 在受限命名空间中执行基本算术计算
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
# 第三步：手写 ReAct 调度器循环
# ==============================================================================

class NativeReActAgent:
    """纯手写 ReAct 智能体引擎"""

    def __init__(self, model_name: str = "gpt-4o"):
        self.client = AsyncOpenAI() # 读取环境变量中的 OPENAI_API_KEY
        self.model_name = model_name
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
        核心执行逻辑：
        维护一个 messages 数组，在 while 循环中与大模型交替通信。
        """
        # 初始化消息上下文（相当于会话状态存储）
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query}
        ]

        # 整理所有工具的 JSON Schema 定义传给模型
        tools_spec = [item["schema"] for item in TOOL_REGISTRY.values()]

        print(f"\n=======================================================")
        print(f"🚀 [任务启动] 用户提出需求: {user_query}")
        print(f"=======================================================")

        for turn in range(1, max_turns + 1):
            print(f"\n--- [第 {turn} 轮思考与推理] ---")

            # 1. 带着目前的全部上下文和工具列表，请求大模型
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools_spec,
                tool_choice="auto" # 模型自主决定：是调工具，还是直接回复
            )

            assistant_msg = response.choices[0].message
            # 将模型的回答压入上下文
            messages.append(assistant_msg.model_dump(exclude_none=True))

            # 2. 判断模型是否发起了工具调用 (Action)
            if assistant_msg.tool_calls:
                for call in assistant_msg.tool_calls:
                    fn_name = call.function.name
                    fn_args = json.loads(call.function.arguments)
                    call_id = call.id

                    print(f"🔍 [Agent 决定调用工具]: {fn_name}")
                    print(f"   传入参数: {fn_args}")

                    # 3. 本地执行工具函数
                    if fn_name in TOOL_REGISTRY:
                        executor = TOOL_REGISTRY[fn_name]["func"]
                        observation = await executor(**fn_args)
                    else:
                        observation = json.dumps({"error": f"找不到工具 {fn_name}"})

                    print(f"📥 [外部工具返回/Observation]: {observation}")

                    # 4. 关键：将工具的执行结果以 role='tool' 追加回上下文
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": observation
                    })

                # 工具执行完毕，继续进入下一轮循环，让模型根据 Observation 进行下一步推理
                continue

            # 5. 如果没有发起 tool_calls，说明大模型认为已经得到最终结论
            print(f"\n🎯 [Agent 推理完成，输出最终答复]:")
            return assistant_msg.content or "任务已完成。"

        return "⚠️ 警告：已达到最大允许思考步数，强制熔断退出。"

# ==============================================================================
# 测试运行
# ==============================================================================

if __name__ == "__main__":
    agent = NativeReActAgent()
    # 提一个必须先查天气、再根据查到的摄氏度套入公式换算成华氏度的复合问题
    test_question = "请帮我查一下杭州现在的气温，并利用计算器算出如果换算成华氏度是多少？公式：(摄氏度 * 9 / 5) + 32"
    
    # 启动异步任务
    try:
        final_answer = asyncio.run(agent.execute_task(test_question))
        print(f"\n最终交付结果:\n{final_answer}")
    except Exception as e:
        print(f"执行异常（请检查网络与 OPENAI_API_KEY 配置）: {e}")
