# app/apitest/store.py
"""接口测试数据持久化层（基于 SQLite）

统一管理接口定义、接口用例、场景编排、Mock 服务、环境配置等数据的存储。
支持：
- 项目/多租户维度（project_id）
- 版本管理（versionId/refId/latest）
- 回收站机制（软删除→回收站→恢复）
- 操作日志/审计
"""
import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger

logger = get_logger(__name__)

# 统一使用 Database 连接池管理
from app.apitest.schema_ddl import ensure_api_definitions_table
from app.core.database import Database

# 模块级缓存连接，避免每次操作新建/关闭 SQLite 连接

def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（统一使用 Database 连接池）。"""
    return Database.get_conn("apitest.db")


def _ensure_column(conn, table: str, column: str, definition: str) -> None:
    """确保表中存在指定列，不存在则添加。"""
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except Exception as e:
            logger.warning("添加列失败 [table=%s, col=%s, err=%s]", table, column, e)


def _init_db() -> None:
    """初始化接口测试库表结构（使用独立临时连接）。"""
    conn = _get_conn()
    try:
        # 接口定义
        # 注意：app.api_testing.management（V1 前端兼容层）与本模块（V2 主引擎）
        # 共用同一张 api_definitions 表。历史实现是两边各写一份 CREATE TABLE，
        # 由 import 顺序决定物理列结构，导致注册表里同表名出现 2 个物理版本。
        # 现统一走权威 DDL（app/apitest/schema_ddl.py）：列集合 = V1 ∪ V2 超集，
        # 存量库按 DDL 解析出的列清单 ALTER 补齐，不再维护第二份补列清单。
        ensure_api_definitions_table(conn)

        # 接口用例
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_cases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                api_definition_id TEXT DEFAULT '',
                request TEXT DEFAULT '{}',        -- 请求体（覆盖定义）
                asserts TEXT DEFAULT '[]',        -- 断言规则列表
                pre_scripts TEXT DEFAULT '[]',    -- 前置脚本
                post_scripts TEXT DEFAULT '[]',   -- 后置脚本
                pre_sql TEXT DEFAULT '[]',        -- 前置 SQL
                post_sql TEXT DEFAULT '[]',       -- 后置 SQL
                variables TEXT DEFAULT '[]',      -- 变量提取
                logic_controllers TEXT DEFAULT '[]',  -- 逻辑控制器
                environment_id TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                priority TEXT DEFAULT 'P2',
                description TEXT DEFAULT '',
                project_id TEXT DEFAULT '',
                created_at REAL,
                updated_at REAL,
                metadata TEXT DEFAULT '{}',
                deleted INTEGER DEFAULT 0,
                deleted_at REAL
            )
        """)
        _ensure_column(conn, "api_cases", "project_id", "TEXT DEFAULT ''")
        _ensure_column(conn, "api_cases", "deleted", "INTEGER DEFAULT 0")
        _ensure_column(conn, "api_cases", "deleted_at", "REAL")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cases_project ON api_cases(project_id)
        """)

        # 接口场景
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_scenarios (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                steps TEXT DEFAULT '[]',          -- 编排步骤（有序）
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                environment_id TEXT DEFAULT '',
                project_id TEXT DEFAULT '',
                created_at REAL,
                updated_at REAL,
                metadata TEXT DEFAULT '{}',
                deleted INTEGER DEFAULT 0,
                deleted_at REAL
            )
        """)
        _ensure_column(conn, "api_scenarios", "project_id", "TEXT DEFAULT ''")
        _ensure_column(conn, "api_scenarios", "deleted", "INTEGER DEFAULT 0")
        _ensure_column(conn, "api_scenarios", "deleted_at", "REAL")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scenarios_project ON api_scenarios(project_id)
        """)

        # Mock 服务
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_mocks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                api_definition_id TEXT DEFAULT '',
                method TEXT DEFAULT 'GET',
                path TEXT DEFAULT '',
                status_code INTEGER DEFAULT 200,
                response_body TEXT DEFAULT '',
                response_headers TEXT DEFAULT '{}',
                delay_ms INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1,
                description TEXT DEFAULT '',
                project_id TEXT DEFAULT '',
                match_type TEXT DEFAULT 'exact',   -- exact/path/wildcard/script
                match_script TEXT DEFAULT '',       -- 复杂匹配脚本
                created_at REAL,
                updated_at REAL,
                deleted INTEGER DEFAULT 0,
                deleted_at REAL
            )
        """)
        _ensure_column(conn, "api_mocks", "project_id", "TEXT DEFAULT ''")
        _ensure_column(conn, "api_mocks", "match_type", "TEXT DEFAULT 'exact'")
        _ensure_column(conn, "api_mocks", "match_script", "TEXT DEFAULT ''")
        _ensure_column(conn, "api_mocks", "deleted", "INTEGER DEFAULT 0")
        _ensure_column(conn, "api_mocks", "deleted_at", "REAL")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_mocks_project ON api_mocks(project_id)
        """)

        # 环境管理
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_environments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                base_url TEXT DEFAULT '',
                headers TEXT DEFAULT '{}',
                variables TEXT DEFAULT '{}',
                description TEXT DEFAULT '',
                project_id TEXT DEFAULT '',
                script TEXT DEFAULT '',           -- 环境前置脚本
                database_config TEXT DEFAULT '{}', -- 数据库驱动配置
                config TEXT DEFAULT '{}',          -- 前端完整 EnvDetailItem 配置
                deleted INTEGER DEFAULT 0,         -- 0: 正常, 1: 已删除(回收站)
                deleted_at REAL,
                created_at REAL,
                updated_at REAL
            )
        """)
        _ensure_column(conn, "api_environments", "project_id", "TEXT DEFAULT ''")
        _ensure_column(conn, "api_environments", "script", "TEXT DEFAULT ''")
        _ensure_column(conn, "api_environments", "database_config", "TEXT DEFAULT '{}'")
        _ensure_column(conn, "api_environments", "config", "TEXT DEFAULT '{}'")
        _ensure_column(conn, "api_environments", "deleted", "INTEGER DEFAULT 0")
        _ensure_column(conn, "api_environments", "deleted_at", "REAL")
        # 环境组表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS env_groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                project_id TEXT DEFAULT '',
                env_group_project TEXT DEFAULT '[]',
                pos INTEGER DEFAULT 0,
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_env_groups_project ON env_groups(project_id)
        """)
        # 全局参数表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS global_params (
                id TEXT PRIMARY KEY,
                project_id TEXT DEFAULT '',
                headers TEXT DEFAULT '[]',
                common_variables TEXT DEFAULT '[]',
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_global_params_project ON global_params(project_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_envs_project ON api_environments(project_id)
        """)

        # 操作日志表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_operation_logs (
                id TEXT PRIMARY KEY,
                resource_type TEXT DEFAULT '',   -- definition/case/scenario/mock/environment
                resource_id TEXT DEFAULT '',
                resource_name TEXT DEFAULT '',
                action TEXT DEFAULT '',          -- create/update/delete/restore/recover/version
                operator TEXT DEFAULT '',
                detail TEXT DEFAULT '{}',
                project_id TEXT DEFAULT '',
                created_at REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_resource ON api_operation_logs(resource_type, resource_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_project ON api_operation_logs(project_id)
        """)

        # 版本表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_definition_versions (
                id TEXT PRIMARY KEY,
                ref_id TEXT DEFAULT '',          -- 版本分组 ID（同一接口的多个版本共享）
                definition_id TEXT DEFAULT '',
                version TEXT DEFAULT 'v1',       -- 版本号
                version_id TEXT DEFAULT '',       -- 对应版本 ID
                snapshot TEXT DEFAULT '{}',       -- 版本快照
                created_at REAL,
                created_by TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_versions_ref ON api_definition_versions(ref_id)
        """)

        conn.commit()
    finally:
        # 不关闭共享连接：由 Database 连接池统一管理，避免破坏连接复用
        pass


