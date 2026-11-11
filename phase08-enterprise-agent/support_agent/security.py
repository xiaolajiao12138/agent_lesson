"""企业实战第 4 课｜身份由服务端解析，业务查询用可信身份限定资源范围。"""

from dataclasses import dataclass
from hashlib import sha256
import os
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, TypeAdapter


@dataclass(frozen=True)
class Actor:
    user_id: str
    tenant_id: str
    role: Literal["customer", "reviewer"]


class IdentityInput(BaseModel):
    token: str = Field(min_length=24, max_length=256, pattern=r"^[a-zA-Z0-9_-]+$")
    user_id: str = Field(min_length=1, max_length=64)
    tenant_id: str = Field(min_length=1, max_length=64)
    role: Literal["customer", "reviewer"]


def load_identities() -> dict[str, Actor]:
    """从环境变量读取练习凭证，构造 token 哈希到身份的映射。"""
    try:
        records = TypeAdapter(list[IdentityInput]).validate_json(os.environ.get("AGENT_IDENTITIES_JSON", "[]"))
    except ValueError:
        # 校验异常可能包含原始 JSON，改用固定错误文案。
        raise RuntimeError("AGENT_IDENTITIES_JSON 格式不正确") from None
    identities = {
        token_digest(record.token): Actor(record.user_id, record.tenant_id, record.role)
        for record in records
    }
    if not identities or len(identities) != len(records):
        raise RuntimeError("AGENT_IDENTITIES_JSON 需要至少一个身份，且 token 不能重复")
    return identities


def token_digest(token: str) -> str:
    """对高熵随机 bearer token 生成查询索引。用户密码应使用专门的密码哈希。"""
    return sha256(token.encode("utf-8")).hexdigest()


bearer = HTTPBearer(auto_error=False)


def current_actor(
    request: Request, credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Actor:
    """从 Authorization: Bearer ... 读取凭证。无效凭证统一返回 401。"""
    actor = request.app.state.identities.get(token_digest(credential.credentials)) if credential else None
    if actor is None:
        raise HTTPException(status_code=401, detail="需要有效的 Bearer Token",
                            headers={"WWW-Authenticate": "Bearer"})
    return actor


def require_reviewer(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
    """鉴权通过后再检查角色。角色通过后仍需检查资源的租户归属。"""
    if actor.role != "reviewer":
        raise HTTPException(status_code=403, detail="该操作需要审批员角色")
    return actor
