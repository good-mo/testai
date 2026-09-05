"""数据访问层：统一管理所有数据库操作。

导出：
  - BaseRepo           统一 CRUD 基类
  - interface          域 Repository 协议与注册表
  - schema_registry    表结构声明注册处（Phase D）
"""

from app.core.schema_registry import (
    TABLE_DDL,
    TABLE_DDL_ALL,
    TABLE_SOURCES,
    audit_all_schemas,
    ensure_schema_consistent,
    get_table_ddl,
    list_all_tables,
)
from app.repositories.base import BaseRepo
from app.repositories.interface import (
    DOMAIN_REPOSITORIES,
    ApitestRepositoryProtocol,
    BaseRepository,
    CrudRepositoryProtocol,
    get_domain_repository,
    register_domain_repository,
)

__all__ = [
    "BaseRepo",
    "BaseRepository",
    "ApitestRepositoryProtocol",
    "CrudRepositoryProtocol",
    "DOMAIN_REPOSITORIES",
    "register_domain_repository",
    "get_domain_repository",
    "TABLE_DDL",
    "TABLE_DDL_ALL",
    "TABLE_SOURCES",
    "get_table_ddl",
    "list_all_tables",
    "ensure_schema_consistent",
    "audit_all_schemas",
]
