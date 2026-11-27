"""统一成功响应：字段与前端 Axios transform 保持一致。"""
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "操作成功"
    data: T | None = None
    request_id: str | None = None
