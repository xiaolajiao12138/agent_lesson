"""企业实战第 2 课｜创建 Engine、设置连接参数与选择数据库方言。

调用链为 main.create_app() 或 seed -> build_engine() -> sessionmaker -> Session。
Engine 管理连接池及 SQL 方言，sessionmaker 是会话工厂，Session 承担一次工作单元。
建立 Engine 时通常还没有连接数据库，首次执行 SQL 等操作才会申请实际连接。
"""

import os

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


def build_engine(database_url: str | None = None) -> Engine:
    """根据数据库 URL 创建可复用的同步 Engine，返回值交给应用或测试负责释放。

    显式 database_url 优先，其次读取 DATABASE_URL，最后使用相对当前工作目录的 SQLite 文件。
    make_url() 将字符串解析成 URL 对象，支持读取 drivername、database 等字段。
    PostgreSQL 的 pool_pre_ping 在借出连接时检查活性，pool_timeout 限制等待连接池的时间。
    connect_timeout 限制新建 PostgreSQL 连接的等待，SQLite timeout 限制等待数据库锁的时间。
    hide_parameters 隐藏 SQLAlchemy 自身日志与异常中的绑定参数，降低业务数据泄露风险。
    本项目使用文件 SQLite 做可重启恢复实验，单独的内存数据库需要不同连接生命周期配置。
    """
    url = make_url(database_url or os.environ.get("DATABASE_URL", "sqlite:///./support_agent.db"))
    if url.drivername == "postgresql+psycopg":
        return create_engine(
            url, pool_pre_ping=True, pool_timeout=5,
            connect_args={"connect_timeout": 5}, hide_parameters=True,
        )
    if url.drivername not in {"sqlite", "sqlite+pysqlite"} or url.database in {None, "", ":memory:"}:
        raise ValueError("请使用 SQLite 文件 URL 或 postgresql+psycopg:// URL")

    # 这里使用同步引擎。异步方案通常组合 create_async_engine 与 AsyncSession。
    engine = create_engine(url, hide_parameters=True, connect_args={"timeout": 5})

    # 装饰器在 build_engine() 执行时注册，回调的函数体在连接事件发生时执行。
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _record) -> None:
        """在每条新建 SQLite 物理连接上启用外键约束。

        event.listens_for(engine, 'connect') 注册回调，建立连接时由 SQLAlchemy 调用。
        connect 事件关注新物理连接，checkout 事件关注从池中借出连接的时刻。
        cursor() 创建 DBAPI 游标，execute() 执行 PRAGMA，finally 中 close() 释放游标。
        关闭游标结束本次游标使用，连接的池化与归还继续由 Engine 管理。
        """
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    return engine


def conflict_insert(session: Session, model):
    """返回对应方言的 INSERT 语句构造器，供业务代码追加冲突处理。

    session.get_bind() 取得该会话绑定的 Engine/Connection，dialect.name 识别数据库类型。
    SQLite 与 PostgreSQL 的 insert() 都支持本项目用到的 on_conflict_do_nothing/update。
    通用 sqlalchemy.insert() 提供通用插入能力，方言版再暴露各数据库专用选项。
    此函数只构造语句，调用方通过 session.execute() 执行，并由外层事务控制提交。
    """
    if session.get_bind().dialect.name == "postgresql":
        return pg_insert(model)
    return sqlite_insert(model)
