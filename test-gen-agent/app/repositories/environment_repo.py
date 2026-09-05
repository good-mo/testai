# app/repositories/environment_repo.py
"""环境数据访问层（Phase 3 重构 · 4 层对齐）。

本层从「委托旧 app.environment.manager」下沉为**仓库内直接 SQLite 实现**，
消除 Repository 空壳化。纯数据访问（环境 CRUD / 回收站 / 告警 / 统计）
均在仓库内直连 SQL，输出与旧 manager 完全一致（tags 反序列化等）。

容器拉起/停止/健康检查属 Docker 运维副作用，由服务层
app.services.environment_service 编排实现；本层仅提供其所需的纯数据
访问（环境读取/状态更新/create_alert），不承担任何外部副作用。
"""
import json
import time
import uuid
from typing import List, Optional

from app.core.database import Database
from app.repositories.base import BaseRepo

# 环境状态 / 告警级别（与旧 app.environment.manager 保持一致）
ENV_STATUS_ONLINE = "online"
ENV_STATUS_OFFLINE = "offline"
ENV_STATUS_ERROR = "error"
ENV_STATUS_MAINTENANCE = "maintenance"
ENV_STATUS_LAUNCHING = "launching"
VALID_STATUSES = {
    ENV_STATUS_ONLINE, ENV_STATUS_OFFLINE, ENV_STATUS_ERROR,
    ENV_STATUS_MAINTENANCE, ENV_STATUS_LAUNCHING,
}
ALERT_LEVEL_INFO = "info"
ALERT_LEVEL_WARNING = "warning"
ALERT_LEVEL_CRITICAL = "critical"
VALID_ALERT_LEVELS = {ALERT_LEVEL_INFO, ALERT_LEVEL_WARNING, ALERT_LEVEL_CRITICAL}


