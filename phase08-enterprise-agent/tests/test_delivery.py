"""企业实战第 6 课｜通过公开 API 验证完整业务闭环，衔接 Day 23。

阅读每条用例时依次找准备数据、发送请求、assert 预期、清理资源。
测试函数的参数名会请求 conftest.py 中的 fixture，各测试拥有隔离数据库。
前四组覆盖就绪检查、幂等、重启恢复和访问控制，再读参数化、并发、回滚和知识库评测。
当前测试实际运行数据库与 FastAPI，模型调用费用取决于项目业务；本课程问答采用本地关键词基线。
TOKENS 是公开教学凭证的测试索引，身份内容由 demo-identities.json 装配。
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from evals.run import load_cases, run_cases
from fastapi.testclient import TestClient
from sqlalchemy import event
from support_agent.main import create_app

TOKENS = {
    "alice": "training-blue-customer-000001",
    "bob": "training-blue-customer-000002",
    "mei": "training-blue-reviewer-000001",
    "lin": "training-green-reviewer-000001",
}


def auth(user: str) -> dict[str, str]:
    """按教学用户简称创建 Authorization 请求头。

    f-string 将凭证拼成 Bearer 格式，字典可直接交给 TestClient 的 headers 参数。
    每次调用返回一个新的字典，建单辅助函数可继续展开它并加入幂等键。
    """
    return {"Authorization": f"Bearer {TOKENS[user]}"}


def open_ticket(
    client: TestClient, question: str = "需要人工处理", key: str = "request-001"
):
    """测试辅助方法，使用 alice 身份向 POST /tickets 发送建单请求。

    question 和 key 提供默认样例，测试可按场景覆盖其中任一参数。
    {**auth(...), ...} 合并请求头，json= 让客户端编码 JSON 并设置对应内容类型。
    返回完整 Response，便于用例分别断言 status_code、headers 和 json()。
    """
    return client.post(
        "/tickets",
        headers={**auth("alice"), "Idempotency-Key": key},
        json={"question": question},
    )


def test_readiness_requires_migration(engine, identities):
    """验证进程存活和数据库就绪是不同条件。

    engine fixture 尚未执行迁移，因此 live 返回 200，ready 返回 503。
    同时断言错误响应也带 X-Request-ID，便于按失败请求查询日志。
    """
    with TestClient(create_app(engine, identities)) as client:
        assert client.get("/health/live").status_code == 200
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.headers["X-Request-ID"]


def test_create_replay_and_conflict(client):
    """验证首次创建、相同请求重放、相同键不同内容三条路径。

    首尾空格会由 Question 类型规范化，因此第二次请求与首次问题相同。
    依次期望 201、200、409，且重放返回同一份工单数据。
    不同 HTTP 请求各自有 Request ID，同一次业务操作可以复用幂等键。
    审计中只应出现一次 created，验证重复请求的业务副作用受到约束。
    """
    assert client.get("/health/ready").status_code == 200
    first = open_ticket(client)
    replay = open_ticket(client, question=" 需要人工处理 ")
    conflict = open_ticket(client, question="另一件事")
    assert (first.status_code, replay.status_code, conflict.status_code) == (
        201,
        200,
        409,
    )
    assert replay.json() == first.json()
    assert first.headers["X-Request-ID"] != replay.headers["X-Request-ID"]
    ticket_id = first.json()["id"]
    history = client.get(f"/tickets/{ticket_id}/events", headers=auth("mei"))
    assert [item["action"] for item in history.json()] == ["created"]


def test_review_after_restart_and_retry(migrated, identities):
    """验证工单写入数据库后可被新的应用实例读取和审批。

    前一个 TestClient 创建工单，关闭后 dispose 旧连接，再用同一隔离数据库创建新应用。
    相同审批重试两次都成功，相反终态返回 409。
    最后检查审计只有 created 和 approved，验证重放没有新增审批事件。
    """
    with TestClient(create_app(migrated, identities)) as before_restart:
        ticket_id = open_ticket(before_restart).json()["id"]
    # 丢弃旧应用和连接池里的连接，然后用同一个数据库启动新应用。
    migrated.dispose()
    with TestClient(create_app(migrated, identities)) as after_restart:
        route = f"/tickets/{ticket_id}/review"
        for _ in range(2):
            response = after_restart.post(
                route, headers=auth("mei"), json={"decision": "approved"}
            )
            assert response.status_code == 200
            assert response.json()["status"] == "approved"
        reject = after_restart.post(
            route, headers=auth("mei"), json={"decision": "rejected"}
        )
        assert reject.status_code == 409
        history = after_restart.get(f"/tickets/{ticket_id}/events", headers=auth("mei"))
        assert [event["action"] for event in history.json()] == ["created", "approved"]


def test_identity_and_resource_access(client):
    """分别验证身份认证、角色授权、租户边界和工单所有者边界。

    无凭证或错误凭证为 401，合法客户访问审批资源为 403。
    同租户其他客户、其他租户审批员访问本工单时得到统一 404。
    最后确认工单仍处于待审状态，表明被拒绝请求没有改变业务状态。
    """
    ticket_id = open_ticket(client).json()["id"]
    path = f"/tickets/{ticket_id}"
    assert client.get(path).status_code == 401
    assert (
        client.get(path, headers={"Authorization": "Bearer invalid"}).status_code == 401
    )
    assert client.get(path, headers=auth("alice")).status_code == 200
    assert client.get(path, headers=auth("bob")).status_code == 404
    assert client.get(path, headers=auth("lin")).status_code == 404
    assert client.get(path + "/events", headers=auth("alice")).status_code == 403
    for user, expected in [("alice", 403), ("lin", 404)]:
        response = client.post(
            path + "/review", headers=auth(user), json={"decision": "approved"}
        )
        assert response.status_code == expected
    assert client.get(path, headers=auth("alice")).json()["status"] == "pending_review"


@pytest.mark.parametrize(
    "payload,key",
    [
        ({"question": "  "}, "request-001"),
        ({"question": "有效问题", "tenant_id": "green"}, "request-001"),
        ({"question": "有效问题"}, "short"),
    ],
)
def test_invalid_create_request(client, payload, key):
    """用三组参数覆盖空问题、额外身份字段和过短幂等键。

    @pytest.mark.parametrize 的每个元组都会生成一次独立测试调用。
    payload 和 key 从参数表注入，client 从 fixture 注入，格式不合法统一期望 422。
    相关的 pytest.raises() 用于直接调用 Python 函数并检查异常，本处检查 HTTP 响应。
    """
    response = client.post(
        "/tickets", headers={**auth("alice"), "Idempotency-Key": key}, json=payload
    )
    assert response.status_code == 422


def test_concurrent_create(client):
    """让两个请求尽量同时提交相同建单操作，验证数据库层幂等约束。

    Barrier(2) 等待两个工作线程都到达后放行，timeout 为失败时提供退出边界。
    ThreadPoolExecutor 负责并发执行，submit() 返回 Future，result() 等待结果并传播异常。
    检查状态码分别为 200 和 201，以及两次返回同一个工单 ID。
    sorted() 用于忽略两个并发请求实际完成的先后顺序。
    """
    # 这里的 timeout 仅限制同步等待；Future.result 的 timeout 另行限制结果等待。
    barrier = Barrier(2, timeout=5)

    def submit():
        """线程任务，等待同步点后调用真实测试接口。

        嵌套函数捕获外层 barrier 和 client；并发到达顺序由调度决定。
        """
        barrier.wait()
        return open_ticket(client)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit) for _ in range(2)]
        responses = [future.result(timeout=15) for future in futures]
    assert sorted(item.status_code for item in responses) == [200, 201]
    assert responses[0].json()["id"] == responses[1].json()["id"]


def test_concurrent_opposing_decisions(client):
    """并发提交 approved 与 rejected，验证只有一个请求完成状态迁移。

    两个线程共享工单 ID，各自提交相反决定，预期一个 200 和一个 409。
    next(...) 选出获胜响应，随后检查审计事件与最终决定一致。
    该用例验证本课程 SQL 条件更新的并发行为，数据库等待超时等情况仍由部署参数决定。
    """
    ticket_id = open_ticket(client).json()["id"]
    barrier = Barrier(2, timeout=5)

    def submit(decision):
        """审批线程任务，在同步点之后提交指定 decision。

        每次调用 client.post() 都会创建一次独立请求，并经过应用的依赖和事务处理。
        """
        barrier.wait()
        return client.post(
            f"/tickets/{ticket_id}/review",
            headers=auth("mei"),
            json={"decision": decision},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(submit, decision) for decision in ("approved", "rejected")
        ]
        responses = [future.result(timeout=15) for future in futures]
    assert sorted(item.status_code for item in responses) == [200, 409]
    winner = next(
        item.json()["status"] for item in responses if item.status_code == 200
    )
    history = client.get(f"/tickets/{ticket_id}/events", headers=auth("mei"))
    assert [event["action"] for event in history.json()] == ["created", winner]


def test_audit_failure_rolls_back_ticket(client, migrated):
    """注入审计 SQL 写入异常，验证工单和审计处于同一事务。

    event.listen() 注册执行前回调，审计 INSERT 到达时人为抛出 RuntimeError。
    接口应返回 500 和 Request ID，finally 中 event.remove() 恢复正常数据库执行。
    相同幂等键随后首次创建仍返回 201，验证前次失败的工单插入已经回滚。
    相关的 AsyncMock.side_effect 适合模拟异步模型异常，此处直接对数据库事件注入故障。
    """
    def break_audit(_conn, _cursor, statement, _parameters, _context, _executemany):
        """SQL 执行前的故障注入回调。

        SQLAlchemy 按事件签名传入连接、游标、SQL、绑定参数和上下文。
        下划线前缀表示该参数当前未使用，仅检查 SQL 指向的审计表。
        """
        if statement.startswith("INSERT INTO ticket_events"):
            raise RuntimeError("教学故障：审计写入失败")

    # 回调只在本条测试的隔离引擎上生效，测试结束后解除注册。
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
    """验证文档更新、重复删除、查询转人工以及跨租户互不影响。

    客户更新知识库被拒绝，审批员 PUT 成功后回答引用应立即反映新正文。
    两次 DELETE 均返回 204，blue 文档删除后建议转人工，green 的同名文档仍可查询。
    本用例通过响应正文检查业务效果，而不只检查 HTTP 成功状态。
    """
    payload = {"title": "新退换政策", "body": "14 天内可退货。", "keywords": ["退货"]}
    route = "/knowledge/returns"
    assert client.put(route, headers=auth("alice"), json=payload).status_code == 403
    assert client.put(route, headers=auth("mei"), json=payload).status_code == 204
    answer = client.post(
        "/agent/answer", headers=auth("alice"), json={"question": "怎么退货？"}
    )
    assert answer.json()["citation"]["excerpt"] == payload["body"]
    for _ in range(2):
        assert client.delete(route, headers=auth("mei")).status_code == 204
    blue = client.post(
        "/agent/answer", headers=auth("alice"), json={"question": "怎么退货？"}
    )
    green = client.post(
        "/agent/answer", headers=auth("lin"), json={"question": "怎么退货？"}
    )
    assert blue.json()["route"] == "transfer"
    assert green.json()["citation"]["excerpt"] == "签收后 15 天内可提交退货申请。"


def test_agent_eval_regression(client):
    """用进程内 TestClient 执行 evals/cases.json 中的固定评测集合。

    run_cases() 返回失败原因列表，assert ... == [] 要求所有样例均符合当前摘录基线。
    同一评测函数也可以通过 httpx.Client 检查真实运行的 API。
    """
    assert run_cases(client, TOKENS, load_cases()) == []
