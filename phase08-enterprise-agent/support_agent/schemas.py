"""企业实战第 1 课｜请求参数校验和对外响应契约。"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .models import Status

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Keyword = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]


class InputModel(BaseModel):
    # 请求体中出现 tenant_id、role 等额外字段时返回 422。
    model_config = ConfigDict(extra="forbid")


class QuestionInput(InputModel):
    question: Question


class ReviewInput(InputModel):
    decision: Literal["approved", "rejected"]


class DocumentInput(InputModel):
    title: ShortText
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    keywords: list[Keyword] = Field(min_length=1, max_length=12)
    visibility: Literal["tenant", "reviewer"] = "tenant"


class TicketView(BaseModel):
    # model_validate 可从 ORM 对象属性读取字段，响应中只包含以下字段。
    model_config = ConfigDict(from_attributes=True)

    id: str
    question: str
    status: Status
    created_at: datetime


class EventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    actor_id: str
    action: str
    created_at: datetime


class Citation(BaseModel):
    source_id: str
    title: str
    excerpt: str


class KnowledgeAnswer(BaseModel):
    route: Literal["answer", "transfer"]
    message: str
    citation: Citation | None = None
