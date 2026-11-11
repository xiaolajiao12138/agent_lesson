"""
================================================================================
DAY 02 实战源码：Pydantic v2 强类型校验与数据契约（大模型时代的“Python 版 Zod”）
================================================================================
文件定位与重要性：
    在传统 Web 开发中，参数校验错了只会返回 400 错误；
    而在 AI Agent 开发中，大模型经常会“幻觉”胡乱返回字段。
    Pydantic v2 是现代 Python 的绝对核心基石（底层由 Rust 编写，速度极快）。
    它的两大神级核心用途：
    1. 【严格把关】：强行校验大模型吐出来的 JSON，一旦格式不对立即报错或自动修正；
    2. 【自动生成契约】：自动把 Python 类转换成标准的 JSON Schema，喂给大模型作为 Function Calling 的“工具说明书”！

前端概念镜像对照：
    - Pydantic BaseModel <======> TypeScript Interface / Zod Schema (z.object({...}))
    - Pydantic Field(...)  <======> Zod 字段约束 (z.string().min(3).describe("..."))
    - @field_validator     <======> Zod 自定义校验 (z.refine((val) => ...))
    - model_json_schema()  <======> zod-to-json-schema

运行方式：
    python day02_pydantic_validation.py
"""

import json
from enum import Enum
from typing import List, Optional

# 从 pydantic 核心库导入三大法宝（进阶为四大法宝）：
# 1. BaseModel: 所有数据模型的基类（相当于所有 Schema 的祖宗模具）
# 2. Field: 字段约束工具（设置默认值、最大最小值、大模型描述文本）
# 3. field_validator: 单字段自定义校验装饰器（针对某个特定字段安检）
# 4. model_validator: 全局/跨字段联动校验装饰器（针对整张卡片多字段联动安检）
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

# ==============================================================================
# 1. 枚举类型定义（对标 TypeScript 的 enum 或字面量联合类型）
# ==============================================================================


# TS 对照: type PriorityLevel = 'low' | 'medium' | 'high' | 'critical';
# 在 Python 中同时继承 str 和 Enum 的小妙招：
# 这样它既是枚举，又是一个标准的字符串，未来转成 JSON 时会自动变成 "low" 字符串，不需要繁琐地写 .value！
class PriorityLevel(str, Enum):
    """
    任务优先级枚举类
    """

    LOW = "low"  # 低优先级
    MEDIUM = "medium"  # 中等优先级（默认值）
    HIGH = "high"  # 高优先级
    CRITICAL = "critical"  # 紧急核心任务


# ==============================================================================
# 2. 定义 Pydantic 数据模型（对标 TS 的 Zod Schema: z.object({...})）
# ==============================================================================


