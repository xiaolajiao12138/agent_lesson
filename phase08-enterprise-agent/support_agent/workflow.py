"""
================================================================================
企业实战：工单业务状态机、幂等性条件更新与事务内审计
================================================================================
本模块实现了企业级售后工单的核心状态机与生命周期流转。
涵盖核心技巧与类似方法对比：
    1. 【多租户安全查询】：ID + 租户联合限定，one_or_none() vs first() vs one()
    2. 【幂等性安全创建】：conflict_insert + on_conflict_do_nothing vs on_conflict_do_update
    3. 【高并发原子状态迁移】：将前置状态检查下沉到 SQL WHERE 避免读后写竞态
    4. 【事务内审计追踪】：业务数据与审计事件在同一数据库事务中原子写入
"""

from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .db import conflict_insert
from .models import Status, Ticket, TicketEvent
from .security import Actor


class TicketNotFound(Exception):
    """当前身份的可见范围内没有这张工单（可能是不存在，也可能是跨租户越权访问已被安全阻断）"""


class TicketConflict(Exception):
    """幂等键复用时参数变了，或工单状态已被其他审批员终结（高并发竞态冲突）"""


def visible_ticket(session: Session, actor: Actor, ticket_id: str) -> Ticket:
    """
    【方法作用】：
        按照工单 ID 与当前登录用户的租户（tenant_id）联合查询可见范围内的工单。
        普通客户（customer）还必须严格是工单的所有者（owner_id），防止水平越权 (IDOR)！

    【参数说明】：
        session (Session): SQLAlchemy 同步数据库会话对象
        actor (Actor): 当前请求的发起者身份（包含 user_id, tenant_id, role）
        ticket_id (str): 工单的全局唯一主键 ID

    【返回值】：
        Ticket: 查到的工单实体模型

    【类似方法与 API 深度对比】：
        1. session.scalars(query).one_or_none() 🌟（当前使用）
           - 作用：期望得到 0 个或 1 个结果。
           - 区别：若查询结果 > 1 条，会立即抛出 MultipleResultsFound 异常，强制报警数据库主键约束失效；
             若未查到，安全返回 None。
        2. session.scalars(query).first()
           - 区别：无论匹配到多少条，永远只拿第 1 条，多余的静默丢弃。
             缺陷是容易掩盖多租户数据错乱的严重脏数据 BUG。
        3. session.scalars(query).one()
           - 区别：严格要求必须正好查出 1 条。没查到抛 NoResultFound，多于 1 条抛 MultipleResultsFound。
        4. session.scalars(query) vs session.execute(query)
           - execute 返回的是由 Row 元组包装的行结果 (Ticket, )，取值需 row[0]；
           - scalars 会自动解包首列，直接将 Ticket 实体对象抛出供你点语法调用。
    """
    # 强制将租户隔离条件植入 SQL WHERE，杜绝通过篡改 ticket_id 窃取其他企业租户数据的风险
    query = select(Ticket).where(Ticket.id == ticket_id, Ticket.tenant_id == actor.tenant_id)
    if actor.role == "customer":
        query = query.where(Ticket.owner_id == actor.user_id)
    
    ticket = session.scalars(query).one_or_none()
    if ticket is None:
        raise TicketNotFound
    return ticket


def create_ticket(session: Session, actor: Actor, question: str, key: str) -> tuple[Ticket, bool]:
    """
    【方法作用】：
        原子级幂等创建工单。
        当客户端（因弱网重试、前端连击）使用同一个幂等键（key）重复发起请求时：
        - 若参数一致：安全复用返回已有工单（不重复插库、不报 500、不生成重复工单）；
        - 若同一个键但问题参数被篡改：抛出 TicketConflict 警告冲突。

    【参数说明】：
        session (Session): 数据库会话
        actor (Actor): 当前提问客户身份
        question (str): 客户提出的售后问题内容
        key (str): 前端生成的幂等键（Idempotency Key，通常由客户端产生 UUID）

    【返回值】：
        tuple[Ticket, bool]: (工单对象, 是否属于首次全新创建)

    【类似方法与架构深度对比】：
        1. on_conflict_do_nothing vs on_conflict_do_update 🌟
           - on_conflict_do_nothing (当前使用)：如果 (tenant_id, owner_id, key) 联合唯一键已存在，
             底层数据库直接略过本次插入，不做任何操作。常用于【防重复创建订单/工单】。
           - on_conflict_do_update (UPSERT)：如果唯一键已存在，执行更新操作覆盖旧字段。
             常用于【知识库文档同步、用户画像更新】。
        2. 事务原子性保证 (All or Nothing)：
           - 工单插入 (Ticket) 与首条审计事件 (TicketEvent) 必须在同一个 Session 事务中；
           - 任何一步失败，整个事务回滚，绝不会出现“工单建了却没有审计记录”的半死状态。
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
    """
    【方法作用】：
        高并发安全的原子状态迁移（将工单从 pending 待审状态转变为 approved/rejected 终态）。
        相同审批员重复提交相同决定时，幂等返回已有工单。

    【参数说明】：
        session (Session): 数据库会话
        actor (Actor): 执行审批的客服/管理员身份
        ticket_id (str): 待审工单 ID
        decision (Status): 审批决定枚举 (Status.APPROVED 或 Status.REJECTED)

    【返回值】：
        Ticket: 审批完成后的最新工单

    【高并发防御：条件更新 vs 先查后改的区别】🌟：
        - ❌ 错误做法（先查后改）：
            ticket = session.get(Ticket, ticket_id)
            if ticket.status == "pending":
                ticket.status = decision
                session.commit()
            缺陷：高并发下两个管理员同时点击审核，两边都会读取到 "pending"，导致两次审核都被执行，审计日志错乱！
        - ✅ 工业级正确做法（当前写法）：
            把 `Ticket.status == Status.PENDING.value` 直接写进 UPDATE 的 WHERE 条件中！
            数据库底层依靠行级排他锁 (Row-level Lock) 保证原子性：
            只要其中一个事务先执行成功，第二个人执行时 WHERE 条件就不再满足，更新行数为 0 (updated_id is None)！
    """
    statement = (
        update(Ticket)
        .where(
            Ticket.id == ticket_id,
            Ticket.tenant_id == actor.tenant_id,
            Ticket.status == Status.PENDING.value,  # 👈 核心行锁条件检查
        )
        .values(status=decision.value, reviewer_id=actor.user_id)
        .returning(Ticket.id)
    )
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
    """
    【方法作用】：
        查询指定工单的全生命周期审计流转记录（如：何时被谁创建、何时被谁通过/驳回）。
        严格先调用 visible_ticket 校验父资源访问权限，杜绝未授权查看审计流。

    【参数说明】：
        session (Session): 数据库会话
        actor (Actor): 请求发起者
        ticket_id (str): 目标工单 ID

    【返回值】：
        list[TicketEvent]: 按时间自增 ID 正序排列的操作事件列表
    """
    ticket = visible_ticket(session, actor, ticket_id)
    return list(session.scalars(select(TicketEvent).where(
        TicketEvent.ticket_id == ticket.id,
    ).order_by(TicketEvent.id)))
