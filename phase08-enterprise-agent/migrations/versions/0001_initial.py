"""企业实战第 2 课｜初始数据库结构的版本快照。

alembic upgrade head 通过 env.py 调用 upgrade()，执行创建工单、事件及文档表。
revision 是本次版本号，down_revision=None 表示本分支的起点。
本文件保留该版本的结构，后续表变更应新增 revision，让旧数据库有可执行的升级路径。
op 提供迁移操作，sa.Column 等显式描述版本当时的列类型与约束。
"""

from alembic import op
import sqlalchemy as sa

# Alembic 根据这些固定名称构建版本依赖图；值是本课程初始版本的标识。
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建当前初始版本的全部业务表及审计查询索引。

    op.create_table() 创建实际表，sa.Column() 描述列，nullable=False 要求列值非空。
    UniqueConstraint 约束业务幂等组合键，CheckConstraint 约束状态或可见性值集合。
    ForeignKey 将事件指向工单，因此先创建 tickets，再创建 ticket_events。
    server_default=sa.func.now() 在写入时由数据库生成创建时间。
    这与 Base.metadata.create_all() 一样可涉及建表，Alembic 还会记录版本及后续迁移路径。
    """
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
    # 普通索引辅助查询性能，唯一约束还会额外限制重复数据。
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
    """回退初始版本所创建的结构，会删除课程表及其中记录。

    先删除子表及关联索引，再删除被引用的 tickets，遵循外键依赖顺序。
    op.drop_table() 删除表结构，业务中的 delete(Document) 删除特定表内的匹配记录。
    回退应在确认目标环境和数据影响后执行，常规启动只执行 upgrade head。
    """
    op.drop_table("documents")
    op.drop_index("ix_ticket_events_ticket_id", table_name="ticket_events")
    op.drop_table("ticket_events")
    op.drop_table("tickets")