class AgentTask(BaseModel):
    """
    智能体任务卡片数据契约模型 (Data Contract)

    【核心知识点】：
    每个字段的定义格式为：
    字段名: 类型 = Field(默认值或..., 约束条件1, 约束条件2, description="说明")
    """

    # 1. 必填字段 (Required Field)
    # 核心细节：这里的三个点 ... (Ellipsis 省略号) 在 Pydantic 中专门表示【此字段必须传入，绝不能漏传】！
    # 对标 TS: task_id: string; (非可选属性)
    task_id: str = Field(
        ..., description="任务唯一ID标识，通常由系统自动生成（如 TASK_001）"
    )

    # 2. 带有长度约束的字符串
    # min_length=3, max_length=50 相当于对标 TS Zod 的: z.string().min(3).max(50)
    title: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="任务简要标题，长度必须在 3 到 50 个字符之间",
    )

    # 3. 带有默认值的枚举字段
    # 如果外部没有传 priority 字段，自动使用默认值 PriorityLevel.MEDIUM ("medium")
    # 对标 TS: priority?: PriorityLevel; (默认赋值 'medium')
    priority: PriorityLevel = Field(
        default=PriorityLevel.MEDIUM, description="任务执行优先级，默认为 medium"
    )

    # 4. 复杂列表字段与【默认工厂函数 default_factory】(极其高频的面试与实战避坑点！)
    # ⚠️ 为什么不写 default=[] 而是写 default_factory=list？
    # 避坑解释：在 Python 中，如果直接写 default=[]，所有生成的对象会共享同一个列表内存引用！
    # 导致对象 A 修改列表，对象 B 也会跟着被污染；
    # 写 default_factory=list 代表：每次实例化新对象时，都全新执行一次 list() 生成独立空列表！
    assigned_tools: List[str] = Field(
        default_factory=list,
        description="分配给该任务调用的工具名称列表，例如 ['web_search', 'calculator']",
    )

    # 5. 数字范围校验（ge 与 le）
    # ge = Greater than or equal (大于等于 >= 5)
    # le = Less than or equal (小于等于 <= 300)
    # 对标 TS Zod: z.number().min(5).max(300)
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="任务最大等待执行超时时间（单位：秒，必须介于 5 到 300 之间）",
    )

    # 6. 可选字段 (Optional Field)
    # Optional[str] 等同于 str | None
    # 默认值是 None，说明调用方不传这个字段也不会报错
    # 对标 TS: extra_notes?: string | null;
    extra_notes: str = Field(
        default=None, description="额外补充说明或备注信息（可选字段，默认为空）"
    )

    # ==========================================================================
    # 自定义字段校验钩子（对标 TS Zod 的 .refine((val) => boolean)）
    # ==========================================================================
    # 作用：内置的 min_length、ge 无法满足复杂的业务逻辑时，手写校验规则
    @field_validator("title")
    @classmethod
    def validate_title_content(cls, v: str) -> str:
        """
        参数说明：
            cls: 当前类自身 (AgentTask)
            v: 外部传入的该字段值 (title 的值)
        返回值：
            必须把经过清洗/校验后的合法值 return 出去！
        """
        # 业务规则：防止用户或者大模型只传了一堆纯空格（如 "    "）蒙混过关
        cleaned_title = v.strip()
        if not cleaned_title:
            # 抛出 ValueError 会被 Pydantic 自动捕获并包装成规范的 ValidationError
            raise ValueError("任务标题不能仅由无意义的空白字符组成！")

        # 返回清洗过首尾空格后的干净字符串
        return cleaned_title

    # ==========================================================================
    # 核心大招：模型级全量校验器（对标 TS Zod: z.object({...}).refine(allData => ...)）
    # ==========================================================================
    # 【与 @field_validator 的最大区别】：
    # 1. @field_validator 只能看到单个字段（参数是 v）
    # 2. @model_validator(mode="after") 能一口气看到【所有字段】（参数是 self 实例！）
    # 适用场景：多字段互相制约联动（比如：密码与确认密码一致、紧急任务限制超时时间）
    @model_validator(mode="after")
    def validate_cross_field_rules(self):
        """
        此时所有基础字段都已经过初步解析，self 身上已经拥有了完整的属性！

        【业务联动规则】：
        如果该智能体任务被标记为最高紧急等级（CRITICAL），
        为了防止大模型卡死引发系统雪崩，它的超时时间（timeout_seconds）绝不能超过 60 秒！
        """
        if self.priority == PriorityLevel.CRITICAL and self.timeout_seconds > 60:
            raise ValueError(
                f"【多字段联动违规】紧急任务 (critical) 为了防止系统卡死，超时时间绝不能超过 60 秒！当前传入了: {self.timeout_seconds}s"
            )

        # ⚠️ 规则要求：校验完成后，必须把 self 原样 return 出去！
        return self


# ==============================================================================
# 3. 核心实战演示：为什么开发 AI Agent 必须使用 Pydantic？
# ==============================================================================


