"""Alembic 环境配置。

项目采用原生 SQLite（无 SQLAlchemy ORM 模型），
因此不依赖 autogenerate，迁移脚本以 op.execute(raw_sql) 手工编写。
基线迁移 (0001) 从 app.core.schema_registry 导入全部 DDL。

可通过环境变量 TGA_DB_PATH 指定目标数据库文件（测试用）。
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# 将项目根目录加入 sys.path（确保可以 import app.*）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 统一数据库：业务数据全部落 tga.db（见 app/db.py resolve_db_name）
# 支持通过环境变量 TGA_DB_PATH 覆盖（测试 / 临时环境）
TGA_DB_PATH = os.environ.get("TGA_DB_PATH",
                             os.path.join(PROJECT_ROOT, "tga.db"))

config = context.config

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 不使用 autogenerate（无 ORM 模型）
target_metadata = None


def _get_url() -> str:
    """返回 SQLAlchemy URL。"""
    return f"sqlite:///{TGA_DB_PATH}"


def run_migrations_offline() -> None:
    """以 offline 模式运行迁移（生成 SQL 而非执行）。"""
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """以 online 模式运行迁移。"""
    connectable = create_engine(_get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
