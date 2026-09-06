"""文件聚合仓储实现（Adapter / Anti-Corruption Layer）。"""
from __future__ import annotations

from typing import List, Optional

from app.core.database import Database
from app.domain.file.domain.entities.file_item import FileItem


class FileRepoAdapter:
    """文件聚合的 SQLite 持久化适配器。"""

    db_name = "tga.db"

    def __init__(self) -> None:
        conn = Database.get_conn(self.db_name)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS domain_files (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                project_id TEXT NOT NULL DEFAULT '',
                module_id TEXT NOT NULL DEFAULT 'root',
                create_user TEXT NOT NULL DEFAULT '',
                update_user TEXT NOT NULL DEFAULT '',
                storage TEXT NOT NULL DEFAULT 'minio',
                file_type TEXT NOT NULL DEFAULT 'FILE',
                description TEXT NOT NULL DEFAULT '',
                enable INTEGER NOT NULL DEFAULT 1,
                size INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )"""
        )
        conn.commit()

    def upsert_meta(self, file: FileItem) -> None:
        data = file.to_dict()
        conn = Database.get_conn(self.db_name)
        conn.execute(
            """INSERT INTO domain_files
            (id, name, project_id, module_id, create_user, update_user, storage,
             file_type, description, enable, size, created_at, updated_at)
            VALUES (:id, :name, :project_id, :module_id, :create_user, :update_user,
                    :storage, :file_type, :description, :enable, :size,
                    :created_at, :updated_at)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, project_id=excluded.project_id,
                module_id=excluded.module_id, update_user=excluded.update_user,
                storage=excluded.storage, file_type=excluded.file_type,
                description=excluded.description, enable=excluded.enable,
                size=excluded.size, updated_at=excluded.updated_at""",
            {**data, "enable": int(data["enable"])},
        )
        conn.commit()

    def get_meta(self, file_id: str) -> Optional[FileItem]:
        row = Database.get_conn(self.db_name).execute(
            "SELECT * FROM domain_files WHERE id = ?", (file_id,)
        ).fetchone()
        return FileItem.from_dict(row) if row else None

    def list_by_ids(self, file_ids: List[str]) -> List[FileItem]:
        if not file_ids:
            return []
        placeholders = ",".join("?" for _ in file_ids)
        rows = Database.get_conn(self.db_name).execute(
            f"SELECT * FROM domain_files WHERE id IN ({placeholders})", file_ids
        ).fetchall()
        return [FileItem.from_dict(dict(r)) for r in rows]

    def delete_by_ids(self, file_ids: List[str]) -> int:
        if not file_ids:
            return 0
        placeholders = ",".join("?" for _ in file_ids)
        conn = Database.get_conn(self.db_name)
        cur = conn.execute(
            f"DELETE FROM domain_files WHERE id IN ({placeholders})", file_ids
        )
        conn.commit()
        return cur.rowcount

    def list_by_project(self, project_id: str = "") -> List[FileItem]:
        conn = Database.get_conn(self.db_name)
        if project_id:
            rows = conn.execute(
                "SELECT * FROM domain_files WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM domain_files ORDER BY created_at DESC"
            ).fetchall()
        return [FileItem.from_dict(dict(r)) for r in rows]

    def count_by_module(self, project_id: str = "", storage: str = "") -> dict:
        conn = Database.get_conn(self.db_name)
        clauses, params = [], []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if storage:
            clauses.append("storage = ?")
            params.append(storage)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT module_id, COUNT(*) AS count FROM domain_files{where} GROUP BY module_id",
            params,
        ).fetchall()
        return {str(row["module_id"]): row["count"] for row in rows}


__all__ = ["FileRepoAdapter", "file_repo"]


# ── 薄门面：兼容旧 file_repo.upsert_meta(file_id, data) 签名 ──────────────
class _FileRepoFacade:
    """薄门面，让 attachment.py 的 file_repo.upsert_meta(file_id, data) 调用
    本地 FileRepoAdapter，不再依赖 app.repositories.file_repo。"""

    def __init__(self) -> None:
        self._adapter = FileRepoAdapter()

    def upsert_meta(self, file_id: str, data: dict) -> None:
        from app.domain.file.domain.entities.file_item import FileItem
        item = self._adapter.get_meta(file_id)
        if item:
            item.update_meta(data)
        else:
            item = FileItem(file_id=file_id, name=data.get("name", file_id), _uploaded=False)
            item.update_meta(data)
        self._adapter.upsert_meta(item)


file_repo = _FileRepoFacade()
