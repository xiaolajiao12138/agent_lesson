"""企业实战第 4 课｜从 Bearer 凭证得到可信身份，再检查角色与资源范围。

调用链为 HTTPBearer -> current_actor -> require_reviewer -> 业务函数的租户/所有者过滤。
HTTPBearer 提取 Authorization 中的凭证，current_actor 核验凭证映射，角色依赖执行授权。
本课使用 demo-identities.json 中公开教学身份，字段由 IdentityInput 校验后转成 Actor。
Day 21 的 Depends 与 Annotated 在这里用于复用依赖，Day 22 的环境配置用于装配身份表。
"""

import os
from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, TypeAdapter


@dataclass(frozen=True)
class Actor:
    """已认证的服务端身份对象，保存用户、租户及角色。

    @dataclass 自动生成初始化等方法，frozen=True 阻止常规字段重新赋值。
    普通 dataclass 主要保存数据，Pydantic BaseModel 还会执行输入解析与校验。
    这里的 Literal 为类型工具提供提示，运行时角色校验发生在 IdentityInput 中。
    业务查询使用 Actor 中的值限定资源范围。
    """

    user_id: str
    tenant_id: str
    role: Literal["customer", "reviewer"]


class IdentityInput(BaseModel):
    """加载教学身份配置时使用的 Pydantic 模型。

    Field 的 min_length/max_length 限定长度，pattern 是允许字符的正则表达式。
    Literal 把角色限定为 customer 或 reviewer，未提供默认值的字段均为必填。
    这些检查验证配置结构与格式，凭证是否能匹配身份由 current_actor 继续判断。
    """

    token: str = Field(min_length=24, max_length=256, pattern=r"^[a-zA-Z0-9_-]+$")
    user_id: str = Field(min_length=1, max_length=64)
    tenant_id: str = Field(min_length=1, max_length=64)
    role: Literal["customer", "reviewer"]


def load_identities() -> dict[str, Actor]:
    """读取 AGENT_IDENTITIES_JSON，校验后返回“凭证摘要 -> Actor”的字典。

    os.environ.get() 读取环境变量字符串，缺省时使用 '[]'。
    TypeAdapter(list[IdentityInput]) 校验整个列表，validate_json() 同时完成 JSON 解析和模型校验。
    BaseModel.model_validate_json() 适合单个模型，TypeAdapter 可处理 list[模型] 等组合类型。
    字典推导式建立快速查找表，len() 对比可发现摘要键覆盖造成的重复配置。
    捕获校验异常后使用固定提示，raise ... from None 隐去原异常链中的配置内容。
    """
    try:
        records = TypeAdapter(list[IdentityInput]).validate_json(
            os.environ.get("AGENT_IDENTITIES_JSON", "[]")
        )
    except ValueError:
        # 校验异常可能包含原始 JSON，改用固定错误文案。
        raise RuntimeError("AGENT_IDENTITIES_JSON 格式不正确") from None
    # JSON 中每个对象有 token、user_id、tenant_id、role 四个字段，来源见 demo-identities.json。
    identities = {
        token_digest(record.token): Actor(record.user_id, record.tenant_id, record.role)
        for record in records
    }
    if not identities or len(identities) != len(records):
        raise RuntimeError("AGENT_IDENTITIES_JSON 需要至少一个身份，且 token 不能重复")
    return identities


def token_digest(token: str) -> str:
    """将 Bearer Token 编码为 UTF-8 字节，再计算 SHA-256 十六进制摘要。

    encode() 完成字符串到字节的转换，hexdigest() 返回便于作为字典键使用的摘要文本。
    数据库或内存查找用相同算法计算摘要，再根据摘要定位 Actor。
    该方法面向高熵随机凭证的查找，用户密码通常需要专门的慢哈希方案。
    """
    return sha256(token.encode("utf-8")).hexdigest()


# auto_error=False 让无凭证等情况交回 current_actor，由本课统一形成 401 响应。
# 同时为 Swagger 生成 Bearer 安全方案，页面的 Authorize 会设置 Authorization 请求头。
bearer = HTTPBearer(auto_error=False)


def current_actor(
    request: Request,
    credential: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Actor:
    """解析当前请求的 Bearer 凭证，返回对应的可信 Actor。

    Depends(bearer) 让 FastAPI 先调用 HTTPBearer，并传入 HTTPAuthorizationCredentials。
    credential.credentials 是凭证正文，credential.scheme 表示认证方案。
    request.app.state.identities 是 create_app() 启动时装配的身份映射。
    未找到身份时抛 HTTPException(401)，WWW-Authenticate 指示客户端使用 Bearer 认证。
    普通 return 把 Actor 交给下游依赖，带 yield 的依赖还可执行资源清理。
    """
    actor = (
        request.app.state.identities.get(token_digest(credential.credentials))
        if credential
        else None
    )
    if actor is None:
        raise HTTPException(
            status_code=401,
            detail="需要有效的 Bearer Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return actor


def require_reviewer(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
    """复用 current_actor 完成认证，再将可执行角色限定为 reviewer。

    登录身份有效但角色不足时返回 403，通过后返回同一个 Actor 给路由使用。
    依赖链按所需资源求值，current_actor 的结果可在同一次请求中被 FastAPI 缓存复用。
    角色通过后，workflow.py 和 knowledge.py 仍按租户、所有者及文档可见范围过滤资源。
    """
    if actor.role != "reviewer":
        raise HTTPException(status_code=403, detail="该操作需要审批员角色")
    return actor
