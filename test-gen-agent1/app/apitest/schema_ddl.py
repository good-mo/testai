# -*- coding: utf-8 -*-
"""api_definitions 表权威 DDL（单一真源）。

背景
----
历史上 app.api_testing.management（V1 前端兼容层）与 app.apitest.store
（V2 主引擎）各自持有一份 ``CREATE TABLE api_definitions``，两份列集合不同：

  - 先被 import 的一侧决定物理列结构；
  - 另一侧靠 ``_ensure_column`` / ``_ensure_api_columns`` 补列；

结果是「注册表与实际建表漂移」——schema_registry 里同一个表名有 2 个物理版本，
CI 的 schema 冲突检测长期报警，且任何一处补列漏写都会在运行期炸出
``no such column``（实测：module_id 列谁都没建，但 list_definitions 的
module_ids 过滤在用，前端按模块筛选接口列表直接 500）。

收敛方式
--------
  1. 权威 DDL 只在本模块保留一份字面量，物理结构 = V1 ∪ V2 ∪ 运行期实际
     使用列（module_id），不再由 import 顺序决定；
  2. 两侧建表统一调用 :func:`ensure_api_definitions_table`，
     存量库通过 ALTER 补齐缺失列（列定义直接从 DDL 字面量解析，
     不存在第二份列清单需要同步）；
  3. ``scripts/sync_schema_registry.py`` 扫描到的 api_definitions 来源
     因此收敛为 1 个，冲突自然消除。

本模块不 import 任何业务模块，避免循环依赖。
"""
import re
import sqlite3
from typing import Optional

from app.core.database import Database
from app.logging_config import get_logger

logger = get_logger(__name__)

__all__ = [
    "API_DEFINITIONS_DDL",
    "API_DEFINITIONS_INDEXES",
    "api_definitions_columns",
    "ensure_api_definitions_table",
]

# ── 权威 DDL ─────────────────────────────────────────────────
# V1(列 request_*/response_*) + V2(列 headers/body/query/params/version_id/
# ref_id/latest/metadata/project_id) + 运行期使用列(module_id) 的超集。
# 顺序上 V2 主引擎列在前，V1 兼容层列在后，module_id 兜底追加。
API_DEFINITIONS_DDL = """
CREATE TABLE IF NOT EXISTS api_definitions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    protocol TEXT DEFAULT 'HTTP',      -- HTTP/TCP/SQL/DUBBO
    method TEXT DEFAULT 'GET',
    path TEXT DEFAULT '',
    headers TEXT DEFAULT '{}',         -- V2 请求头（apitest 主引擎）
    body TEXT DEFAULT '',
    query TEXT DEFAULT '{}',
    params TEXT DEFAULT '{}',
    description TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    module_id TEXT DEFAULT '',         -- 所属模块（模块树筛选，空=root）
    project_id TEXT DEFAULT '',
    version_id TEXT DEFAULT '',
    ref_id TEXT DEFAULT '',
    latest INTEGER DEFAULT 1,          -- 是否为最新版本
    created_at REAL,
    updated_at REAL,
    metadata TEXT DEFAULT '{}',
    deleted INTEGER DEFAULT 0,
    deleted_at REAL,
    -- V1 字段（api_testing 前端兼容层）
    request_headers TEXT DEFAULT '{}',
    request_params TEXT DEFAULT '{}',
    request_body TEXT DEFAULT '',
    request_body_type TEXT DEFAULT 'json',
    response_code TEXT DEFAULT '200',
    response_headers TEXT DEFAULT '{}',
    response_body TEXT DEFAULT '',
    response_body_type TEXT DEFAULT 'json',
    created_by TEXT DEFAULT 'system'
)
"""

# 索引：两侧历史实现各建过一部分，这里统一收口，全部 IF NOT EXISTS
API_DEFINITIONS_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_defs_project ON api_definitions(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_defs_ref ON api_definitions(ref_id)",
    "CREATE INDEX IF NOT EXISTS idx_defs_module ON api_definitions(module_id)",
    "CREATE INDEX IF NOT EXISTS idx_api_defs_name ON api_definitions(name)",
    "CREATE INDEX IF NOT EXISTS idx_api_defs_path ON api_definitions(path)",
)

# 表级约束关键字：切分列定义时需要跳过
_CONSTRAINT_KEYWORDS = {"PRIMARY", "UNIQUE", "FOREIGN", "CHECK", "CONSTRAINT"}


def _strip_sql_comments(sql: str) -> str:
    """去掉 SQL 中的行注释（-- ...），避免注释里的逗号/括号干扰切分。"""
    return re.sub(r"--[^\n]*", "", sql)


def api_definitions_columns() -> list:
    """从权威 DDL 解析出 [(列名, 列定义), ...]。

    列定义直接来自 DDL 字面量，存量库补列时无需再维护第二份列清单，
    从根上消除「DDL 改了、_ensure_column 没跟着改」的漂移。
    """
    inner = API_DEFINITIONS_DDL[
        API_DEFINITIONS_DDL.index("(") + 1: API_DEFINITIONS_DDL.rindex(")")
    ]
    inner = _strip_sql_comments(inner)

    parts, depth, cur = [], 0, ""
    for ch in inner:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())

    columns = []
    for part in parts:
        definition = " ".join(part.split())
        if not definition:
            continue
        name = definition.split()[0].strip('`"')
        if name.upper() in _CONSTRAINT_KEYWORDS:
            continue
        columns.append((name, definition))
    return columns


def ensure_api_definitions_table(conn: Optional[sqlite3.Connection] = None) -> None:
    """按权威 DDL 建表，并把存量库补齐到同一列集合。

    幂等：新建库直接与权威 DDL 一致；存量库按缺失列 ALTER ADD COLUMN。
    未显式传 conn 时统一走 Database 连接池的 apitest.db。
    """
    if conn is None:
        conn = Database.get_conn("apitest.db")
    conn.execute(API_DEFINITIONS_DDL)
    existing = {row[1] for row in conn.execute("PRAGMA table_info(api_definitions)")}
    for name, definition in api_definitions_columns():
        if name in existing:
            continue
        try:
            conn.execute(f"ALTER TABLE api_definitions ADD COLUMN {definition}")
        except Exception as exc:  # pragma: no cover - 极端存量库才可能失败
            logger.warning("api_definitions 补列失败 [col=%s, err=%s]", name, exc)
    for index_ddl in API_DEFINITIONS_INDEXES:
        conn.execute(index_ddl)
    conn.commit()
