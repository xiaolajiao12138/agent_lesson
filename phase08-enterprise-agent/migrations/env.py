"""由 Alembic 调用。命令行和测试可以共用迁移脚本。"""

from alembic import context

from support_agent.db import build_engine
from support_agent.models import Base


def run_online(connection) -> None:
    """绑定数据库连接，按 revision 图执行迁移操作。"""
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    # offline 模式只生成 SQL 文本，适合上线前审阅。
    engine = build_engine()
    try:
        context.configure(dialect_name=engine.dialect.name, target_metadata=Base.metadata,
                          literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    finally:
        engine.dispose()
else:
    injected_connection = context.config.attributes.get("connection")
    if injected_connection is not None:
        run_online(injected_connection)
    else:
        engine = build_engine()
        try:
            with engine.connect() as connection:
                run_online(connection)
        finally:
            engine.dispose()
