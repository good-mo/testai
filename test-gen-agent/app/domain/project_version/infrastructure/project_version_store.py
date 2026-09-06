"""项目版本上下文 SQLite 存储。

为 project_version_repo_impl 提供本地存储实现，替代对
app.repositories.project_version_repo 的旧依赖。
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

from app.core.database import Database


class ProjectVersionStore:
    db_name = "tga.db"

    def __init__(self) -> None:
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_project_versions ("
            "id TEXT PRIMARY KEY, project_id TEXT NOT NULL, name TEXT NOT NULL, "
            "description TEXT DEFAULT '', status INTEGER DEFAULT 1, latest INTEGER DEFAULT 0, "
            "publish_time REAL, update_time REAL, create_user TEXT DEFAULT '', "
            "created_at REAL NOT NULL, updated_at REAL NOT NULL)"
        )
        conn.commit()

    def add_version(self, project_id, name, description="", status=1, latest=0, publish_time=None, update_time=None, create_user="", version_id=None):
        item_id = version_id or uuid.uuid4().hex[:12]
        now = time.time()
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO domain_project_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (item_id, project_id, name, description, status, latest, publish_time, update_time or now, create_user, now, now),
        )
        conn.commit()
        return self.get_version(item_id)

    def get_version(self, version_id):
        r = Database.get_conn(self.db_name).execute("SELECT * FROM domain_project_versions WHERE id=?", (version_id,)).fetchone()
        return dict(r) if r else None

    def update_version(self, version_id, data):
        set_clause = ", ".join(f"{k}=?" for k in data)
        conn = Database.get_conn(self.db_name)
        conn.execute(f"UPDATE domain_project_versions SET {set_clause}, updated_at=? WHERE id=?", (*data.values(), time.time(), version_id))
        conn.commit()
        return self.get_version(version_id)

    def list_versions(self, project_id, keyword=""):
        q = "SELECT * FROM domain_project_versions WHERE project_id=?"
        p = [project_id]
        if keyword:
            q += " AND (name LIKE ? OR description LIKE ?)"
            p += [f"%{keyword}%", f"%{keyword}%"]
        rows = Database.get_conn(self.db_name).execute(q + " ORDER BY created_at DESC", p).fetchall()
        return [dict(r) for r in rows]

    def delete_version(self, version_id):
        Database.get_conn(self.db_name).execute("DELETE FROM domain_project_versions WHERE id=?", (version_id,))
        Database.get_conn(self.db_name).commit()
        return True

    def clear_project_latest(self, project_id, exclude_id=""):
        q = "UPDATE domain_project_versions SET latest=0 WHERE project_id=?"
        p = [project_id]
        if exclude_id:
            q += " AND id != ?"
            p.append(exclude_id)
        Database.get_conn(self.db_name).execute(q, p)
        Database.get_conn(self.db_name).commit()
        return True

    def set_latest(self, version_id):
        self.clear_project_latest(self.get_version(version_id)["project_id"] if self.get_version(version_id) else "")
        Database.get_conn(self.db_name).execute("UPDATE domain_project_versions SET latest=1 WHERE id=?", (version_id,))
        Database.get_conn(self.db_name).commit()
        return True

    def set_status(self, version_id, status):
        Database.get_conn(self.db_name).execute("UPDATE domain_project_versions SET status=? WHERE id=?", (int(status), version_id))
        Database.get_conn(self.db_name).commit()
        return True


project_version_repo = ProjectVersionStore()
__all__ = ["project_version_repo", "ProjectVersionStore"]