"""企业实战第 2、7 课｜Alembic 的迁移运行环境，由 alembic 命令加载。

alembic.ini 指向本迁移目录，env.py 负责提供连接、模型元数据及事务环境。
命令行通常创建 Engine，测试通过 config.attributes 注入隔离连接。
Base.metadata 描述当前 ORM 表结构，versions/ 中的 revision 记录已审核的结构演进步骤。
本文件配置并执行迁移，业务请求的数据库 Session 在 support_agent/main.py 中提供。
"""



# alembic.ini 的 script_location 指向迁移目录，prepend_sys_path 把项目加入导入搜索路径。
# %(here)s 表示配置文件所在目录。INI 保持 ASCII 注释，兼容 Windows 按本地编码读取的方式。

from alembic import context

from support_agent.db import build_engine
from support_agent.models import Base


def run_online(connection) -> None:
    """在已有 Connection 上配置并执行升级或回退所需的迁移步骤。

    context.configure() 绑定连接及元数据，compare_type=True 用于自动生成迁移时比较列类型。
    context.begin_transaction() 建立 Alembic 迁移事务上下文，具体 DDL 事务能力取决于数据库。
    context.run_migrations() 根据版本图及当前版本调用各 migration 的 upgrade()/downgrade()。
    普通业务的 session.begin() 管理数据操作，这里处理的是数据库结构迁移。
    """
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


# --sql 等离线模式主要生成待审阅的 SQL 文本；在线模式连接数据库执行迁移。
if context.is_offline_mode():
    # offline 模式只生成 SQL 文本，适合上线前审阅。
    engine = build_engine()
    try:
        # literal_binds=True 尽量将参数写成 SQL 字面量，方便生成独立 SQL 文本。
        context.configure(dialect_name=engine.dialect.name, target_metadata=Base.metadata,
                          literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    finally:
        engine.dispose()
else:
    # 测试把连接存入 Config.attributes，本处复用它，以使用同一个隔离事务和 schema。
    injected_connection = context.config.attributes.get("connection")
    if injected_connection is not None:
        run_online(injected_connection)
    else:
        engine = build_engine()
        try:
            # connect() 管理借出和关闭连接，迁移事务由 run_online() 中的上下文管理。
            with engine.connect() as connection:
                run_online(connection)
        finally:
            engine.dispose()
