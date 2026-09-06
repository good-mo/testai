# app/repositories/project_app_config_repo.py
"""项目应用配置数据访问层（Phase 3 重构 · 4 层对齐）。

承接原 app.projects.application_config 与 app/routers/project_compat_extra2.py
中对 project_app_configs 表的全部 SQLite 读写，实现 Repository 层下沉：
  - 建表 / 模块配置读取合并默认值 / 配置持久化（upsert）
  - projectVersion 模块启用开关的读写（原散落在路由层的内联 SQL）

数据存储在 projects.db（经 Database 连接池统一解析）。输出形态与旧层完全一致，
保证上层（service / 兼容门面 / 路由）行为零回归。
"""
import time
from typing import Any, Dict, List

from app.core.database import Database
from app.logging_config import get_logger

logger = get_logger(__name__)

# project_app_configs 表的逻辑库名（与旧 application_config 保持一致）
db_name = "projects.db"


def _get_conn():
    """获取数据库连接（统一使用 Database 连接池）。"""
    return Database.get_conn(db_name)


def ensure_tables() -> None:
    """幂等建表（权威 DDL，供 schema_registry / 迁移兜底引用）。"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_app_configs (
            project_id TEXT NOT NULL,
            module TEXT NOT NULL,          -- workstation/testPlan/bugManagement/...
            config_key TEXT NOT NULL,      -- API_CLEAN_REPORT 等
            config_value TEXT DEFAULT '',
            updated_at REAL,
            PRIMARY KEY (project_id, module, config_key)
        )
    """)
    conn.commit()


ensure_tables()


# 每个模块的默认配置
DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
    "workstation": {
        "WORKSTATION_SYNC_RULE": True,
    },
    "testPlan": {
        "TEST_PLAN_CLEAN_REPORT": "3M",
        "TEST_PLAN_SHARE_REPORT": "1D",
    },
    "bugManagement": {
        "BUG_SYNC_SYNC_ENABLE": False,
    },
    "caseManagement": {
        "CASE_RELATED_CASE_ENABLE": False,
        "CASE_RE_REVIEW": True,
        "CASE_PUBLIC": False,
    },
    "apiTest": {
        "API_CLEAN_REPORT": "3M",
        "API_SHARE_REPORT": "1D",
        "API_RESOURCE_POOL_ID": "",
        "API_SCRIPT_REVIEWER_ID": "",
        "API_URL_REPEATABLE": False,
        "API_SYNC_CASE": False,
        "ENABLE_FAKE_ERROR_NUM": 0,
    },
    "uiTest": {
        "UI_CLEAN_REPORT": "3M",
        "UI_SHARE_REPORT": "1D",
        "UI_RESOURCE_POOL_ID": "",
    },
    "taskCenter": {
        "TASK_CLEAN_REPORT": "3M",
        "TASK_RECORD": "3M",
    },
    "loadTest": {
        "PERFORMANCE_TEST_CLEAN_REPORT": "3M",
        "PERFORMANCE_TEST_SHARE_REPORT": "1D",
        "PERFORMANCE_TEST_SCRIPT_REVIEWER_ID": "",
        "PERFORMANCE_TEST_SCRIPT_REVIEWER_ENABLE": False,
    },
}

# 模块名称（菜单管理列表）
MODULES: List[Dict[str, Any]] = [
    {"module": "workstation", "moduleEnable": True},
    {"module": "testPlan", "moduleEnable": True},
    {"module": "bugManagement", "moduleEnable": True},
    {"module": "caseManagement", "moduleEnable": True},
    {"module": "apiTest", "moduleEnable": True},
    {"module": "taskCenter", "moduleEnable": True},
    {"module": "uiTest", "moduleEnable": True},
    {"module": "loadTest", "moduleEnable": True},
]


