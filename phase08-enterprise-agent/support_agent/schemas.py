"""企业实战第 1 课｜请求校验与响应结构，衔接 Day 21 的 BaseModel、Field 和 Annotated。

阅读顺序为可复用类型、请求基类、具体请求体、响应模型。
models.py 描述数据库表，本文件描述接口允许输入和输出哪些字段。
BaseModel 提供解析与校验，ConfigDict 配置模型行为，Field 配置单个字段。
这些类在 FastAPI 参数或返回类型中使用时，会参与校验及 OpenAPI 文档生成。
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .models import Status

# Annotated[原始类型, 约束元数据] 让同一组校验可以在多个模型中复用。
# StringConstraints 专用于字符串处理，Field 还可配置数值范围、默认值和字段描述。
Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Keyword = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]


class InputModel(BaseModel):
    # 请求体中出现 tenant_id、role 等额外字段时返回 422。
    """所有请求体共用的校验基类。

    继承 BaseModel 获得校验能力，子类继续继承 model_config。
    extra='forbid' 会拒绝未声明字段，FastAPI 会把请求校验错误转换为 422。
    相关选项 extra='ignore' 会忽略额外字段，extra='allow' 会保留额外字段。
    model_config 是 Pydantic 约定的配置名称，本类可以只定义配置，再由子类声明业务字段。
    """
    model_config = ConfigDict(extra="forbid")


class QuestionInput(InputModel):
    """问答和建单共用的 JSON 请求体，question 必填。

    Question 是上方 Annotated 字符串类型的别名，包含去空白及长度约束。
    继承 InputModel 后，客户端额外提交 tenant_id 或 role 会被拒绝。
    业务身份仍由 security.py 从凭证中解析，输入校验与身份授权各自负责对应环节。
    """
    question: Question


class ReviewInput(InputModel):
    """审批请求体，将 decision 限定为两个终态字符串。

    Literal 校验具体可选值，str 主要约束类型，Status 枚举集中定义业务状态。
    请求通过校验后，路由用 Status(payload.decision) 转为业务枚举。
    """
    decision: Literal["approved", "rejected"]


class DocumentInput(InputModel):
    """知识库写入的请求体，包含内容、匹配关键词和可见范围。

    title、body 的字符串约束会先去掉首尾空白，再检查长度。
    list[Keyword] 检查每个元素，Field(min_length=1, max_length=12) 检查列表项数。
    Field 没有设置 default，因此 keywords 是必填项。
    visibility 有默认值 'tenant'，调用方省略它时使用默认值。
    model_dump() 会把已校验模型转为 Python 字典，model_dump_json() 会生成 JSON 文本。
    """
    title: ShortText
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    # 外层 Field 限制关键词个数，Keyword 限制每个关键词的字符长度。
    keywords: list[Keyword] = Field(min_length=1, max_length=12)
    visibility: Literal["tenant", "reviewer"] = "tenant"


class TicketView(BaseModel):
    # model_validate 可从 ORM 对象属性读取字段，响应中只包含以下字段。
    """工单响应结构，筛选允许返回给前端的字段。

    from_attributes=True 允许 model_validate(ticket) 读取 ORM 对象属性。
    model_validate() 接收 Python 字典或对象，model_validate_json() 接收 JSON 文本或字节。
    Status 会将数据库状态字符串校验为枚举，datetime 会参与响应时间序列化。
    """
    model_config = ConfigDict(from_attributes=True)

    # 以下字段都是响应契约，只声明类型且没有默认值时为必填。
    id: str
    question: str
    status: Status
    created_at: datetime


class EventView(BaseModel):
    """单条审计事件的响应结构，使用 ORM 属性生成接口数据。

    它只暴露执行者、动作和创建时间，路由会返回 list[EventView]。
    响应模型的字段声明控制输出内容，数据库模型中还可以保留内部字段。
    """
    model_config = ConfigDict(from_attributes=True)

    actor_id: str
    action: str
    created_at: datetime


class Citation(BaseModel):
    """回答的出处，包含文档编号、标题和引用正文。

    它作为 KnowledgeAnswer 的嵌套模型，方便前端展示引用及追溯来源。
    当前摘录来自获授权的知识库文档正文。
    """
    source_id: str
    title: str
    excerpt: str


class KnowledgeAnswer(BaseModel):
    """问答的统一结果，route 指示回答或建议转人工。

    route='answer' 时当前业务会同时提供 message 和 Citation。
    route='transfer' 时 citation 使用默认值 None，由前端另行决定是否发起建单请求。
    Citation | None 表示允许两种类型，'= None' 进一步表示调用方可以省略这个字段。
    """
    route: Literal["answer", "transfer"]
    message: str
    citation: Citation | None = None