_init_db()


def _now() -> float:
    return time.time()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    for key in ("headers", "query", "params", "metadata", "response_headers", "variables",
                "database_config", "snapshot"):
        if key in data and isinstance(data[key], str):
            try:
                data[key] = json.loads(data[key])
            except (json.JSONDecodeError, TypeError):
                data[key] = {}
    for key in ("tags", "asserts", "pre_scripts", "post_scripts", "pre_sql",
                "post_sql", "variables", "logic_controllers", "steps", "detail"):
        if key in data and isinstance(data[key], str):
            try:
                data[key] = json.loads(data[key])
            except (json.JSONDecodeError, TypeError):
                data[key] = []
    return data


def _log_operation(resource_type: str, resource_id: str, resource_name: str,
                   action: str, operator: str = "", detail: dict = None,
                   project_id: str = "") -> None:
    """记录操作日志。"""
    try:
        conn = _get_conn()
        conn.execute("""
            INSERT INTO api_operation_logs
            (id, resource_type, resource_id, resource_name, action, operator,
             detail, project_id, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (_new_id(), resource_type, resource_id, resource_name, action, operator,
              json.dumps(detail or {}, ensure_ascii=False), project_id, _now()))
        conn.commit()
    except Exception as e:
        logger.warning("记录操作日志失败 [err=%s]", e)


def list_operation_logs(resource_type: str = "", resource_id: str = "",
                        project_id: str = "", limit: int = 100,
                        offset: int = 0, **kwargs) -> List[Dict[str, Any]]:
    """列出操作日志（仓库内直连 SQL 已下沉）。"""
    from app.repositories.apitest_repo import ApitestRepo
    return ApitestRepo.list_operation_logs(
        resource_type=resource_type, resource_id=resource_id,
        project_id=project_id, limit=limit, offset=offset, **kwargs,
    )


def count_operation_logs(resource_type: str = "", resource_id: str = "",
                         project_id: str = "") -> int:
    """统计操作日志条数（仓库内直连 SQL 已下沉）。"""
    from app.repositories.apitest_repo import ApitestRepo
    return ApitestRepo.count_operation_logs(
        resource_type=resource_type, resource_id=resource_id,
        project_id=project_id,
    )


def clear_operation_logs(days: int = 30) -> int:
    """清理指定天数之前的操作日志（仓库内直连 SQL 已下沉）。"""
    from app.repositories.apitest_repo import ApitestRepo
    return ApitestRepo.clear_operation_logs(days=days)


# ── 通用 CRUD 辅助 ─────────────────────────────────────────
def _insert(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    cols = ", ".join(data.keys())
    marks = ", ".join(["?"] * len(data))
    conn = _get_conn()
    conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", list(data.values()))
    conn.commit()
    return data


def _update(table: str, item_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sets = ", ".join([f"{k} = ?" for k in data.keys()])
    conn = _get_conn()
    cur = conn.execute(f"UPDATE {table} SET {sets} WHERE id = ?",
                       list(data.values()) + [item_id])
    conn.commit()
    if cur.rowcount == 0:
        return None
    return data


def _delete(table: str, item_id: str) -> bool:
    conn = _get_conn()
    cur = conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
    conn.commit()
    return cur.rowcount > 0


def _get(table: str, item_id: str, include_deleted: bool = True) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
    return _row_to_dict(row) if row else None


def _list(table: str, keyword: str = "", limit: int = 100, offset: int = 0,
          order_by: str = "created_at DESC", project_id: str = "") -> List[Dict[str, Any]]:
    conn = _get_conn()
    if keyword:
        if project_id:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE name LIKE ? AND (project_id = ? OR project_id = '') "
                f"AND (deleted IS NULL OR deleted = 0) ORDER BY {order_by} LIMIT ? OFFSET ?",
                (f"%{keyword}%", project_id, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE name LIKE ? AND (deleted IS NULL OR deleted = 0) "
                f"ORDER BY {order_by} LIMIT ? OFFSET ?",
                (f"%{keyword}%", limit, offset),
            ).fetchall()
    else:
        if project_id:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE (project_id = ? OR project_id = '') "
                f"AND (deleted IS NULL OR deleted = 0) ORDER BY {order_by} LIMIT ? OFFSET ?",
                (project_id, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE (deleted IS NULL OR deleted = 0) "
                f"ORDER BY {order_by} LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _count(table: str, project_id: str = "") -> int:
    conn = _get_conn()
    if project_id:
        row = conn.execute(
            f"SELECT COUNT(*) AS c FROM {table} WHERE (project_id = ? OR project_id = '') "
            f"AND (deleted IS NULL OR deleted = 0)",
            (project_id,),
        ).fetchone()
    else:
        row = conn.execute(
            f"SELECT COUNT(*) AS c FROM {table} WHERE (deleted IS NULL OR deleted = 0)"
        ).fetchone()
    return row["c"]