def demonstrate_pydantic_for_agents():
    print("=" * 70)
    print("【1. 成功解析与对象化】（类似 Zod.parse 校验合法数据）")
    print("=" * 70)

    # 模拟从前端表单、或者从大模型返回的原始 JSON 字典数据
    raw_data = {
        "task_id": "TASK_2026_001",
        "title": "分析 Q3 财报并提取风险点",
        "priority": "high",  # 会被自动映射并验证为 PriorityLevel.HIGH
        "assigned_tools": ["pdf_parser", "calculator"],
        "timeout_seconds": 60,
        # extra_notes 没传，会自动填充默认值 None
    }

    # 使用双星号 ** 将字典解构传参（还记得 lesson04 学过的字典解包吗？）
    # 这一步内部会自动触发全量类型转换和边界检查
    task_instance = AgentTask(**raw_data)

    # 验证完成后，直接享受面向对象属性点语法访问（VSCode 自带完美类型提示！）
    print(f"[通过] 任务实例化成功！")
    print(f"   任务编号: {task_instance}")
    print(f"   任务标题: {task_instance.title}")
    print(
        f"   优先级对象: {task_instance.priority} (其底层字符串值: {task_instance.priority.value})"
    )
    print(f"   工具列表: {task_instance.assigned_tools}")
    print(f"   超时限制: {task_instance.timeout_seconds}s")
    print(f"   可选备注: {task_instance.extra_notes}")

    # 导出序列化（两个神级方法，极其常用）：
    # 1. model_dump(): 转成普通的 Python 字典 (dict)
    # 2. model_dump_json(): 转成标准的 JSON 字符串 (类似 JSON.stringify)
    dict_result = task_instance.model_dump()
    json_result = task_instance.model_dump_json(indent=2)
    print(f"\n[序列化导出] 一键转换为标准 JSON 字符串:\n{json_result}")
    print(f"{dict_result}")

    print("\n" + "=" * 70)
    print("【2. 异常拦截机制】（当大模型发疯、返回残缺或非法数据时）")
    print("=" * 70)

    # 故意构造一份违规数据，模拟大模型“抽风幻觉”生成了不符合要求的参数：
    # 1. 漏掉了必填的 task_id
    # 2. title 只有 2 个字，违反了 min_length=3
    # 3. timeout_seconds 传了 9999，违反了 le=300
    invalid_llm_output = {"title": "太短", "timeout_seconds": 9999}

    try:
        print("正在尝试解析非法数据...")
        AgentTask(**invalid_llm_output)
    except ValidationError as err:
        # Pydantic 的报错信息极其详细，包含发生错误的字段路径、期望值与实际值！
        print(f"[精准拦截！] Pydantic 成功拦截了大模型的不合规输出！")
        print(f"错误详情统计共包含 {err.error_count()} 处违规：\n")
        # 遍历具体的错误字段与原因
        for item in err.errors():
            loc = " -> ".join(str(x) for x in item["loc"])
            msg = item["msg"]
            print(f"   -> 字段 [{loc}]: {msg}")

    print("\n" + "=" * 70)
    print("【3. 全量跨字段联动拦截】（@model_validator 多字段互相制约校验）")
    print("=" * 70)

    # 模拟数据：每个字段单独看都完全合规！
    # - task_id 填了（合规）
    # - title 长度够长（合规）
    # - timeout_seconds 是 180s（处于 5~300 范围内，合规！）
    # ⚠️ 但是！两者组合在一起违规了：
    # priority 是 critical（紧急任务），按业务规则超时时间绝不能超过 60 秒！
    conflict_data = {
        "task_id": "TASK_CRITICAL_999",
        "title": "核心支付系统宕机紧急修复任务",
        "priority": "critical",
        "timeout_seconds": 180,  # 违反了 @model_validator 设定的不超过 60 秒规则！
    }

    try:
        print("正在尝试解析【单字段看似合规、组合起来违规】的联动数据...")
        AgentTask(**conflict_data)
    except ValidationError as err:
        print(f"[精准拦截！] @model_validator 成功捕获到了跨字段业务逻辑违规！")
        for item in err.errors():
            msg = item["msg"]
            print(f"   -> 违规详情: {msg}")

    print("\n" + "=" * 70)
    print("【4. 终极大招：零成本自动生成给大模型的 Function Calling 工具说明书！】")
    print("=" * 70)
    """
    【为什么所有 Agent 框架（LangChain / OpenAI / LlamaIndex）都用 Pydantic？】
    因为大模型的 Tool Calling 参数要求必须传入一份标准的 JSON Schema。
    在前端你可能需要费劲引入三方转换库；
    而在 Pydantic 中，只需调用一个方法：类名.model_json_schema()！
    它会自动把你上面写的所有类型、min_length、description 全部编译成大模型能看懂的官方文档！
    """
    tool_schema = AgentTask.model_json_schema()

    print("直接传递给 OpenAI / DeepSeek 的 tools[i].function.parameters 契约规范如下：")
    print(json.dumps(tool_schema, indent=2, ensure_ascii=False))


# ==============================================================================
# 主执行入口（还记得 lesson04 学过的 if __name__ == '__main__' 吗？）
# ==============================================================================
if __name__ == "__main__":
    demonstrate_pydantic_for_agents()
