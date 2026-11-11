"""企业实战第 2 课｜连接池、请求级 Session 与事务边界。"""

import os

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


def build_engine(database_url: str | None = None) -> Engine:
    """创建可复用的 Engine。Engine 管理连接池，实际连接按需打开。"""
    url = make_url(database_url or os.environ.get("DATABASE_URL", "sqlite:///./support_agent.db"))
    if url.drivername == "postgresql+psycopg":
        return create_engine(
            url, pool_pre_ping=True, pool_timeout=5,
            connect_args={"connect_timeout": 5}, hide_parameters=True,
        )
    if url.drivername not in {"sqlite", "sqlite+pysqlite"} or url.database in {None, "", ":memory:"}:
        raise ValueError("请使用 SQLite 文件 URL 或 postgresql+psycopg:// URL")

    engine = create_engine(url, hide_parameters=True, connect_args={"timeout": 5})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _record) -> None:
        """SQLite 每条连接都要开启外键检查，课程的外键约束才能生效。"""
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    return engine


def conflict_insert(session: Session, model):
    """构造支持 ON CONFLICT 的 INSERT，执行由调用方控制。"""
    if session.get_bind().dialect.name == "postgresql":
        return pg_insert(model)
    return sqlite_insert(model)
