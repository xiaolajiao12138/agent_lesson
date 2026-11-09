"""
DAY 07 实战源码：大模型强制结构化输出（Structured Outputs 与防幻觉）
==============================================================================
【文件导读】：
    大模型默认是生成纯文本的“文字接龙机器”。但在 Agent 开发中，下游往往是数据库或前端组件，
    我们需要模型 100% 返回合法、且严格符合 Schema 的 JSON。
    如果让大模型自由发挥，它常常会夹带 markdown 标记（如 ```json ... ```）或缺漏字段导致 JSON.parse 崩溃。
    本文件演示现代大模型的 Structured Outputs 特性。

【核心技术原理】：
    1. Constrained Decoding（语法受限解码）：
       大模型不是“生成完文本后再用正则检查”，而是在生成每一个 Token 的瞬间，
       根据 JSON Schema 动态将不合规的 Token 概率强制压制为 0，从而实现 100% 格式合规。
    2. Pydantic 自动编译为 JSON Schema：
       开发人员无需手写繁琐的 JSON Schema，只需定义 Pydantic BaseModel，SDK 会自动完成协议转换。

【运行要求】：
    pip install openai pydantic
    python day07_structured_output.py
==============================================================================
"""

import json
import os
import sys
from typing import List, Optional
from pydantic import BaseModel, Field

# 动态引入项目根目录的通用配置
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from config import get_openai_client, DEFAULT_MODEL
except ImportError:
    # 兼容独立运行
    from openai import OpenAI
    def get_openai_client():
        return OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "sk-7c29a50f89c958db7015b7c49984767782d86dcc5844b3e4e767a8e22b655345"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://sub2api.starysp.top/v1")
        )
    DEFAULT_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-6.1-sol")

# ==============================================================================
# 1. 定义我们期望从非结构化文本中精准抽取的契约结构 (Pydantic Schema)
# ==============================================================================

class UserProfileExtract(BaseModel):
    """
    【用户画像提取契约模型】
    模型会根据类名、Docstring、字段名以及 Field 的 description 来精准理解每个字段的业务语义。
    """
    user_name: str = Field(description="用户姓名")
    current_role: str = Field(description="当前职业岗位角色，如前端工程师、产品经理等")
    skills: List[str] = Field(description="用户掌握的专业技能列表（数组结构）")
    years_of_experience: int = Field(description="工作年限，必须提取为纯整型数字")
    is_interested_in_ai: bool = Field(description="是否对 AI 或 Agent 表现出浓厚兴趣，布尔值")
    
    # ge (greater than or equal) 与 le (less than or equal) 
    # 会被自动转化为 JSON Schema 的 {"minimum": 0.0, "maximum": 1.0}，约束模型评分范围
    confidence_score: float = Field(
        description="大模型对提取信息完整度的自我置信度评分 (0.0 到 1.0)",
        ge=0.0,
        le=1.0
    )

# ==============================================================================
# 2. 调用大模型并强制应用结构化解析
# ==============================================================================

def extract_structured_data(raw_user_bio: str) -> UserProfileExtract:
    """
    使用 client.beta.chat.completions.parse 强制模型遵循 Pydantic Schema。
    模型返回的对象会被 SDK 自动反序列化为 UserProfileExtract 强类型实例。
    """
    client = get_openai_client()

    print(f"原始非结构化口语文本:\n---\n{raw_user_bio}\n---")
    print(f"正在请求大模型 [{DEFAULT_MODEL}] 进行信息结构化提炼（应用语法受限解码）...")

    # 核心调用：使用 beta 命名空间下的 parse 方法
    completion = client.beta.chat.completions.parse(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "你是一个极其严格的信息抽取助手。请仔细阅读用户提供的个人自述，提取出规范的人物画像。"
            },
            {
                "role": "user",
                "content": raw_user_bio
            }
        ],
        # 【关键参数】：将 Pydantic 类直接传入 response_format，SDK 会自动将其编译为严格的 JSON Schema
        response_format=UserProfileExtract,
    )

    # 提取模型解析后的强类型对象
    parsed_result: UserProfileExtract = completion.choices[0].message.parsed
    return parsed_result


# ==============================================================================
# 3. 本地运行与演示验证
# ==============================================================================

if __name__ == "__main__":
    # 模拟一段典型的非结构化口语文本（真实场景可能来自用户注册问卷、客服聊天记录或简历）
    mock_bio = (
        "大家好！我叫小陈，目前在一家外企做前端开发，主要技术栈是 React、TypeScript 和 Next.js，"
        "不知不觉在这个领域已经搬砖整整 4 年了。最近大模型特别火，我目前正在全力自学 Agent 开发和 LangGraph，"
        "希望今年内能转型成为一名优秀的 AI 智能体全栈工程师！"
    )

    print("\n" + "=" * 60)
    print("=== 大模型结构化输出抽取实战（真实 API 调用模式）===")
    print("=" * 60)

    try:
        profile = extract_structured_data(mock_bio)

        # 打印强类型对象的字段值
        print("\n[提取成功] 获得强类型 Pydantic 对象：")
        print(f"姓名: {profile.user_name}")
        print(f"当前岗位: {profile.current_role}")
        print(f"技能清单: {profile.skills}")
        print(f"从业年限: {profile.years_of_experience} 年")
        print(f"是否对 AI 感兴趣: {'是' if profile.is_interested_in_ai else '否'}")
        print(f"提取置信度: {round(profile.confidence_score * 100, 1)}%")

        # 导出为干净的标准 JSON，供前端页面或数据库存储
        print("\n[序列化导出] 格式化输出供前端 Vue/React 直接渲染的 JSON:")
        print(profile.model_dump_json(indent=2))

    except Exception as e:
        print(f"[调用异常]: {e}")