def _serialize(value: Any) -> str:
    """将配置值序列化为文本存储。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _deserialize(value: str, default: Any) -> Any:
    """将存储的文本反序列化为原始类型。"""
    if isinstance(default, bool):
        return value == "true"
    if isinstance(default, int):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    return value


def _read_config_rows(project_id: str, module: str) -> Dict[str, str]:
    """读取某 project+module 下全部已持久化的 config_key->config_value。"""
    conn = _get_conn()
    rows = {}
    try:
        cur = conn.execute(
            "SELECT config_key, config_value FROM project_app_configs WHERE project_id=? AND module=?",
            (project_id, module),
        )
        rows = {r["config_key"]: r["config_value"] for r in cur.fetchall()}
    except Exception as e:
        logger.warning("project_app_configs 读取失败: %s", e)
    return rows


def get_module_config(project_id: str, module: str) -> Dict[str, Any]:
    """获取某模块的配置（合并默认值）。"""
    defaults = DEFAULT_CONFIG.get(module, {})
    rows = _read_config_rows(project_id, module)
    result: Dict[str, Any] = {}
    # 先填默认值
    for key, default in defaults.items():
        result[key] = _deserialize(rows[key], default) if key in rows else default
    # 再合并已存储的自定义 key（不在默认配置中但已持久化的项）
    for key, raw in rows.items():
        if key not in result:
            result[key] = _deserialize(raw, "")
    return result


def save_module_config(project_id: str, module: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """保存某模块的配置。config 为 {key: value}，upsert 至 project_app_configs。"""
    defaults = DEFAULT_CONFIG.get(module, {})
    now = time.time()
    conn = _get_conn()
    try:
        for key, value in config.items():
            # 保留原默认类型推断：默认不存在时按实际值类型序列化
            default = defaults.get(key)
            if default is None:
                default = True if isinstance(value, bool) else (
                    int if isinstance(value, (int, float)) else "")
            serialized = _serialize(value)
            conn.execute(
                """
                INSERT INTO project_app_configs (project_id, module, config_key, config_value, updated_at)
                VALUES (?,?,?,?,?)
                ON CONFLICT(project_id, module, config_key) DO UPDATE SET config_value=excluded.config_value, updated_at=excluded.updated_at
                """,
                (project_id, module, key, serialized, now),
            )
        conn.commit()
    except Exception as e:
        logger.warning("project_app_configs 写入失败: %s", e)
    return get_module_config(project_id, module)


def get_all_modules(project_id: str) -> List[Dict[str, Any]]:
    """返回菜单管理列表（顶层模块）。project_id 目前未参与数据读取。"""
    return [dict(m) for m in MODULES]


# ── projectVersion 模块启用开关（供项目版本功能使用）───────────
def get_config_value(project_id: str, module: str, config_key: str,
                     default: str = "") -> str:
    """读取单条原始配置值（未反序列化）。不存在返回 default。"""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT config_value FROM project_app_configs WHERE project_id=? AND module=? AND config_key=?",
            (project_id, module, config_key),
        ).fetchone()
        if row:
            return str(row[0])
    except Exception as e:
        logger.warning("project_app_configs 单值读取失败: %s", e)
    return default


def set_config_value(project_id: str, module: str, config_key: str,
                     value: Any, updated_at: float = None) -> None:
    """写入单条配置（INSERT OR REPLACE）。"""
    conn = _get_conn()
    ts = updated_at if updated_at is not None else time.time()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO project_app_configs (project_id, module, config_key, config_value, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, module, config_key, _serialize(value), ts),
        )
        conn.commit()
    except Exception as e:
        logger.warning("project_app_configs 单值写入失败: %s", e)


# ── 兼容别名 ─────────────────────────────────────────────
def _init_tables() -> None:
    """兼容旧模块导入：委托 ensure_tables。"""
    ensure_tables()


__all__ = [
    "ensure_tables",
    "get_module_config",
    "save_module_config",
    "get_all_modules",
    "get_config_value",
    "set_config_value",
    "DEFAULT_CONFIG",
    "MODULES",
    "db_name",
]
