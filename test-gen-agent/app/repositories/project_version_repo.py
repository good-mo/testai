# app/repositories/project_version_repo.py
"""项目版本（project_versions）数据访问层（Phase 4 重构 · 4 层对齐）。

从 app/routers/project_compat_extra2.py 下沉：原 router 目录直接持有建表 +
CRUD SQL，现收敛到本仓库——Router → Service → Repository → DB。

承载 project_versions 表（projects.db）：
  - 每条项目版本存一行，字段含 status/latest/publish_time/create_time 等。
  - 版本「功能开关」沿用 project_app_configs 表（module='projectVersion'，
    该表独立于 project_versions 表），一并在此收口为版本功能配置读写。

纯数据访问（建表 / CRUD / 开关读写）均在仓库内直连 SQL，
业务编排与前端 camelCase 字段映射归 Service 层，不在此处。
"""
import time
import uuid
from typing import List, Optional

from app.core.database import Database
from app.repositories.base import BaseRepo


class ProjectVersionRepo(BaseRepo):
    """项目版本仓库：project_versions 表数据访问。"""

    db_name = "projects.db"
    table_name = "project_versions"

    # 建表守卫：收敛到 _conn() 一处，冷启动空库下任意方法（含此前无守卫的
    # update_version / get_feature_enabled / set_feature_enabled）都会自动建表。
    _schema_ensured = False

    # ── 建表 ──────────────────────────────────────────────
    @classmethod
    def _conn(cls):
        """获取连接；首访懒触发一次 project_versions 建表守卫。"""
        if not cls._schema_ensured:
            cls.init_table()
            cls._schema_ensured = True
        return Database.get_conn(cls.db_name)

    @classmethod
    def init_table(cls) -> None:
        """幂等建表（直接用 Database 连接，避免与 _conn 守卫互相递归）。"""
        conn = Database.get_conn(cls.db_name)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_versions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                status INTEGER DEFAULT 0,
                latest INTEGER DEFAULT 0,
                publish_time REAL,
                create_time REAL,
                create_user TEXT DEFAULT 'admin',
                update_time REAL
            )
        """)
        conn.commit()

    @classmethod
    def _ensure_table(cls) -> None:
        cls.init_table()

    # ── 版本 CRUD ─────────────────────────────────────────
    @classmethod
    def list_versions(cls, project_id: str, keyword: str = "") -> List[dict]:
        """列出项目版本（create_time 降序）。"""
        cls._ensure_table()
        conn = cls._conn()
        query = "SELECT * FROM project_versions WHERE project_id=?"
        params = [project_id]
        if keyword:
            query += " AND name LIKE ?"
            params.append(f"%{keyword}%")
        query += " ORDER BY create_time DESC"
        try:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    @classmethod
    def get_version(cls, version_id: str) -> Optional[dict]:
        """按 id 查询单个项目版本；不存在返回 None。"""
        cls._ensure_table()
        conn = cls._conn()
        row = conn.execute(
            "SELECT * FROM project_versions WHERE id=?", (version_id,)
        ).fetchone()
        return dict(row) if row else None

    @classmethod
    def add_version(cls, project_id: str, name: str, description: str = "",
                    status: bool = False, latest: bool = False,
                    publish_time: float = 0.0, create_user: str = "admin",
                    version_id: str = "") -> Optional[dict]:
        """新增项目版本并落库，返回新行；失败返回 None。

        version_id 可选：DDD 聚合接线时传入聚合根的 id，保证返回 id == 落库 id；
        缺省时由本层生成（向后兼容既有调用方）。
        """
        cls._ensure_table()
        conn = cls._conn()
        vid = version_id or str(uuid.uuid4())
        now = time.time()
        try:
            conn.execute("""
                INSERT INTO project_versions
                    (id, project_id, name, description, status, latest,
                     publish_time, create_time, create_user, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (vid, project_id, name, description, int(status), int(latest),
                  publish_time, now, create_user, now))
            conn.commit()
            return cls.get_version(vid)
        except Exception:
            return None

    @classmethod
    def update_version(cls, version_id: str, updates: dict) -> Optional[dict]:
        """按 id 部分更新（updates 为列名->值映射），返回更新后新行。"""
        if not updates:
            return cls.get_version(version_id)
        conn = cls._conn()
        set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
        try:
            conn.execute(
                f"UPDATE project_versions SET {set_clause} WHERE id=?",
                (*updates.values(), version_id),
            )
            conn.commit()
            return cls.get_version(version_id)
        except Exception:
            return None

    @classmethod
    def delete_version(cls, version_id: str) -> bool:
        """按 id 删除项目版本；返回是否实际删除。"""
        cls._ensure_table()
        conn = cls._conn()
        try:
            cur = conn.execute(
                "DELETE FROM project_versions WHERE id=?", (version_id,)
            )
            conn.commit()
            return cur.rowcount > 0
        except Exception:
            return False

    @classmethod
    def clear_project_latest(cls, project_id: str, exclude_id: str = "") -> None:
        """清除某项目下（除 exclude_id 外）所有版本的 latest 标记。"""
        cls._ensure_table()
        conn = cls._conn()
        try:
            conn.execute(
                "UPDATE project_versions SET latest=0 WHERE project_id=? AND id!=?",
                (project_id, exclude_id),
            )
            conn.commit()
        except Exception:
            pass

    @classmethod
    def set_latest(cls, version_id: str) -> None:
        """将某版本置为最新。"""
        cls._ensure_table()
        conn = cls._conn()
        try:
            conn.execute(
                "UPDATE project_versions SET latest=1 WHERE id=?", (version_id,)
            )
            conn.commit()
        except Exception:
            pass

    @classmethod
    def set_status(cls, version_id: str, status: bool) -> None:
        """设置某版本状态（启用/停用）。"""
        cls._ensure_table()
        conn = cls._conn()
        try:
            conn.execute(
                "UPDATE project_versions SET status=?, update_time=? WHERE id=?",
                (int(status), time.time(), version_id),
            )
            conn.commit()
        except Exception:
            pass

    # ── 版本功能开关（project_app_configs）─────────────────
    @classmethod
    def get_feature_enabled(cls, project_id: str) -> bool:
        """项目版本功能是否启用。"""
        from app.repositories.project_app_config_repo import ensure_tables
        ensure_tables()
        conn = cls._conn()
        try:
            row = conn.execute(
                "SELECT config_value FROM project_app_configs "
                "WHERE project_id=? AND module='projectVersion' AND config_key='enabled'",
                (project_id,),
            ).fetchone()
            if row:
                return str(row[0]).lower() in ('true', '1', 'yes')
        except Exception:
            pass
        return False

    @classmethod
    def set_feature_enabled(cls, project_id: str, enabled: bool) -> None:
        """设置项目版本功能启用状态。"""
        from app.repositories.project_app_config_repo import ensure_tables
        ensure_tables()
        conn = cls._conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO project_app_configs
                    (project_id, module, config_key, config_value, updated_at)
                VALUES (?, 'projectVersion', 'enabled', ?, ?)
            """, (project_id, str(enabled).lower(), time.time()))
            conn.commit()
        except Exception:
            pass


# 模块级单例（与其它 repo 风格一致）
project_version_repo = ProjectVersionRepo()
