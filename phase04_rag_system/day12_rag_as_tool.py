"""
DAY 12 实战源码：多工具路由调度 —— 大模型如何精准点名并调用不同函数？
==============================================================================
【文件导读与核心解答】：
    用户疑问：
    "大模型返回了 tool_calls，我们怎么知道要去调用哪一个对应的本地函数？
     比如怎么知道去调天气函数，还是调知识库函数？"

    本文件带你彻底透视真相：
    1. 注册多个工具说明书（规章制度库 + 实时天气 + 数学计算器）；
    2. 建立本地【函数派发字典】（TOOL_REGISTRY，对标前端的 Action Handlers）；
    3. 大模型返回时，读取 tool_call.function.name（模型点名的名字）；
    4. 像查字典一样，动态命中并执行对应的 Python 函数！
==============================================================================
"""

import json
import os
import sys
from typing import Any

from dotenv import load_dotenv

# 确保 Windows 控制台正常支持 UTF-8 编码，防止字符集报错
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 确保父级目录路径正常加载
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.append(current_dir)

load_dotenv(os.path.join(parent_dir, ".env"), override=True)
load_dotenv(os.path.join(current_dir, ".env"), override=True)

OPENAI_API_KEY = (
    os.getenv("api_key")
    or os.getenv("OPENAI_API_KEY")
    or "sk-7c29a50f89c958db7015b7c49984767782d86dcc5844b3e4e767a8e22b655345"
)
OPENAI_BASE_URL = (
    os.getenv("base_url")
    or os.getenv("OPENAI_BASE_URL")
    or "https://sub2api.starysp.top/v1"
)
DEFAULT_MODEL = os.getenv("mode") or "gpt-6.1-sol"

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["OPENAI_BASE_URL"] = OPENAI_BASE_URL

from day09_vector_rag import SimpleVectorRAG
from openai import OpenAI
from pydantic import BaseModel, Field

# ==============================================================================
# 第一步：编写 3 个完全不同的本地业务函数
# ==============================================================================

# 初始化全局向量库实例
rag_system = SimpleVectorRAG()


def search_company_policy_tool(query: str, top_k: int = 2) -> str:
    """工具 1：从企业向量知识库中语义检索制度规范"""
    print(f"   >>> [本地执行] 触发知识库检索函数，关键词: '{query}'")
    chunks = rag_system.semantic_search(query, top_k=top_k)
    if not chunks:
        return "企业知识库中未检索到任何相关条款。"
    return "\n\n".join(
        [
            f"【切片 ID: {c['id']} | 分类: {c['category']}】\n{c['content']}"
            for c in chunks
        ]
    )


def get_weather_tool(city: str) -> str:
    """工具 2：查询指定城市的实时气温与天气状态"""
    print(f"   >>> [本地执行] 触发天气查询函数，城市: '{city}'")
    # 模拟外部天气 API 响应
    mock_weather_data = {
        "北京": {"temp": "12℃", "condition": "晴朗少云", "wind": "西北风 3 级"},
        "深圳": {"temp": "26℃", "condition": "多云转阵雨", "wind": "微风"},
        "杭州": {"temp": "18℃", "condition": "阴天", "wind": "东南风 2 级"},
    }
    info = mock_weather_data.get(
        city, {"temp": "20℃", "condition": "晴", "wind": "微风"}
    )
    return json.dumps({"city": city, **info}, ensure_ascii=False)


def calculate_tool(expression: str) -> str:
    """工具 3：高精度数学表达式计算器"""
    print(f"   >>> [本地执行] 触发数学计算器函数，算式: '{expression}'")
    try:
        # 在安全受限命名空间下执行算术计算
        res = eval(expression, {"__builtins__": None}, {})
        return json.dumps({"expression": expression, "result": res}, ensure_ascii=False)
    except Exception as err:
        return json.dumps({"error": f"计算失败: {err!s}"}, ensure_ascii=False)


# ==============================================================================
# 第二步：使用 Pydantic 生成各个工具的入参 Schema 规范（出具说明书）
# ==============================================================================


class PolicyArgs(BaseModel):
    query: str = Field(description="企业制度相关的问题或关键词，如 '出差住宿标准'")
    top_k: int = Field(default=2, description="召回切片数")


class WeatherArgs(BaseModel):
    city: str = Field(description="需要查询天气的城市中文名称，如 '北京', '深圳'")


class CalculateArgs(BaseModel):
    expression: str = Field(description="合法的算术运算表达式，如 '500 * 3 + 120'")


# 将 3 个工具的说明书打包成一个列表，给大模型过目
ALL_TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "search_company_policy",  # 👈 名字 1
            "description": "专用于检索公司内部人事请假、加班调休、差旅报销及技术开发安全合规等官方制度规定。",
            "parameters": PolicyArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",  # 👈 名字 2
            "description": "获取指定城市的实时天气预报、当前气温和风向信息。",
            "parameters": WeatherArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",  # 👈 名字 3
            "description": "进行加减乘除、乘方等精确的数学四则运算。",
            "parameters": CalculateArgs.model_json_schema(),
        },
    },
]

