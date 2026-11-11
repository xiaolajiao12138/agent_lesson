"""企业实战第 1–2 课｜把业务状态、资源边界与数据约束落进表结构。"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Status(StrEnum):
    PENDING = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class Base(DeclarativeBase):
    """每个继承类的表定义都会注册到 Base.metadata，供 Alembic 比较。"""


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        # 两个并发请求可能同时发现“没有记录”，所以唯一性由数据库保证。
        UniqueConstraint("tenant_id", "owner_id", "idempotency_key", name="uq_ticket_request"),
        CheckConstraint(
            "status IN ('pending_review', 'approved', 'rejected')", name="ck_ticket_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64))
    owner_id: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    reviewer_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TicketEvent(Base):
    __tablename__ = "ticket_events"
    __table_args__ = (Index("ix_ticket_events_ticket_id", "ticket_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id"))
    actor_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
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
