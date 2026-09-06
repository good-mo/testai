# app/repositories/file_repo.py
"""文件元数据数据访问层：记录上传文件的项目/模块/用户归属。"""
import time
from typing import Dict, List, Optional

from app.repositories.base import BaseRepo


class FileRepo(BaseRepo):
    """项目文件元数据 Repository。

    记录文件与项目 / 模块 / 上传用户 / 存储方式等归属关系，
    供 `/project/file/page`、`/project/file/module/count` 精确过滤。
    """

    db_name: str = "testcases.db"
    table_name: str = "project_files"

    # ── 建表 ─────────────────────────────────────────────
    @classmethod
    def ensure_table(cls) -> None:
        conn = cls.get_conn()
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {cls.table_name} (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                project_id TEXT DEFAULT '',
                module_id TEXT DEFAULT 'root',
                create_user TEXT DEFAULT '',
                update_user TEXT DEFAULT '',
                storage TEXT DEFAULT 'minio',
                file_type TEXT DEFAULT 'FILE',
                enable INTEGER DEFAULT 1,
                description TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                size INTEGER DEFAULT 0,
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{cls.table_name}_project
            ON {cls.table_name}(project_id)
        """)
        conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{cls.table_name}_module
            ON {cls.table_name}(module_id)
        """)
        conn.commit()

    # ── 查询 ─────────────────────────────────────────────
    @classmethod
    def upsert_meta(cls, file_id: str, data: dict) -> None:
        """写入/更新文件元数据。"""
        cls.ensure_table()
        conn = cls.get_conn()
        now = time.time()
        existing = conn.execute(
            f"SELECT id FROM {cls.table_name} WHERE id=?",
            (file_id,),
        ).fetchone()
        if existing:
            sets = ", ".join([f"{k}=?" for k in data.keys()])
            params = tuple(data.values())
            conn.execute(
                f"UPDATE {cls.table_name} SET {sets}, updated_at=? WHERE id=?",
                (*params, now, file_id),
            )
        else:
            cols = ["id", "name", "created_at", "updated_at"]
            vals = [file_id, data.get("name", ""), now, now]
            for key, val in data.items():
                if key != "name":
                    cols.append(key)
                    vals.append(val)
            placeholders = ", ".join(["?"] * len(cols))
            conn.execute(
                f"INSERT INTO {cls.table_name} ({', '.join(cols)}) VALUES ({placeholders})",
                vals,
            )
        conn.commit()

    @classmethod
    def get_meta(cls, file_id: str) -> Optional[dict]:
        """按文件 id 查询元数据。"""
        cls.ensure_table()
        return cls.query_one(
            f"SELECT * FROM {cls.table_name} WHERE id=?",
            (file_id,),
        )

    @classmethod
    def list_by_project(cls, project_id: str = "") -> List[dict]:
        """列出项目下文件元数据（不指定项目则全部）。"""
        cls.ensure_table()
        if project_id:
            return cls.query_all(
                f"SELECT * FROM {cls.table_name} WHERE project_id=?",
                (project_id,),
            )
        return cls.query_all(f"SELECT * FROM {cls.table_name}")

    @classmethod
    def count_by_module(cls, project_id: str = "", storage: str = "") -> dict:
        """按模块统计文件数量，返回 {module_id: count, root, all, my}。"""
        cls.ensure_table()
        where, params = [], []
        if project_id:
            where.append("project_id=?")
            params.append(project_id)
        if storage:
            where.append("storage=?")
            params.append(storage.lower())
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        rows = cls.query_all(
            f"SELECT module_id, COUNT(*) as cnt FROM {cls.table_name}{where_sql} GROUP BY module_id",
            tuple(params),
        )
        counts: Dict[str, int] = {}
        for r in rows:
            counts[r["module_id"]] = r["cnt"]
        total = sum(counts.values())
        counts.setdefault("root", counts.get("root", 0))
        counts["all"] = total
        # my 由 router 层根据 create_user 过滤计算
        return counts

    @classmethod
    def list_by_ids(cls, file_ids: List[str]) -> List[dict]:
        """按多个 id 查询。"""
        if not file_ids:
            return []
        cls.ensure_table()
        placeholders = ", ".join(["?"] * len(file_ids))
        return cls.query_all(
            f"SELECT * FROM {cls.table_name} WHERE id IN ({placeholders})",
            tuple(file_ids),
        )

    @classmethod
    def delete_by_ids(cls, file_ids: List[str]) -> int:
        """批量删除元数据。"""
        if not file_ids:
            return 0
        cls.ensure_table()
        placeholders = ", ".join(["?"] * len(file_ids))
        cur = cls.execute(
            f"DELETE FROM {cls.table_name} WHERE id IN ({placeholders})",
            tuple(file_ids),
        )
        return cur.rowcount


file_repo = FileRepo

__all__ = ["file_repo", "FileRepo"]
