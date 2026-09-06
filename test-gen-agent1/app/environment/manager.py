"""
环境状态可视化 + 容器环境拉起 + 告警模块
====================================
提供：
  - 环境注册与状态追踪（在线/离线/异常/维护中）
  - 容器环境一键拉起（基于 Docker Compose / 单容器）
  - 环境告警（健康检查失败、资源超限、服务异常自动触发通知）
"""
import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger

logger = get_logger(__name__)

# 统一使用 Database 连接池管理
from app.core.database import Database

# 环境状态
ENV_STATUS_ONLINE = "online"
ENV_STATUS_OFFLINE = "offline"
ENV_STATUS_ERROR = "error"
ENV_STATUS_MAINTENANCE = "maintenance"
ENV_STATUS_LAUNCHING = "launching"

VALID_STATUSES = {
    ENV_STATUS_ONLINE, ENV_STATUS_OFFLINE,
    ENV_STATUS_ERROR, ENV_STATUS_MAINTENANCE,
    ENV_STATUS_LAUNCHING,
}

# 告警级别
ALERT_LEVEL_INFO = "info"
ALERT_LEVEL_WARNING = "warning"
ALERT_LEVEL_CRITICAL = "critical"

VALID_ALERT_LEVELS = {ALERT_LEVEL_INFO, ALERT_LEVEL_WARNING, ALERT_LEVEL_CRITICAL}



def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（统一使用 Database 连接池）。"""
    return Database.get_conn("environments.db")


def _init_db() -> None:
    """初始化表结构（使用独立临时连接）。"""
    conn = _get_conn()
    try:
        # 环境表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS environments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                env_type TEXT DEFAULT 'docker',
                status TEXT DEFAULT 'offline',
                endpoint TEXT DEFAULT '',
                docker_compose_path TEXT DEFAULT '',
                container_name TEXT DEFAULT '',
                image TEXT DEFAULT '',
                health_check_url TEXT DEFAULT '',
                owner TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                last_checked_at REAL,
                last_status_change REAL,
                error_message TEXT DEFAULT '',
                created_at REAL,
                updated_at REAL,
                deleted INTEGER DEFAULT 0,
                deleted_at REAL,
                project_id TEXT DEFAULT '',      -- 所属项目
                base_url TEXT DEFAULT '',        -- 基础 URL（兼容 api_environments 风格）
                headers TEXT DEFAULT '{}',       -- 默认请求头
                variables TEXT DEFAULT '{}',     -- 全局变量
                is_default INTEGER DEFAULT 0     -- 是否默认环境
            )
        """)
        # 迁移：为历史库补充软删除列
        cols = [r[1] for r in conn.execute("PRAGMA table_info(environments)").fetchall()]
        # 补充所有可能缺失的列
        _all_migrations = {
            "deleted": "INTEGER DEFAULT 0",
            "deleted_at": "REAL",
            "env_type": "TEXT DEFAULT 'docker'",
            "status": "TEXT DEFAULT 'offline'",
            "endpoint": "TEXT DEFAULT ''",
            "docker_compose_path": "TEXT DEFAULT ''",
            "container_name": "TEXT DEFAULT ''",
            "image": "TEXT DEFAULT ''",
            "health_check_url": "TEXT DEFAULT ''",
            "owner": "TEXT DEFAULT ''",
            "tags": "TEXT DEFAULT '[]'",
            "last_checked_at": "REAL",
            "last_status_change": "REAL",
            "error_message": "TEXT DEFAULT ''",
            "project_id": "TEXT DEFAULT ''",
            "base_url": "TEXT DEFAULT ''",
            "headers": "TEXT DEFAULT '{}'",
            "variables": "TEXT DEFAULT '{}'",
            "is_default": "INTEGER DEFAULT 0",
        }
        for col, definition in _all_migrations.items():
            if col not in cols:
                try:
                    conn.execute(f"ALTER TABLE environments ADD COLUMN {col} {definition}")
                    cols.append(col)
                except Exception:
                    pass
        # 告警记录表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                env_id TEXT,
                env_name TEXT DEFAULT '',
                level TEXT DEFAULT 'warning',
                message TEXT DEFAULT '',
                detail TEXT DEFAULT '',
                status TEXT DEFAULT 'open',
                created_at REAL,
                resolved_at REAL
            )
        """)
        conn.commit()
    finally:
        pass  # shared cached conn


_init_db()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    for k in ("tags",):
        if data.get(k):
            try:
                data[k] = json.loads(data[k])
            except (json.JSONDecodeError, TypeError):
                pass
    return data


# ═══════════════════════════════════════════════════════════
# 环境 CRUD
# ═══════════════════════════════════════════════════════════

def register_environment(
    name: str,
    description: str = "",
    env_type: str = "docker",
    endpoint: str = "",
    docker_compose_path: str = "",
    container_name: str = "",
    image: str = "",
    health_check_url: str = "",
    owner: str = "",
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """注册新环境。"""
    env_id = uuid.uuid4().hex[:12]
    now = time.time()
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO environments
               (id, name, description, env_type, status, endpoint,
                docker_compose_path, container_name, image,
                health_check_url, owner, tags, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (env_id, name, description, env_type, ENV_STATUS_OFFLINE,
             endpoint, docker_compose_path, container_name, image,
             health_check_url, owner, json.dumps(tags or []), now, now),
        )
        conn.commit()
        logger.info("环境已注册 [id=%s, name=%s]", env_id, name)
        return get_environment(env_id) or {"id": env_id}
    finally:
        pass  # shared cached conn


def get_environment(env_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM environments WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (env_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        pass  # shared cached conn


def list_environments(
    status: Optional[str] = None,
    env_type: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conn = _get_conn()
    try:
        query = "SELECT * FROM environments WHERE (deleted IS NULL OR deleted = 0)"
        params: List = []
        if status and status in VALID_STATUSES:
            query += " AND status = ?"
            params.append(status)
        if env_type:
            query += " AND env_type = ?"
            params.append(env_type)
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        query += " ORDER BY updated_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        pass  # shared cached conn


def update_environment(env_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    existing = get_environment(env_id)
    if not existing:
        return None

    allowed = {"name", "description", "env_type", "endpoint", "status",
               "docker_compose_path", "container_name", "image",
               "health_check_url", "owner", "tags", "error_message",
               "last_checked_at", "last_status_change"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}

    if "tags" in updates and isinstance(updates["tags"], list):
        updates["tags"] = json.dumps(updates["tags"])
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise ValueError(f"无效环境状态: {updates['status']}")

    if not updates:
        return existing

    updates["updated_at"] = time.time()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [env_id]

    conn = _get_conn()
    try:
        conn.execute(f"UPDATE environments SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return get_environment(env_id)
    finally:
        pass  # shared cached conn


def delete_environment(env_id: str, permanent: bool = False) -> bool:
    """删除环境。默认软删除（进入回收站），permanent=True 时彻底删除。"""
    conn = _get_conn()
    try:
        if permanent:
            cur = conn.execute("DELETE FROM environments WHERE id = ?", (env_id,))
        else:
            cur = conn.execute(
                "UPDATE environments SET deleted = 1, deleted_at = ? WHERE id = ? AND (deleted IS NULL OR deleted = 0)",
                (time.time(), env_id),
            )
        conn.commit()
        return cur.rowcount > 0
    finally:
        pass  # shared cached conn


def list_trash_environments() -> List[Dict[str, Any]]:
    """列出回收站中的环境。"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM environments WHERE deleted = 1 ORDER BY deleted_at DESC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        pass  # shared cached conn


