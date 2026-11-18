"""Day 23 / 29｜用离线模型替身验证报价规则和 HTTP 行为。"""

import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Event
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from quote_agent import create_app, make_quote, model_budget


def test_budget_and_compatibility():
    # Day 24｜明确边界：总价正好等于预算时，整套设备仍然可选。
    result = make_quote(300000)
    assert result["total_cents"] == 280000
    assert all(item["interface"] == "USB" for item in result["items"])
    assert make_quote(280000) == {**result, "budget_cents": 280000}
    assert make_quote(279999)["status"] == "no_match"


def test_api(tmp_path):
    # Day 23｜tmp_path 给每个测试安排独立数据库，替身函数避免调用外部模型。
    app = create_app(tmp_path / "quotes.db", "test-token", lambda _: 300000)
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer test-token", "Idempotency-Key": "test-request"}
        assert client.post("/quotes", json={"request": "test"}).status_code == 401
        first = client.post("/quotes", headers=headers, json={"request": "test"})
        assert first.status_code == 200
        assert (
            client.post("/quotes", headers=headers, json={"request": "test"}).json() == first.json()
        )
        conflict = client.post("/quotes", headers=headers, json={"request": "changed"})
        assert conflict.status_code == 409
        assert conflict.headers["X-Request-ID"]
        assert client.get("/health/ready").status_code == 200


def test_swagger_has_bearer_scheme(tmp_path):
    # Day 3 / 27｜OpenAPI 有 Bearer 方案，Swagger 才能用 Authorize 发凭证。
    app = create_app(tmp_path / "quotes.db", "test-token", lambda _: 300000)
    spec = app.openapi()
    assert spec["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert {"HTTPBearer": []} in spec["paths"]["/quotes"]["post"]["security"]


def test_readiness_reports_missing_schema(tmp_path):
    # Day 30｜人为让查询目标消失，断言探针报告 503 而不是抛数据库异常。
    database = tmp_path / "quotes.db"
    app = create_app(database, "test-token", lambda _: 300000)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("DROP TABLE quotes")
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 503


def test_missing_database_does_not_create_a_blank_database(tmp_path):
    # Day 25 / 30｜模拟文件在启动后不可用。探针和报价都能报告依赖故障。
    database = tmp_path / "quotes.db"
    app = create_app(database, "test-token", lambda _: 300000)
    database.rename(tmp_path / "offline.db")
    with TestClient(app) as client:
        assert client.get("/health/ready").status_code == 503
        failed = client.post(
            "/quotes",
            headers={"Authorization": "Bearer test-token", "Idempotency-Key": "storage-demo"},
            json={"request": "预算3000元"},
        )
        assert failed.status_code == 503
        assert failed.headers["X-Request-ID"]
    assert not database.exists()


def test_invalid_adapter_budget_is_not_saved(tmp_path):
    # Day 2 / 23｜替换模型适配器后，API 仍需拒绝无效的预算值。
    answers = iter([-1, 300000])
    app = create_app(tmp_path / "quotes.db", "test-token", lambda _: next(answers))
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer test-token", "Idempotency-Key": "invalid-demo"}
        payload = {"request": "预算3000元"}
        assert client.post("/quotes", headers=headers, json=payload).status_code == 502
        assert client.post("/quotes", headers=headers, json=payload).json()["total_cents"] == 280000


@pytest.mark.parametrize(
    ("reason", "calls", "expected"),
    [
        ("stop", [], None),
        ("tool_calls", [("quote_budget", '{"budget_cents":300000}')], 300000),
        ("length", [], ValueError),
        ("tool_calls", [("other_tool", '{"budget_cents":300000}')], ValueError),
        ("tool_calls", [("quote_budget", '{"budget_cents":"300000"}')], ValueError),
    ],
)
def test_model_response(monkeypatch, reason, calls, expected):
    # Day 13 / 23｜用 SDK 同形的对象验证真实解析函数，不加载密钥或调用网络。
    client = MagicMock()
    scoped_client = client.with_options.return_value.__enter__.return_value
    completion = scoped_client.chat.completions.create
    completion.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=reason,
                message=SimpleNamespace(
                    tool_calls=[
                        SimpleNamespace(
                            type="function", function=SimpleNamespace(name=name, arguments=args)
                        )
                        for name, args in calls
                    ]
                ),
            )
        ]
    )
    monkeypatch.setitem(
        sys.modules,
        "config",
        SimpleNamespace(
            DEFAULT_MODEL="fixture-model",
            get_openai_client=lambda: client,
        ),
    )

    if expected is ValueError:
        with pytest.raises(ValueError):
            model_budget("我的预算是3000元")
    else:
        assert model_budget("我的预算是3000元") == expected
    assert completion.call_args.kwargs["model"] == "fixture-model"


def test_model_failure_can_retry(tmp_path):
    # Day 26 / 29｜第一次失败不应占用幂等键，恢复后同键可重试并读回原结果。
    answers = iter([TimeoutError(), 300000])

    def model_stub(_):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    with TestClient(create_app(tmp_path / "quotes.db", "test-token", model_stub)) as client:
        headers = {"Authorization": "Bearer test-token", "Idempotency-Key": "retry-demo"}
        payload = {"request": "预算3000元"}
        failed = client.post("/quotes", headers=headers, json=payload)
        assert failed.status_code == 502
        assert failed.headers["X-Request-ID"]
        retried = client.post("/quotes", headers=headers, json=payload)
        assert retried.status_code == 200
        assert retried.json()["total_cents"] == 280000
        assert client.post("/quotes", headers=headers, json=payload).json() == retried.json()


def test_concurrent_model_failure_reuses_committed_result(tmp_path):
    # Day 26｜第一个模型调用卡住，第二个同键请求先提交，随后第一个调用失败。
    started = Event()
    committed = Event()

    def model_stub(_):
        if started.is_set():
            return 300000
        started.set()
        if not committed.wait(timeout=8):
            raise AssertionError("测试没有观察到另一请求完成")
        raise TimeoutError()

    app = create_app(tmp_path / "quotes.db", "test-token", model_stub)
    headers = {"Authorization": "Bearer test-token", "Idempotency-Key": "concurrent-demo"}

    def submit():
        with TestClient(app) as client:
            return client.post("/quotes", headers=headers, json={"request": "预算3000元"})

    with ThreadPoolExecutor(max_workers=2) as pool:
        slow = pool.submit(submit)
        try:
            assert started.wait(timeout=5)
            winner = pool.submit(submit).result(timeout=5)
            assert winner.status_code == 200
        finally:
            committed.set()
        replay = slow.result(timeout=5)
    assert replay.status_code == 200
    assert replay.json() == winner.json()
