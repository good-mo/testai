"""项目应用配置上下文 SQLite 存储。

为 project_app_config_repo_impl 提供本地存储实现，替代对
app.repositories.project_app_config_repo 的旧依赖。
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from app.core.database import Database


class ProjectAppConfigStore:
    db_name = "tga.db"

    def __init__(self) -> None:
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_project_app_configs ("
            "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, module TEXT NOT NULL, "
            "config_key TEXT NOT NULL, config_value TEXT DEFAULT '', "
            "created_at REAL NOT NULL, updated_at REAL NOT NULL)"
        )
        conn.commit()

    def get_module_config(self, project_id, module):
        rows = Database.get_conn(self.db_name).execute(
            "SELECT config_key, config_value FROM domain_project_app_configs WHERE project_id=? AND module=?",
            (project_id, module),
        ).fetchall()
        return {r["config_key"]: r["config_value"] for r in rows}

    def save_module_config(self, project_id, module, config):
        now = time.time()
        conn = Database.get_conn(self.db_name)
        for k, v in config.items():
            item_id = f"{project_id}_{module}_{k}"
            conn.execute(
                "INSERT OR REPLACE INTO domain_project_app_configs VALUES (?, ?, ?, ?, ?, ?)",
                (item_id, project_id, module, k, json.dumps(v), now, now),
            )
        conn.commit()
        return config

    def get_config_value(self, project_id, module, config_key, default=""):
        r = Database.get_conn(self.db_name).execute(
            "SELECT config_value FROM domain_project_app_configs WHERE project_id=? AND module=? AND config_key=?",
            (project_id, module, config_key),
        ).fetchone()
        if not r:
            return default
        try:
            return json.loads(r["config_value"])
        except Exception:
            return r["config_value"]

    def set_config_value(self, project_id, module, config_key, value):
        now = time.time()
        item_id = f"{project_id}_{module}_{config_key}"
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT OR REPLACE INTO domain_project_app_configs VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, project_id, module, config_key, json.dumps(value), now, now),
        )
        conn.commit()

    def get_all_modules(self, project_id=""):
        q = "SELECT DISTINCT module FROM domain_project_app_configs WHERE 1=1"
        p = []
        if project_id:
            q += " AND project_id=?"
            p.append(project_id)
        rows = Database.get_conn(self.db_name).execute(q, p).fetchall()
        return [{"module": r["module"]} for r in rows]


project_app_config_repo = ProjectAppConfigStore()
__all__ = ["project_app_config_repo", "ProjectAppConfigStore"]