def restore_environment(env_id: str) -> bool:
    """从回收站恢复环境。"""
    conn = _get_conn()
    try:
        cur = conn.execute(
            "UPDATE environments SET deleted = 0, deleted_at = NULL WHERE id = ? AND deleted = 1",
            (env_id,),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        pass  # shared cached conn


def trash_environment(env_id: str) -> bool:
    """将环境移入回收站。"""
    conn = _get_conn()
    try:
        cur = conn.execute(
            "UPDATE environments SET deleted = 1, deleted_at = ? WHERE id = ? AND (deleted IS NULL OR deleted = 0)",
            (time.time(), env_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        pass  # shared cached conn


def purge_environment(env_id: str) -> bool:
    """从回收站彻底删除环境。"""
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM environments WHERE id = ?", (env_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        pass  # shared cached conn


# ═══════════════════════════════════════════════════════════
# 容器环境拉起 / 停止 / 健康检查
# ═══════════════════════════════════════════════════════════
# Docker 生命周期与健康检查的实际运维逻辑已迁移到
# app/services/environment_service.EnvironmentService（服务层编排，
# Repository 仅提供纯数据访问）。旧调用方请改走该服务链；
# 本模块仅保留环境的 CRUD / 回收站 / 告警查询与统计等数据兼容能力。
# 容器环境拉起 / 停止 / 健康检查 / 建告警等副作用函数已不再驻留本文件。


def list_alerts(
    status: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    conn = _get_conn()
    try:
        query = "SELECT * FROM alerts WHERE 1=1"
        params: List = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if level and level in VALID_ALERT_LEVELS:
            query += " AND level = ?"
            params.append(level)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        pass  # shared cached conn


def resolve_alert(alert_id: str) -> bool:
    """标记告警为已解决。"""
    conn = _get_conn()
    try:
        cur = conn.execute(
            "UPDATE alerts SET status = 'resolved', resolved_at = ? WHERE id = ? AND status = 'open'",
            (time.time(), alert_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        pass  # shared cached conn


def get_stats() -> Dict[str, Any]:
    """获取环境与告警统计。"""
    conn = _get_conn()
    try:
        env_total = conn.execute(
            "SELECT COUNT(*) FROM environments WHERE (deleted IS NULL OR deleted = 0)"
        ).fetchone()[0]
        # 一次 GROUP BY 查询代替逐状态 COUNT（消除 N+1）
        by_status = {s: 0 for s in VALID_STATUSES}
        for row in conn.execute(
            "SELECT status, COUNT(*) AS cnt FROM environments "
            "WHERE (deleted IS NULL OR deleted = 0) GROUP BY status"
        ):
            if row["status"] in by_status:
                by_status[row["status"]] = row["cnt"]

        alert_open = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE status = 'open'"
        ).fetchone()[0]
        alert_total = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]

        return {
            "env_total": env_total,
            "env_by_status": by_status,
            "alert_open": alert_open,
            "alert_total": alert_total,
        }
    finally:
        pass  # shared cached conn
