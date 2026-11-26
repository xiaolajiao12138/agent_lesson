"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""
# 企业实战第 2 课的迁移生成模板，alembic revision 会使用本文件创建新版本。
# 美元符号和花括号中的内容是 Mako 模板表达式，生成时会替换为版本号、导入或 SQL 操作。
from alembic import op
import sqlalchemy as sa
${imports if imports else ''}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    # 升级函数保存这个版本新增的结构操作，自动生成后仍需核对变更内容。
    ${upgrades if upgrades else 'pass'}


def downgrade() -> None:
    # 回退函数保存反向结构操作，需要核对依赖顺序及数据影响。
    ${downgrades if downgrades else 'pass'}
