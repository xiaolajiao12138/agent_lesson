"""企业实战第 6 课｜pytest 共享 fixture，衔接 Day 23 的测试准备与清理。

pytest 自动发现 conftest.py，测试按参数名请求 fixture，当前默认作用域是每个测试函数。
依赖顺序为 engine -> migrated -> client，identities 为 client 提供教学身份。
engine 准备隔离存储，migrated 执行真实迁移和样例导入，client 装配测试应用。
yield 前准备资源，测试执行期间提供资源，退出时执行 finally/with 清理。
这是测试上下文的资源交接，与 FastAPI 的请求级 yield 依赖在调用方和作用范围上不同。
"""

import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pytest import fixture
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema
from support_agent.db import build_engine
from support_agent.main import create_app
from support_agent.security import load_identities
from support_agent.seed import seed_documents

# resolve() 得到绝对路径，parents[1] 指向项目目录，保证从不同工作目录启动也能找到配置。
PROJECT = Path(__file__).resolve().parents[1]


@fixture
def engine(tmp_path):
    """为每条测试准备独立 Engine，默认使用 pytest 临时目录内的 SQLite 文件。

    tmp_path 是 pytest 提供的 pathlib.Path，as_posix() 生成适合拼接 URL 的路径形式。
    设置 TEST_DATABASE_URL 时使用 PostgreSQL，每条用例拥有随机 schema。
    Engine.begin() 打开连接及事务，成功退出提交，异常退出回滚。
    CreateSchema/DropSchema 操作测试命名空间，cascade=True 在清理时一并移除该 schema 内对象。
    update_query_dict() 在 URL 中设置 search_path，让建表和查询使用本用例的 schema。
    render_as_string(hide_password=False) 为数据库连接生成完整 URL，日志输出应继续隐藏密码。
    finally 块确保用例异常时也释放引擎并清理自己创建的 schema。
    """
    postgres_url = os.environ.get("TEST_DATABASE_URL")
    if not postgres_url:
        database = build_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
        try:
            yield database
        finally:
            database.dispose()
        return

    # 只创建和清理由本用例随机命名的 schema，互不共享表或迁移版本。
    admin = build_engine(postgres_url)
    # UUID 仅用于本次用例命名，独立 schema 让并行测试拥有各自的表和迁移版本。
    schema = "course_test_" + uuid4().hex
    try:
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        try:
            isolated_url = admin.url.update_query_dict(
                {"options": f"-csearch_path={schema}"}
            )
            database = build_engine(isolated_url.render_as_string(hide_password=False))
            try:
                yield database
            finally:
                database.dispose()
        finally:
            with admin.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
    finally:
        admin.dispose()


@fixture
def migrated(engine):
    """在隔离数据库上执行到最新迁移，再导入教学文档，返回 Engine。

    Config() 读取 alembic.ini，attributes['connection'] 将现有连接传给 migrations/env.py。
    command.upgrade(config, 'head') 执行版本图中尚未应用的升级步骤。
    'head' 表示最新版本，指定 revision 可迁移到对应版本，downgrade 用于回退。
    sessionmaker(engine).begin() 创建 Session 与事务，导入成功后提交并关闭。
    依赖 engine 的测试可以观察迁移前状态，依赖 migrated 的测试获得已建表的数据环境。
    """
    config = Config(str(PROJECT / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    with sessionmaker(engine).begin() as session:
        seed_documents(session)
    return engine


@fixture
def identities(monkeypatch):
    """将公开教学身份配置注入测试环境，并调用真实配置解析函数。

    monkeypatch.setenv() 临时设置变量，fixture 结束后 pytest 自动恢复原环境。
    Path.read_text(encoding='utf-8') 读取 JSON 文本，load_identities() 校验并构造身份映射。
    本用例通过依赖环境配置隔离身份，相关的 dependency_overrides 适合直接替换 FastAPI 依赖函数。
    """
    monkeypatch.setenv(
        "AGENT_IDENTITIES_JSON",
        (PROJECT / "demo-identities.json").read_text(encoding="utf-8"),
    )
    return load_identities()


@fixture
def client(migrated, identities):
    """为每个测试提供一个 TestClient，并管理应用生命周期。

    create_app(migrated, identities) 使用 fixture 的数据库和身份，绕过运行环境的资源装配。
    with TestClient(...) 触发应用启动与关闭，yield 把客户端交给测试函数。
    TestClient 在进程内执行 ASGI 应用，httpx.Client 通常连接实际监听的 HTTP 服务。
    两者均提供 get/post 等接口，evals.run.run_cases() 因此可以复用同一套请求逻辑。
    """
    with TestClient(create_app(migrated, identities)) as test_client:
        yield test_client
