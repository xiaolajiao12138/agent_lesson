"""Engine 管理连接；sessionmaker 创建 Session；Session 管理一次数据库工作。

知识对应：SQLAlchemy、上下文管理器、yield、FastAPI Depends。
这里只提供会话和 Base，不定义订单表、不自动建表、不提供业务 SQL。
"""
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session

from .core.config import BACKEND_DIR, Settings


class Base(DeclarativeBase):
    """未来的 Order、Ticket、User 等模型继承此类；当前没有业务数据表。"""


def build_engine(settings: Settings):
    url = make_url(settings.database_url)
    options = {"pool_pre_ping": True}
    if url.get_backend_name() == "sqlite":
        if url.database and url.database != ":memory:":
            database_path = Path(url.database)
            if not database_path.is_absolute():
                database_path = BACKEND_DIR / database_path
            database_path.parent.mkdir(parents=True, exist_ok=True)
            url = url.set(database=str(database_path))
        options["connect_args"] = {"check_same_thread": False, "timeout": 10}
    engine = create_engine(url, **options)
    if url.get_backend_name() == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()
    return engine


def get_session(request: Request) -> Iterator[Session]:
    """每次请求创建独立 Session。with 负责 close，不代表自动 commit。

    未来写接口时，由业务入口显式使用 with session.begin() 管理提交和回滚。
    """
    with request.app.state.sessions() as session:
        yield session


Database = Annotated[Session, Depends(get_session)]
