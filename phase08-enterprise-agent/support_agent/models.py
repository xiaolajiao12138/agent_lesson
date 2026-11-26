"""企业实战第 1–2 课｜数据库模型、状态枚举与数据约束。

建议先读 Status，再读 Ticket、TicketEvent，最后读 Document。
Mapped[T] 描述 ORM 属性类型，mapped_column() 描述实际数据库列。
Pydantic 的 Field 用于接口数据校验，数据库列约束由这里的主键、唯一键、外键等承担。
修改模型后通过 Alembic 新增迁移，将相应表结构变更应用到数据库。
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Status(StrEnum):
    """工单状态的字符串枚举。

    Status.PENDING 是枚举成员，Status.PENDING.value 得到 'pending_review'。
    StrEnum 兼具字符串特征，Enum 可以表达更一般的成员类型，Literal 适合直接限定参数值。
    数据库还用 CheckConstraint 限定状态集合，服务重启后状态仍保存在工单表中。
    """
    PENDING = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class Base(DeclarativeBase):
    """SQLAlchemy 声明式模型基类。

    子类定义的表会汇集到 Base.metadata，Alembic 用它对照数据库结构。
    DeclarativeBase 负责 ORM 映射，Pydantic BaseModel 负责接口数据的解析与校验。
    metadata.create_all() 可以创建缺失表，已有表的结构演进由本项目的迁移文件记录。
    """


class Ticket(Base):
    """工单主表，记录租户、所有者、问题、审批状态及审批者。

    __tablename__ 是实际表名，__table_args__ 汇总表级约束。
    租户、所有者和幂等键构成联合唯一约束，配合 workflow.py 处理重复建单。
    Mapped[str | None] 让 reviewer_id 可以为空，表示工单尚无审批者。
    这里声明的是列和约束，单条数据的创建与状态迁移在 workflow.py 中执行。
    """
    __tablename__ = "tickets"
    __table_args__ = (
        # 两个并发请求可能同时发现“没有记录”，所以唯一性由数据库保证。
        UniqueConstraint("tenant_id", "owner_id", "idempotency_key", name="uq_ticket_request"),
        CheckConstraint(
            "status IN ('pending_review', 'approved', 'rejected')",
            name="ck_ticket_status",
        ),
    )

    # Mapped[str] 提供属性类型，String(36) 描述列长度，primary_key=True 声明主键。
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64))
    owner_id: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    # Text 适合正文，String(n) 适合编号等短文本。SQLite 的长度限制还需结合输入校验。
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    reviewer_id: Mapped[str | None] = mapped_column(String(64))
    # server_default 让数据库在 INSERT 时生成时间。default=某个 Python 函数则由 Python 端提供值。
    # timezone=True 表达时区类型意图，具体存储及返回行为取决于数据库方言。
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TicketEvent(Base):
    """工单审计事件表，保存创建和审批动作。

    ForeignKey('tickets.id') 将事件关联到工单，调用方会在同一事务中写入工单及事件。
    整型主键 id 为事件提供排序依据，联合索引支持按 ticket_id 过滤并按 id 排序。
    外键负责关联约束，查询关联数据时仍需在 SQL 中声明条件。
    """
    __tablename__ = "ticket_events"
    __table_args__ = (Index("ix_ticket_events_ticket_id", "ticket_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"))
    actor_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    """知识库文档表，文档标识在租户范围内唯一。

    tenant_id 与 source_id 同时作为主键，因此两个租户可以使用同一个 source_id。
    keywords 以 JSON 文本保存在 Text 列，knowledge.py 负责 dumps/loads 转换。
    visibility 的 CheckConstraint 将值限定为 tenant 或 reviewer，查询阶段按身份裁剪候选文档。
    """
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("visibility IN ('tenant', 'reviewer')", name="ck_document_visibility"),
    )

    # 租户内的文档编号，例如 returns-01。两个租户可以使用相同编号。
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    keywords: Mapped[str] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(16))
