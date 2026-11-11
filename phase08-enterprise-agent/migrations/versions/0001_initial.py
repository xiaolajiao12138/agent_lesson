"""创建工单、审计事件和知识库。迁移文件保留当时的结构定义。"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("owner_id", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reviewer_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "owner_id", "idempotency_key", name="uq_ticket_request"),
        sa.CheckConstraint("status IN ('pending_review', 'approved', 'rejected')", name="ck_ticket_status"),
    )
    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id", sa.String(36), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ticket_events_ticket_id", "ticket_events", ["ticket_id", "id"])
    op.create_table(
        "documents",
        sa.Column("tenant_id", sa.String(64), primary_key=True),
        sa.Column("source_id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(16), nullable=False),
        sa.CheckConstraint("visibility IN ('tenant', 'reviewer')", name="ck_document_visibility"),
    )


def downgrade() -> None:
    # 审计事件引用工单，回退时先删除子表。此版本回退会丢弃课程数据。
    op.drop_table("documents")
    op.drop_index("ix_ticket_events_ticket_id", table_name="ticket_events")
    op.drop_table("ticket_events")
    op.drop_table("tickets")
