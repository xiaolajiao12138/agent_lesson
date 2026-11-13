import asyncio
import json
import os
import sys

from pydantic import BaseModel, Field

# 动态引入项目根目录的通用配置
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from config import DEFAULT_MODEL, get_async_openai_client
except ImportError:
    from openai import AsyncOpenAI

    def get_async_openai_client():
        return AsyncOpenAI(
            api_key=os.getenv(
                "OPENAI_API_KEY",
                "sk-7c29a50f89c958db7015b7c49984767782d86dcc5844b3e4e767a8e22b655345",
            ),
            base_url=os.getenv("OPENAI_BASE_URL", "https://sub2api.starysp.top/v1"),
        )

    DEFAULT_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-6.1-sol")


async def get_weather(city: str, unit: str = "celsius") -> str:  # 获取城市天气工具方法
    await asyncio.sleep(0.3)  # 模拟网络延迟
    return json.dumps(
        {
            "city": city,
            "temperature": "25",
            "unit": unit,
            "condition": "晴转多云",
            "humidity": "45%",
        },
        ensure_ascii=False,
    )


async def calcuate(express: str) -> str:
    await asyncio.sleep(0.5)
    try:
        result = eval(express, {"__builtins__": None}, {})
        return json.dumps({"express": express, "result": result}, ensure_ascii=False)
    except Exception as e:
        print(e)


class WeatherArgs(BaseModel):  # 获取城市天气参数定义
    city: str = Field(description="城市名称，例如：北京，深圳")
    unit: str = Field(default="celsius", description="温度单位：celsius摄氏度或fahrenheit华氏度")


class CalculateArgs(BaseModel):  # s算术参数定义
    express: str = Field(description="合法的数学算式字符串，例如：（24*9/5）+32")


##工具注册表
TOOL_REGISTRY: dict[str, dict[str, any]] = {
    "get_weather": {
        "func": get_weather,  ##方法
        "schema": {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取特定城市的天气和气温",
                "parameters": WeatherArgs.model_json_schema(),
            },
        },
    },
    "calculate": {
        "func": calcuate,
        "schema": {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "进行精准的算术运算",
                "parameters": CalculateArgs.model_json_schema(),
            },
        },
    },
}


class NativeReactAgent:
    def __init__(self, model_name: str = None):
        self.agent_name = model_name or DEFAULT_MODEL  # 往self添加模型版本
        # 添加防幻觉系统
        self.system_promt = (
            "你是一个高智商、讲求事实依据的 AI 智能体。\n"
            "在面对用户的复合问题时，请遵循 ReAct 范式：\n"
            "1. 思考（Thought）：分析目前掌握的信息是否充足，还需要什么数据；\n"
            "2. 行动（Action）：主动调用提供的工具去获取外部客观真实数据；\n"
            "3. 观察（Observation）：根据工具返回的数据再次思考，直到能推导出最终结论；\n"
            "严禁凭空猜测事实数据，当工具返回结果后，请综合所有信息给用户简洁清晰的最终答复。"
        )

    async def execute_task(self, query: str, max_turns: int = 6) -> str:
        client = get_async_openai_client()
        messages = [  # 初始化对话列表
            {"role": "system", "content": self.system_promt},
            {"role": "user", "content": query},
        ]
        tool_schema = [item["schema"] for item in TOOL_REGISTRY.values()]
        # 进入ReAct推理  -行动多轮循环
        for trun in range(1, max_turns + 1):  # 从1开始循环一直到6结束，后面+1是为了让最后一位到6
            response = await client.chat.completions.create(
                model=self.agent_name,
                messages=messages,
                tools=tool_schema,
                tool_choice="auto",  # 模型自主判断是需要调用工具还是直接输出
            )
            assisten_msg = response.choices[0].message
            messages.append(
                assisten_msg.model_dump(exclude_none=True)
            )  # 将大模型返回的消息再次压入到messages中
            if assisten_msg.tool_calls:  # 判断是否调用工具
                for call in assisten_msg.tool_calls:  # 是调用工具，那么就循环调用的工具的方法
                    fn_name = call.function.name  # 获取大模型返回的工具名
                    fn_args = json.loads(call.function.arguments)  # 获取大模型填写的参数
                    callid = call.id  # 获取大模型的返回的这一轮对话的idjisuan
                    if fn_name in TOOL_REGISTRY:  # 如果大模型返回的工具名在注册表中
                        executor = TOOL_REGISTRY[fn_name]["func"]  # 获取对应的方法
                        observation = await executor(
                            **fn_args
                        )  # 调用对应的方法，并将大模型返回的参数传给方法中
                    else:
                        observation = json.dumps({"error": f"未找到名为{fn_name}的工具"})
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": callid,  # 上一轮大模型对话的id
                            "content": observation,
                        }
                    )
                continue  # 跳出本次循环，进入下一轮循环
            print("\n【推理完成，输出最终答案】")
            return assisten_msg.content
        return "已达到最大允许思考步数，触发保护规则"


if __name__ == "__main__":
    # 主调用口   提出问题进行方法调用
    question = "请帮我查一下杭州现在的气温，并利用计算器算出如果换算成华氏度是多少？公式：(摄氏度 * 9 / 5) + 32"

    try:
        agent = NativeReactAgent()  # 调用类init，添加初始化防幻觉系统
        answer = asyncio.run(
            agent.execute_task(question)
        )  # 调用主函数  asyncio.run只能传入一个主函数
        print(f"最终交付的结果{answer}")
    except Exception as e:
        print(e)
