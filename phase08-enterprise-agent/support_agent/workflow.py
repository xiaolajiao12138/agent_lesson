"""企业实战第 3–4 课｜工单持久化状态机、重复请求和并发审批。

调用链为 main.py 路由的 session.begin() -> 业务函数 -> 工单与审计 SQL -> 事务提交。
本文件的函数复用调用方提供的 Session，业务提交由外层路由或脚本统一控制。
阅读顺序为可见性检查、创建、审批、历史查询，数据库约束定义见 models.py。
状态持久化在 Ticket 中，应用重启后可继续从数据库读取和审批。
"""

from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .db import conflict_insert
from .models import Status, Ticket, TicketEvent
from .security import Actor


class TicketNotFound(Exception):
    """业务异常，表示当前身份的可见范围内查不到工单。

    可能是记录不存在，也可能是租户或所有者条件不匹配。
    main.py 用 @app.exception_handler 将它转换为 HTTP 404，业务测试也可直接检查此异常。
    """


class TicketConflict(Exception):
    """业务异常，表示重复键的请求内容冲突，或审批终态不允许本次修改。

    它与输入字段格式错误分别处理，格式错误由 Pydantic 返回 422，此异常由路由映射为 409。
    """


def visible_ticket(session: Session, actor: Actor, ticket_id: str) -> Ticket:
    """按工单 ID、租户和客户所有者范围查询，返回一个 Ticket。

    actor 由鉴权依赖生成，客户端提供 ticket_id，SQL 同时约束资源编号与身份范围。
    .where(a, b) 将多个条件按 AND 连接，多次调用 .where() 会继续组合条件。
    scalars(query) 从每行第一列取出 ORM 对象，execute(query) 默认得到包含列值的 Row 结果。
    one_or_none() 允许零或一条，多条会抛异常；one() 要求恰好一条；first() 只取首条。
    first() 本身不为 SQL 添加 LIMIT，确需限制查询可在 select() 后显式 .limit(1)。
    当前查询有主键条件，额外的租户与所有者条件负责访问范围校验。
    """
    # 在 SQL WHERE 中同时校验资源编号与身份范围，查询本身只返回获授权记录。
    query = select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == actor.tenant_id)
    if actor.role == "customer":
        query = query.where(Ticket.owner_id == actor.user_id)

    ticket = session.scalars(query).one_or_none()
    if ticket is None:
        raise TicketNotFound
    return ticket


def create_ticket(session: Session, actor: Actor, question: str, key: str) -> tuple[Ticket, bool]:
    """在调用方事务内创建工单，返回 (工单对象, 是否首次创建)。

    values() 组织待插入字段，uuid4() 生成候选工单 ID。
    on_conflict_do_nothing() 指定联合唯一约束冲突时跳过插入，配合数据库约束处理并发重试。
    returning(Ticket.id) 取得本次成功插入的 ID，scalar_one_or_none() 读取零或一个标量值。
    首次插入时 session.add() 登记创建事件，外层提交前由 flush() 将 ORM 变更发送到数据库。
    冲突时查询已存在记录，并确认 question 相同，相同键携带不同内容会抛 TicketConflict。
    相关的 on_conflict_do_update() 会覆盖指定字段，用在 knowledge.save_document() 中。
    flush() 发送待处理变更，commit() 提交事务，rollback() 放弃未提交变更，refresh() 重读对象属性。
    本函数共用外层事务，使工单和审计事件一起提交或回滚。
    """
    statement = (
        conflict_insert(session, Ticket)
        .values(
            id=str(uuid4()),
            tenant_id=actor.tenant_id,
            owner_id=actor.user_id,
            idempotency_key=key,
            question=question,
            status=Status.PENDING.value,
        )
        .on_conflict_do_nothing(index_elements=["tenant_id", "owner_id", "idempotency_key"])
        .returning(Ticket.id)
    )
    # execute 执行 SQL，scalar_one_or_none 从 RETURNING 结果中提取单个 ID。
    ticket_id = session.execute(statement).scalar_one_or_none()
    if ticket_id is not None:
        # 首次创建成功：同步在同一事务中记录创建审计事件
        session.add(TicketEvent(ticket_id=ticket_id, actor_id=actor.user_id, action="created"))
        return visible_ticket(session, actor, ticket_id), True

    # 命中唯一键冲突：代表之前该幂等键已插入过工单，查出既有记录
    existing = session.scalars(select(Ticket).where(
        Ticket.tenant_id == actor.tenant_id,
        Ticket.owner_id == actor.user_id,
        Ticket.idempotency_key == key,
    )).one()

    # 校验入参是否一致，防止同一个幂等键被用于完全不同的两个问题
    if existing.question != question:
        raise TicketConflict("该幂等键已用于另一条问题")
    return existing, False


def review_ticket(session: Session, actor: Actor, ticket_id: str, decision: Status) -> Ticket:
    """在调用方事务内把待审核工单迁移到一个终态，并写入审批审计。

    update(Ticket).where(...) 构造条件更新，WHERE 同时限定 ID、租户及当前待审状态。
    values() 声明更新字段，returning() 读取成功更新的 ID，未更新到记录时结果为空。
    同一状态检查放进一条 UPDATE，可避免两个请求依据相同旧状态都成功审批。
    PostgreSQL 通过相应的行锁协调写入，SQLite 使用其写锁机制，两者锁粒度不同。
    更新成功才登记审计；相同审批人重放相同决定时返回已有结果；冲突决定返回 409。
    先查询后修改也需要事务及相应并发控制，当前课程用条件 UPDATE 明确竞争条件。
    并发或数据库暂不可用仍可能产生等待及数据库异常，测试覆盖本课程的预期竞争场景。
    """
    statement = (
        update(Ticket)
        .where(
            Ticket.id == ticket_id,
            Ticket.tenant_id == actor.tenant_id,
            Ticket.status == Status.PENDING.value,  # 核心条件更新检查，锁机制取决于数据库。
        )
        .values(status=decision.value, reviewer_id=actor.user_id)
        .returning(Ticket.id)
    )
    # 判断成功迁移的是本次请求，再查询最新可见状态，区分幂等重放与审批冲突。
    updated_id = session.execute(statement).scalar_one_or_none()
    ticket = visible_ticket(session, actor, ticket_id)

    if updated_id is not None:
        # 更新成功：在同一事务中记录审批审计事件
        session.add(TicketEvent(ticket_id=ticket.id, actor_id=actor.user_id, action=decision.value))
    elif ticket.reviewer_id != actor.user_id or ticket.status != decision.value:
        # 被其他审批员抢先处理、或审批意见冲突
        raise TicketConflict("工单已被处理，请刷新页面")

    return ticket


def ticket_history(session: Session, actor: Actor, ticket_id: str) -> list[TicketEvent]:
    """返回当前身份可见工单的审计事件，并按事件 ID 升序排序。

    先验证父工单可见性，再按 ticket_id 读取事件，身份范围由相同的 visible_ticket() 规则控制。
    order_by(TicketEvent.id) 默认升序，.desc() 可表达降序。
    session.scalars() 提供结果迭代，list() 将它物化为调用方可重复访问的列表。
    """
    ticket = visible_ticket(session, actor, ticket_id)
    return list(session.scalars(select(TicketEvent).where(
        TicketEvent.ticket_id == ticket.id,
    ).order_by(TicketEvent.id)))
