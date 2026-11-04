"""
DAY 02 实战源码：Pydantic v2 强类型与数据契约（大模型的“Zod”）
文件说明：
    在 Agent 开发中，我们必须强迫大模型按严格的 JSON 输出，或者验证用户给工具的传参。
    Pydantic v2 是 Python 现代开发的基石。如果你熟悉前端的 Zod / TypeScript Interface，
    学习 Pydantic 会有 100% 的即视感。
运行方式：python day02_pydantic_validation.py
"""

import json
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

# ==============================================================================
# 1. 枚举与字段约束（类似 TS 中的 enum 或字面量联合类型 'low' | 'medium' | 'high'）
# ==============================================================================

class PriorityLevel(str, Enum):
    """任务优先级枚举，继承 str 便于直接序列化为字符串"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# ==============================================================================
# 2. 定义 Pydantic 模型（类似 TS 中的 Zod Schema: z.object({...})）
# ==============================================================================

class AgentTask(BaseModel):
    """
    智能体任务卡片数据模型
    
    字段解析说明：
    - task_id: 任务唯一标识字符串
    - title: 任务标题，最小长度 3，最大长度 50
    - priority: 优先级，必须属于 PriorityLevel
    - assigned_tools: 该任务需要调用的工具名称列表
    - timeout_seconds: 超时时间，默认 30 秒，约束在 5 到 300 秒之间
    - metadata: 可选的元数据字典，类似 TS 的 Record<string, any> | undefined
    """
    task_id: str = Field(
        ..., # ... 代表该字段必填 (Required)
        description="任务唯一ID，由系统自动生成"
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="任务简要标题"
    )
    priority: PriorityLevel = Field(
        default=PriorityLevel.MEDIUM,
        description="任务执行优先级，默认为 medium"
    )
    assigned_tools: List[str] = Field(
        default_factory=list, # 空列表的默认工厂函数，避免引用类型共享陷阱
        description="分配给该任务的工具列表，如 ['web_search', 'calculator']"
    )
    timeout_seconds: int = Field(
        default=30,
        ge=5,  # greater than or equal: >= 5
        le=300, # less than or equal: <= 300
        description="任务最大等待执行超时时间（秒）"
    )
    extra_notes: Optional[str] = Field(
        default=None,
        description="额外补充备注说明"
    )

    # 类似 Zod 的 .refine() 自定义校验钩子
    @field_validator("title")
    @classmethod
    def validate_title_content(cls, v: str) -> str:
        """检查标题是否包含违法字符或空格过长"""
        if v.strip() == "":
            raise ValueError("标题不能仅由空格组成！")
        return v.strip()

# ==============================================================================
# 3. 为什么 Agent 开发极度依赖 Pydantic？—— 自动生成 JSON Schema！
# ==============================================================================

def demonstrate_pydantic_for_agents():
    print("=== 1. 数据校验与实例化（类似 Zod.parse） ===")
    
    # 正确的数据样本
    raw_data = {
        "task_id": "TASK_2026_001",
        "title": "分析 Q3 财报并提取风险点",
        "priority": "high",
        "assigned_tools": ["pdf_parser", "calculator"],
        "timeout_seconds": 60
    }

    # 类似 const task = AgentTaskSchema.parse(raw_data)
    task_instance = AgentTask(**raw_data)
    print(f"数据校验成功！对象属性访问: task_id={task_instance.task_id}, 优先级={task_instance.priority.value}")

    # 导出为标准 JSON 字符串（类似 JSON.stringify）
    json_output = task_instance.model_dump_json(indent=2)
    print(f"序列化为 JSON:\n{json_output}")

    print("\n=== 2. 异常捕获机制（当大模型抽风返回了非法字段时） ===")
    invalid_data = {
        "task_id": "TASK_002",
        "title": "短", # 触发 min_length=3 校验失败
        "timeout_seconds": 9999 # 触发 le=300 校验失败
    }
    try:
        AgentTask(**invalid_data)
    except Exception as e:
        print(f"已拦截非法模型输出！捕获到校验异常详情:\n{e}")

    print("\n=== 3. 核心能力：一键生成给大模型的 Function Calling 参数描述规范 ===")
    # 大模型的 tools 参数需要一个标准的 JSON Schema
    # 在前端可能需要 zod-to-json-schema，而在 Python 中，Pydantic 内置原生支持！
    json_schema = AgentTask.model_json_schema()
    print("用于提供给大模型 tools[i].function.parameters 的标准契约规范:")
    print(json.dumps(json_schema, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    demonstrate_pydantic_for_agents()
