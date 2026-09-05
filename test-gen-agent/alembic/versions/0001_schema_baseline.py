"""
Schema 基线（Phase D · Alembic 迁移基线）

收集全仓 CREATE TABLE 声明到迁移基线。
本迁移基于 app.core.schema_registry 生成，仅用于初始化新库。

Revision ID: 0001_schema_baseline
Revises: None
Create Date: 2026-09-03

执行策略：
  - 只对「不存在的表」执行 CREATE TABLE（IF NOT EXISTS 语义）
  - 同名多版本表（如 api_definitions）取更完整的权威定义

注意：
  1. 本迁移是针对 tga.db（统一库）。
  2. 生成后如后续调整表结构，通过新迁移文件演进，
     不应再回到此文件修改已定义的表。
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_schema_baseline"
down_revision = None
branch_labels = None
depends_on = None


# 从 schema_registry 导入 DDL 定义
from app.core.schema_registry import (
    TABLE_DDL,
    TABLE_DDL_ALL,
)

# 需要跳过的表（独立库/由外部管理）
# checkpoints / writes 等不在 tga.db 建表
_SKIP_TABLES = {
    "checkpoints",    # LangGraph checkpoints.db
    "writes",         # LangGraph writes
}


def upgrade() -> None:
    """创建全部业务表。"""

    for table_name in sorted(TABLE_DDL_ALL.keys()):
        if table_name in _SKIP_TABLES:
            continue

        # 同名多版本：取 TABLE_DDL（默认 V1 = 第一来源）
        ddl = TABLE_DDL.get(table_name, "")
        if not ddl:
            continue

        op.execute(ddl)


def downgrade() -> None:
    """回滚：删除所有由本迁移创建的表。"""
    from sqlalchemy import inspect

    from alembic import context

    bind = context.get_bind()
    inspector = inspect(bind)
    existing = {t for t in inspector.get_table_names()}

    for table_name in sorted(TABLE_DDL_ALL.keys()):
        if table_name in _SKIP_TABLES:
            continue
        if table_name in existing:
            op.execute(f"DROP TABLE IF EXISTS {table_name}")

