import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Generic, TypeVar

# from day21_fastapi_engineering import AgentBizError, ApiResponse, ChatMessageRecord
from fastapi import APIRouter, Body, Depends, FastAPI, Header, Path, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import DEFAULT_MODEL, get_async_openai_client

DB_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "day21_agent.db"
)
DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"


class Base(DeclarativeBase):
    """SQLAlchemy 2.x ORM 表模型基类"""


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    统一返回结构：
        -code:0表示成功，非0表示业务错误码
        -msg:提示信息
        -data:具体业务数据
    """

    code: int = Field(default=0, description="业务状态码，0成功，非0失败")
    msg: str = Field(default="success", description="状态说明信息")
    data: T | None = Field(default=None, description="响应数据载体")


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    app.state.db_engine = engine
    app.state.db_seeion_factory = session_factory
    app.state.shared_resources = {
        "boot_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "vector_db_status": "ready",
        "db_file": DB_FILE_PATH,
        "ingested_docs": {},
    }
    yield  # 一直停留再这里

    app.state.db_engine.dispose()  # 彻底关闭底层连接池，防止链接泄露
    app.state.shared_resources.clear()


app = FastAPI(lifespan=app_lifespan)

chat_router = APIRouter(prefix="/api/v1/sessions", tags=["1.智能体对话模块"])


@chat_router.post("/{session_id}/messages", response_model=ApiResponse[dict[str, Any]])
class ChatRequest(BaseModel):
    """POST JSON请求体模型"""

    message: str = Field(..., min_length=1, max_length=2000, description="用户提问内容")
    model_name: str = Field(default="gpt-6.1-sol", description="指定调用的大模型")


class AgentBizError(Exception):
    """自定义智能体业务异常（比如：token，余额不足，大模型限流，知识库不存在）"""

    def __init__(self, code: int, msg: str, status_code: int = 400):
        self.code = code
        self.msg = msg
        self.status_code = status_code


class ChatMessageRecord(Base):
    """真实的对话记录数据表：chat_messages"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    ai_reply: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[Any] = mapped_column(DateTime, server_default=func.now())


async def get_current_user(
    x_token: str = Header(default="dev_token_001", description="用户鉴权"),
) -> dict[str, Any]:
    """每次请求进来时自动检查请求头x-token  如果传了非法token，直接抛出我们上面定义的AgentBizError"""
    if x_token == "invalid":
        raise AgentBizError(
            code=40101, msg="登录凭证无效或已过期，请重新登录", status_code=401
        )
    return {
        "user_id": "u_888",
        "user_name": "小陈",
        "role": "ai_engineer",
        "token": x_token,
    }


async def get_db_session(request: Request):
    session_factory = request.app.state.db_seeion_factory
    db: Session = session_factory()
    try:
        yield db
    except Exception:
        db.rollback()  # 发生异常自动回滚未提交的事务
        raise
    finally:
        db.close()  # 100% 安全释放连接回连接池，防止连接数爆满！


async def send_message(
    requset: Request,
    session_id: str = Path(
        ..., min_length=1, description="会话唯一ID，如sess_001"
    ),  ##会话唯一ID
    enable_rag: bool = Query(
        default=False, description="是否开启知识库检索"
    ),  # 是否开启知识库检索
    top_k: int = Query(default=3, description="检索召回条数"),
    payload: ChatRequest = Body(..., description="对话请求json体"),  # 前端请求参数
    x_client_version: str = Header(default="web-1.0", description="前端客户端版本号"),
    current_user: dict[str, Any] = Depends(
        get_current_user
    ),  # 用户名称以及token等，可以进行用户鉴权
    db: Session = Depends(get_db_session),  # 数据库
):
    print("111")
    client = get_async_openai_client()
    MODEL = payload.model_name or DEFAULT_MODEL
    client_res = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是一个企业AI助手，请用一句话回答用户问题"},
            {"role": "user", "content": payload.message},
        ],
    )
    ai_res = client_res.choices[0].message.content or ""
    new_record = ChatMessageRecord(
        session_id=session_id,
        username=current_user["username"],
        user_message=payload.message,
        ai_res=ai_res,
        model_name=MODEL,
    )
    db.add(new_record)  # 把ORM对象加入本次数据库事务
    db.commit()  # 真实提交事务写入硬盘文件
    db.refresh(new_record)  # 刷新拿到的数据库事务自动生成的自增主键id与created_at时间
    total_count = db.scalar(
        select(
            func.count(ChatMessageRecord.id).where(
                ChatMessageRecord.session_id == session_id
            )
        )
    )
    return ApiResponse(
        code=0,
        msg="对话处理成功并已写入真是数据库",
        data={
            "saved_record_id": new_record.id,
            "session_total_message": total_count,
            "from_path_session_id": session_id,
            "from_query": {"enable_arg": enable_rag, "top_k": top_k},
            "from_body": payload.model_dump(),
            "from_header_vaersion": x_client_version,
            "from_depends_user": current_user["user_name"],
            "llm_reply": ai_res,
        },
    )


if __name__ == "__main__":
    if "serve" in sys.argv:
        import uvicorn

        print("服务器已启动，地址：http//:127.0.0.1:8001/docs")
        uvicorn.run(app, host="127.0.0.1", port=8001)
