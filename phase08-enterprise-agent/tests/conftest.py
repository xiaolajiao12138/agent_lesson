"""为每个用例创建隔离数据库，使用实际迁移和 FastAPI 请求链路。"""

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

PROJECT = Path(__file__).resolve().parents[1]


@fixture
def engine(tmp_path):
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
    schema = "course_test_" + uuid4().hex
    try:
        with admin.begin() as connection:
            connection.execute(CreateSchema(schema))
        try:
            isolated_url = admin.url.update_query_dict({"options": f"-csearch_path={schema}"})
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
    config = Config(str(PROJECT / "alembic.ini"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    with sessionmaker(engine).begin() as session:
        seed_documents(session)
    return engine


@fixture
def identities(monkeypatch):
    monkeypatch.setenv("AGENT_IDENTITIES_JSON", (PROJECT / "demo-identities.json").read_text(encoding="utf-8"))
    return load_identities()


@fixture
def client(migrated, identities):
    with TestClient(create_app(migrated, identities)) as test_client:
        yield test_client