# ==============================================================================
# 第三步：核心关键！建立本地【函数路由字典】（对标前端的 Action Handlers）
# ==============================================================================

# 这是一个将【工具名字字符串】映射到【真实 Python 函数】的查找表
TOOL_REGISTRY: dict[str, Any] = {
    "search_company_policy": search_company_policy_tool,  # 名字 1 -> 执行函数 1
    "get_weather": get_weather_tool,  # 名字 2 -> 执行函数 2
    "calculate": calculate_tool,  # 名字 3 -> 执行函数 3
}

# ==============================================================================
# 第四步：多工具动态路由调度器（揭秘如何判断调哪个）
# ==============================================================================


def multi_tool_agent_gateway(user_input: str, max_retries: int = 2) -> str:
    """
    智能网关：
    1. 把所有可用工具提交给大模型；
    2. 大模型根据自然语言意图，决定【不调用】或【点名调用哪一个工具】；
    3. 我们读取 tool_call.function.name，在 TOOL_REGISTRY 字典中匹配真实函数执行！
    4. 加入网络自动重试机制，防止瞬时网络波动。
    """
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

    messages = [
        {
            "role": "system",
            "content": (
                "你是一个功能强大的企业多功能助理。\n"
                # "你可以根据需要调用外部工具来协助用户：\n"
                # "- 涉及公司政策制度，调用 search_company_policy；\n"
                # "- 询问外部气温天气，调用 get_weather；\n"
                # "- 涉及数学计算换算，调用 calculate；\n"
                # "- 普通打招呼或通用闲聊，直接礼貌回答，不要触发任何工具。"
            ),
        },
        {"role": "user", "content": user_input},
    ]

    print(f"\n{'=' * 60}")
    print(f"[用户提问]: '{user_input}'")
    print(f"{'-' * 60}")

    # 1. 带着 3 个工具说明书请求大模型（带网络重试保护）
    msg = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                tools=ALL_TOOLS_SPEC,
                tool_choice="auto",
            )
            msg = response.choices[0].message
            break
        except Exception as err:
            if attempt == max_retries:
                return f"网络请求遇到波动，重试失败: {err}"
            print(f"   [提示] 网络连接抖动，正在进行第 {attempt} 次自动重试...")
            import time

            time.sleep(1)

    # 2. 判断模型是否发起了工具调用
    print(msg.model_dump_json(indent=2))
    if msg.tool_calls:
        # 模型返回的 tool_calls 是一个列表（可能包含一个或多个调用意图）
        for tool_call in msg.tool_calls:
            # 核心回答你的疑问：从这里拿到模型点名的函数名字符串！
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            print(f"[模型决策] 点名要求调用工具: 【{function_name}】")
            print(f"   模型生成的入参数据: {function_args}")

            # 核心解答：利用字典查找表，动态拿到真正的函数对象！
            if function_name in TOOL_REGISTRY:
                target_function = TOOL_REGISTRY[function_name]
                # 执行本地函数，将入参解包传进去
                observation = target_function(**function_args)
            else:
                observation = f"错误：本地未注册名为 '{function_name}' 的工具。"

            print(f"   [工具返回结果/Observation]: {observation[:60]}...")

            # 将工具结果追加回历史，让模型综合生成最终答复
            messages.append(msg.model_dump(exclude_none=True))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(observation),
                }
            )

        # 3. 将执行结果回传给模型，产出最终自然语言答案
        try:
            final_res = client.chat.completions.create(
                model=DEFAULT_MODEL, temperature=0.0, messages=messages
            )
            return final_res.choices[0].message.content
        except Exception as err:
            return f"获取最终总结回答时网络异常: {err}"

    # 如果模型没有调工具，直接输出普通回答
    print("[模型决策] 判定为普通会话，无需动用任何工具，直接回答。")
    return msg.content


# ==============================================================================
# 第五步：四大典型场景现场演练
# ==============================================================================

if __name__ == "__main__":
    test_cases = [
        "你好，请问你是谁？今天感觉怎么样？",  # 场景 1：闲聊（不调工具）
        "我下周去深圳出差，请问一线城市的住宿报销标准是多少？",  # 场景 2：触发制度库 (search_company_policy)
        "深圳今天天气怎么样？穿短袖会冷吗？",  # 场景 3：触发天气查询 (get_weather)
        "如果我出差 3 天，每天房费 480 元，总房费是多少钱？",  # 场景 4：触发计算器 (calculate)
    ]

    for query in test_cases:
        try:
            answer = multi_tool_agent_gateway(query)
            print(f"[最终答复]:\n{answer}\n")
        except Exception as e:
            print(f"[执行异常]: {e}\n")
