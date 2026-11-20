import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Generic, TypeVar

from fastapi import APIRouter, FastAPI, Path, Request
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "day21_agent.db"
)
DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"


class Base(DeclarativeBase):
    """SQLAlchemy 2.x ORM 表模型基类"""


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
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

chat_router.post("/{session_id}/messages", response_model=APIResponse[dict[str, any]])


async def send_message(
    requset: Request,
    session_id: str = Path(
        ...,
    ),
):
    print("111")


if __name__ == "__main__":
    if "serve" in sys.argv:
        import uvicorn

        print("服务器已启动，地址：http:127.0.0.1：8001/docs")
        uvicorn.run(app, host="127.0.0.1", port=8001)