class EnvironmentRepo(BaseRepo):
    db_name = "environments.db"
    table_name = "environments"

    # ── 行工具 ────────────────────────────────────────────
    @classmethod
    def _conn(cls):
        return Database.get_conn(cls.db_name)

    @classmethod
    def _row_to_dict(cls, row) -> dict:
        """裸行 → 归一化输出（tags 反序列化，与旧 manager._row_to_dict 一致）。"""
        data = dict(row)
        for k in ("tags",):
            if data.get(k):
                try:
                    data[k] = json.loads(data[k])
                except (json.JSONDecodeError, TypeError):
                    pass
        return data

    # ── 环境 CRUD ─────────────────────────────────────────
    @classmethod
    def create(cls, data: dict) -> dict:
        """注册新环境。

        兼容 base_url → endpoint 映射：必须先无条件弹出 base_url，
        前端整表单提交时 endpoint 以空串存在，若直接把 base_url 传给
        register_environment 会触发 TypeError → 500。
        """
        body = dict(data)
        base_url = body.pop("base_url", None)
        if not body.get("endpoint") and base_url:
            body["endpoint"] = base_url

        env_id = uuid.uuid4().hex[:12]
        now = time.time()
        tags = body.get("tags") or []
        conn = cls._conn()
        conn.execute(
            """INSERT INTO environments
               (id, name, description, env_type, status, endpoint,
                docker_compose_path, container_name, image,
                health_check_url, owner, tags, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                env_id,
                body.get("name", ""),
                body.get("description", ""),
                body.get("env_type", "docker"),
                ENV_STATUS_OFFLINE,
                body.get("endpoint", ""),
                body.get("docker_compose_path", ""),
                body.get("container_name", ""),
                body.get("image", ""),
                body.get("health_check_url", ""),
                body.get("owner", ""),
                json.dumps(tags if isinstance(tags, list) else [], ensure_ascii=False),
                now, now,
            ),
        )
        conn.commit()
        return cls.get(env_id) or {"id": env_id}

    @classmethod
    def get(cls, env_id: str) -> Optional[dict]:
        row = cls._conn().execute(
            "SELECT * FROM environments WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (env_id,)
        ).fetchone()
        return cls._row_to_dict(row) if row else None

    @classmethod
    def list(cls, search: str = "", status: str = "",
             env_type: str = "") -> List[dict]:
        query = "SELECT * FROM environments WHERE (deleted IS NULL OR deleted = 0)"
        params: list = []
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
        rows = cls._conn().execute(query, params).fetchall()
        return [cls._row_to_dict(r) for r in rows]

    @classmethod
    def update(cls, env_id: str, data: dict) -> Optional[dict]:
        existing = cls.get(env_id)
        if not existing:
            return None
        allowed = {
            "name", "description", "env_type", "endpoint", "status",
            "docker_compose_path", "container_name", "image",
            "health_check_url", "owner", "tags", "error_message",
            "last_checked_at", "last_status_change",
        }
        updates = {k: v for k, v in data.items() if k in allowed}
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"], ensure_ascii=False)
        if "status" in updates and updates["status"] not in VALID_STATUSES:
            raise ValueError(f"无效环境状态: {updates['status']}")
        if not updates:
            return existing
        updates["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [env_id]
        conn = cls._conn()
        conn.execute(
            f"UPDATE environments SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
        return cls.get(env_id)

    @classmethod
    def delete(cls, env_id: str, permanent: bool = False) -> bool:
        conn = cls._conn()
        if permanent:
            cur = conn.execute(
                "DELETE FROM environments WHERE id = ?", (env_id,)
            )
        else:
            cur = conn.execute(
                "UPDATE environments SET deleted = 1, deleted_at = ? "
                "WHERE id = ? AND (deleted IS NULL OR deleted = 0)",
                (time.time(), env_id),
            )
        conn.commit()
        return cur.rowcount > 0

    # ── 回收站 ───────────────────────────────────────────
    @classmethod
    def list_trash(cls) -> List[dict]:
        rows = cls._conn().execute(
            "SELECT * FROM environments WHERE deleted = 1 "
            "ORDER BY deleted_at DESC"
        ).fetchall()
        return [cls._row_to_dict(r) for r in rows]

    @classmethod
    def restore(cls, env_id: str) -> bool:
        cur = cls._conn().execute(
            "UPDATE environments SET deleted = 0, deleted_at = NULL "
            "WHERE id = ? AND deleted = 1",
            (env_id,),
        )
        cls._conn().commit()
        return cur.rowcount > 0

    @classmethod
    def trash(cls, env_id: str) -> bool:
        cur = cls._conn().execute(
            "UPDATE environments SET deleted = 1, deleted_at = ? "
            "WHERE id = ? AND (deleted IS NULL OR deleted = 0)",
            (time.time(), env_id),
        )
        cls._conn().commit()
        return cur.rowcount > 0

    @classmethod
    def purge(cls, env_id: str) -> bool:
        cur = cls._conn().execute(
            "DELETE FROM environments WHERE id = ?", (env_id,)
        )
        cls._conn().commit()
        return cur.rowcount > 0

    # ── 告警 ─────────────────────────────────────────────
    @classmethod
    def create_alert(
        cls,
        env_id: str,
        env_name: str,
        level: str,
        message: str,
        detail: str = "",
    ) -> dict:
        """创建告警记录（纯数据访问，供服务层 Docker 运维编排调用）。"""
        alert_id = uuid.uuid4().hex[:12]
        now = time.time()
        conn = cls._conn()
        conn.execute(
            """INSERT INTO alerts
               (id, env_id, env_name, level, message, detail, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (alert_id, env_id, env_name, level, message, detail, "open", now),
        )
        cls._conn().commit()
        return {
            "id": alert_id, "env_id": env_id, "env_name": env_name,
            "level": level, "message": message, "detail": detail,
            "status": "open", "created_at": now,
        }

    @classmethod
    def list_alerts(cls, limit: int = 50, level: str = "") -> List[dict]:
        query = "SELECT * FROM alerts WHERE 1=1"
        params: list = []
        if level and level in VALID_ALERT_LEVELS:
            query += " AND level = ?"
            params.append(level)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = cls._conn().execute(query, params).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def resolve_alert(cls, alert_id: str) -> bool:
        cur = cls._conn().execute(
            "UPDATE alerts SET status = 'resolved', resolved_at = ? "
            "WHERE id = ? AND status = 'open'",
            (time.time(), alert_id),
        )
        cls._conn().commit()
        return cur.rowcount > 0

    @classmethod
    def get_alerts_stats(cls) -> dict:
        conn = cls._conn()
        # 统计口径排除软删除环境（与 app.environment.manager.get_stats 保持一致）
        env_total = conn.execute(
            "SELECT COUNT(*) FROM environments WHERE (deleted IS NULL OR deleted = 0)"
        ).fetchone()[0]
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


environment_repo = EnvironmentRepo
