"""业务验收通过公开 API 验证。并发和失败回滚也需要验证数据库结果。"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event

from evals.run import load_cases, run_cases
from support_agent.main import create_app

TOKENS = {
    "alice": "training-blue-customer-000001",
    "bob": "training-blue-customer-000002",
    "mei": "training-blue-reviewer-000001",
    "lin": "training-green-reviewer-000001",
}


def auth(user: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKENS[user]}"}


def open_ticket(client: TestClient, question: str = "需要人工处理", key: str = "request-001"):
    return client.post("/tickets", headers={**auth("alice"), "Idempotency-Key": key},
                       json={"question": question})


def test_readiness_requires_migration(engine, identities):
    with TestClient(create_app(engine, identities)) as client:
        assert client.get("/health/live").status_code == 200
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.headers["X-Request-ID"]


def test_create_replay_and_conflict(client):
    assert client.get("/health/ready").status_code == 200
    first = open_ticket(client)
    replay = open_ticket(client, question=" 需要人工处理 ")
    conflict = open_ticket(client, question="另一件事")
    assert (first.status_code, replay.status_code, conflict.status_code) == (201, 200, 409)
    assert replay.json() == first.json()
    assert first.headers["X-Request-ID"] != replay.headers["X-Request-ID"]
    ticket_id = first.json()["id"]
    history = client.get(f"/tickets/{ticket_id}/events", headers=auth("mei"))
    assert [item["action"] for item in history.json()] == ["created"]


def test_review_after_restart_and_retry(migrated, identities):
    with TestClient(create_app(migrated, identities)) as before_restart:
        ticket_id = open_ticket(before_restart).json()["id"]
    # 丢弃旧应用和连接池里的连接，然后用同一个数据库启动新应用。
    migrated.dispose()
    with TestClient(create_app(migrated, identities)) as after_restart:
        route = f"/tickets/{ticket_id}/review"
        for _ in range(2):
            response = after_restart.post(route, headers=auth("mei"), json={"decision": "approved"})
            assert response.status_code == 200
            assert response.json()["status"] == "approved"
        reject = after_restart.post(route, headers=auth("mei"), json={"decision": "rejected"})
        assert reject.status_code == 409
        history = after_restart.get(f"/tickets/{ticket_id}/events", headers=auth("mei"))
        assert [event["action"] for event in history.json()] == ["created", "approved"]


def test_identity_and_resource_access(client):
    ticket_id = open_ticket(client).json()["id"]
    path = f"/tickets/{ticket_id}"
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert client.get(path, headers=auth("alice")).status_code == 200
    assert client.get(path, headers=auth("bob")).status_code == 404
    assert client.get(path, headers=auth("lin")).status_code == 404
    assert client.get(path + "/events", headers=auth("alice")).status_code == 403
    for user, expected in [("alice", 403), ("lin", 404)]:
        response = client.post(path + "/review", headers=auth(user), json={"decision": "approved"})
        assert response.status_code == expected
    assert client.get(path, headers=auth("alice")).json()["status"] == "pending_review"


@pytest.mark.parametrize("payload,key", [
    ({"question": "  "}, "request-001"),
    ({"question": "有效问题", "tenant_id": "green"}, "request-001"),
    ({"question": "有效问题"}, "short"),
])
def test_invalid_create_request(client, payload, key):
    response = client.post("/tickets", headers={**auth("alice"), "Idempotency-Key": key}, json=payload)
    assert response.status_code == 422


def test_concurrent_create(client):
    barrier = Barrier(2, timeout=5)

    def submit():
        barrier.wait()
        return open_ticket(client)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit) for _ in range(2)]
        responses = [future.result(timeout=15) for future in futures]
    assert sorted(item.status_code for item in responses) == [200, 201]
    assert responses[0].json()["id"] == responses[1].json()["id"]


def test_concurrent_opposing_decisions(client):
    ticket_id = open_ticket(client).json()["id"]
    barrier = Barrier(2, timeout=5)

    def submit(decision):
        barrier.wait()
        return client.post(f"/tickets/{ticket_id}/review", headers=auth("mei"), json={"decision": decision})

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit, decision) for decision in ("approved", "rejected")]
        responses = [future.result(timeout=15) for future in futures]
    assert sorted(item.status_code for item in responses) == [200, 409]
    winner = next(item.json()["status"] for item in responses if item.status_code == 200)
    history = client.get(f"/tickets/{ticket_id}/events", headers=auth("mei"))
    assert [event["action"] for event in history.json()] == ["created", winner]


def test_audit_failure_rolls_back_ticket(client, migrated):
    def break_audit(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.startswith("INSERT INTO ticket_events"):
            raise RuntimeError("教学故障：审计写入失败")

    event.listen(migrated, "before_cursor_execute", break_audit)
    try:
        response = open_ticket(client)
        assert response.status_code == 500
        assert response.headers["X-Request-ID"]
    finally:
        event.remove(migrated, "before_cursor_execute", break_audit)
    # 相同 key 可以首次成功，说明前一次工单也被回滚。
    assert open_ticket(client).status_code == 201


def test_knowledge_update_and_removal(client):
    payload = {"title": "新退换政策", "body": "14 天内可退货。", "keywords": ["退货"]}
    route = "/knowledge/returns"
    assert client.put(route, headers=auth("alice"), json=payload).status_code == 403
    assert client.put(route, headers=auth("mei"), json=payload).status_code == 204
    answer = client.post("/agent/answer", headers=auth("alice"), json={"question": "怎么退货？"})
    assert answer.json()["citation"]["excerpt"] == payload["body"]
    for _ in range(2):
        assert client.delete(route, headers=auth("mei")).status_code == 204
    blue = client.post("/agent/answer", headers=auth("alice"), json={"question": "怎么退货？"})
    green = client.post("/agent/answer", headers=auth("lin"), json={"question": "怎么退货？"})
    assert blue.json()["route"] == "transfer"
    assert green.json()["citation"]["excerpt"] == "签收后 15 天内可提交退货申请。"


def test_agent_eval_regression(client):
    assert run_cases(client, TOKENS, load_cases()) == []
