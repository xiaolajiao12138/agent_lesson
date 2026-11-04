"""
DAY 07 实战源码：大模型强制结构化输出（Structured Outputs 与防幻觉）
文件说明：
    大模型默认是生成纯文本的“文字接龙机器”。但在 Agent 开发中，下游往往是数据库或前端组件，
    我们需要模型 100% 返回合法、且严格符合 Schema 的 JSON。
    本文件演示现代大模型（OpenAI/Gemini/DeepSeek）的 Structured Outputs 特性。
运行要求：
    pip install openai pydantic
    python day07_structured_output.py
"""

import json
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI

# ---------------------------------------------------------------------------
# 1. 定义我们期望从非结构化文本中精准抽取的契约结构
# ---------------------------------------------------------------------------

class UserProfileExtract(BaseModel):
    """从非结构化履历或用户自我介绍中，精准提炼的用户画像结构体"""
    user_name: str = Field(description="用户姓名")
    current_role: str = Field(description="当前职业岗位角色")
    skills: List[str] = Field(description="用户掌握的专业技能列表")
    years_of_experience: int = Field(description="工作年限，必须为纯数字")
    is_interested_in_ai: bool = Field(description="是否对 AI 或 Agent 表现出浓厚兴趣")
    confidence_score: float = Field(
        description="大模型对提取信息置信度自我评分 (0.0 到 1.0)",
        ge=0.0,
        le=1.0
    )

# ---------------------------------------------------------------------------
# 2. 调用大模型并强制应用结构化解析
# ---------------------------------------------------------------------------

def extract_structured_data(raw_user_bio: str) -> UserProfileExtract:
    """
    使用 client.beta.chat.completions.parse 强制模型遵循 Pydantic Schema
    大模型底层会通过语法受限解码（Constrained Decoding）强行保证返回合法 JSON。
    """
    client = OpenAI() # 自动读取环境变量中的 OPENAI_API_KEY

    print(f"原始非结构化文本:\n---\n{raw_user_bio}\n---")
    print("正在请求大模型进行信息结构化提炼...")

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06", # 支持 Structured Outputs 的模型
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
        # 核心：将 Pydantic 类直接传入 response_format，SDK 会自动将其编译为严格的 JSON Schema
        response_format=UserProfileExtract,
    )

    # 模型返回的对象已经被直接反序列化为 UserProfileExtract 强类型实例
    parsed_result: UserProfileExtract = completion.choices[0].message.parsed
    return parsed_result

if __name__ == "__main__":
    # 模拟一段典型的非结构化口语文本
    mock_bio = (
        "大家好！我叫小陈，目前在一家外企做前端开发，主要技术栈是 React、TypeScript 和 Next.js，"
        "不知不觉在这个领域已经搬砖整整 4 年了。最近大模型特别火，我目前正在全力自学 Agent 开发和 LangGraph，"
        "希望今年内能转型成为一名优秀的 AI 智能体全栈工程师！"
    )

    try:
        profile = extract_structured_data(mock_bio)
        print("\n提取成功！得到强类型 Pydantic 对象：")
        print(f"姓名: {profile.user_name}")
        print(f"当前岗位: {profile.current_role}")
        print(f"技能清单: {profile.skills}")
        print(f"从业年限: {profile.years_of_experience} 年")
        print(f"是否对 AI 感兴趣: {'是' if profile.is_interested_in_ai else '否'}")
        print(f"提取置信度: {profile.confidence_score * 100}%")

        # 导出为干净的 JSON，可直接供前端页面使用
        print("\n格式化输出给前端使用的纯 JSON 数据:")
        print(profile.model_dump_json(indent=2))

    except Exception as e:
        print(f"调用出现错误（请确保已在环境变量中配置合法的 OPENAI_API_KEY）: {e}")
