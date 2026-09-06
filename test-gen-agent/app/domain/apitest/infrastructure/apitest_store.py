"""接口测试上下文的 SQLite 存储适配器。"""

from __future__ import annotations

import json
import time
import uuid
from typing import Optional

from app.core.database import Database


class ApitestStore:
    db_name = "tga.db"
    _tables = {
        "definition": "domain_api_definitions",
        "case": "domain_api_cases",
        "scenario": "domain_api_scenarios",
        "mock": "domain_api_mocks",
    }

    def __init__(self) -> None:
        conn = Database.get_conn(self.db_name)
        for table in self._tables.values():
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ("
                "id TEXT PRIMARY KEY, project_id TEXT NOT NULL DEFAULT '', "
                "name TEXT NOT NULL DEFAULT '', deleted INTEGER NOT NULL DEFAULT 0, "
                "created_at REAL NOT NULL, updated_at REAL NOT NULL, data TEXT NOT NULL)"
            )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_api_definition_versions ("
            "id TEXT PRIMARY KEY, definition_id TEXT NOT NULL, version TEXT NOT NULL, "
            "created_at REAL NOT NULL)"
        )
        conn.commit()

    @staticmethod
    def _row(row) -> Optional[dict]:
        if not row:
            return None
        data = json.loads(row["data"] or "{}")
        data.setdefault("id", row["id"])
        data.setdefault("project_id", row["project_id"])
        data["deleted"] = bool(row["deleted"])
        return data

    def _table(self, kind: str) -> str:
        return self._tables[kind]

    def _get(self, kind: str, item_id: str, include_deleted: bool = False):
        sql = f"SELECT * FROM {self._table(kind)} WHERE id = ?"
        params = [item_id]
        if not include_deleted:
            sql += " AND deleted = 0"
        return self._row(Database.get_conn(self.db_name).execute(sql, params).fetchone())

    def _list(self, kind: str, project_id: str = "", keyword: str = "", limit: int = 100,
              offset: int = 0, include_deleted: bool = False):
        clauses = ["deleted = ?"]
        params = [int(include_deleted)]
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if keyword:
            clauses.append("name LIKE ?")
            params.append(f"%{keyword}%")
        params.extend([max(1, limit), max(0, offset)])
        rows = Database.get_conn(self.db_name).execute(
            f"SELECT * FROM {self._table(kind)} WHERE {' AND '.join(clauses)} "
            "ORDER BY updated_at DESC LIMIT ? OFFSET ?", params
        ).fetchall()
        return [self._row(row) for row in rows]

    def _count(self, kind: str, project_id: str = "", keyword: str = "", deleted: bool = False):
        clauses = ["deleted = ?"]
        params = [int(deleted)]
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if keyword:
            clauses.append("name LIKE ?")
            params.append(f"%{keyword}%")
        row = Database.get_conn(self.db_name).execute(
            f"SELECT COUNT(*) AS n FROM {self._table(kind)} WHERE {' AND '.join(clauses)}", params
        ).fetchone()
        return int(row["n"])

    def _save(self, kind: str, data: dict, item_id: str = "") -> dict:
        item_id = item_id or data.get("id") or uuid.uuid4().hex[:12]
        now = time.time()
        conn = Database.get_conn(self.db_name)
        old = conn.execute(f"SELECT created_at FROM {self._table(kind)} WHERE id = ?", (item_id,)).fetchone()
        project_id = data.get("project_id", data.get("projectId", "")) or ""
        name = data.get("name", "") or ""
        conn.execute(
            f"INSERT INTO {self._table(kind)} (id, project_id, name, deleted, created_at, updated_at, data) "
            "VALUES (?, ?, ?, 0, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "project_id=excluded.project_id, name=excluded.name, deleted=0, "
            "updated_at=excluded.updated_at, data=excluded.data",
            (item_id, project_id, name, old["created_at"] if old else now, now,
             json.dumps({**data, "id": item_id}, ensure_ascii=False, default=str)),
        )
        conn.commit()
        return self._get(kind, item_id)

    def _delete(self, kind: str, item_id: str) -> bool:
        conn = Database.get_conn(self.db_name)
        cur = conn.execute(f"UPDATE {self._table(kind)} SET deleted = 1 WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0

    def _restore(self, kind: str, item_id: str) -> bool:
        conn = Database.get_conn(self.db_name)
        cur = conn.execute(f"UPDATE {self._table(kind)} SET deleted = 0 WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0

    def _purge(self, kind: str, item_id: str) -> bool:
        conn = Database.get_conn(self.db_name)
        cur = conn.execute(f"DELETE FROM {self._table(kind)} WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0

    def get_definition(self, item_id): return self._get("definition", item_id)
    def list_trash_definitions(self, project_id="", limit=100): return self._list("definition", project_id, limit=limit, include_deleted=True)
    def list_definitions(self, keyword="", limit=100, offset=0, project_id="", include_latest_only=True, protocols=None, module_ids=None): return self._list("definition", project_id, keyword, limit, offset)
    def count_definitions(self, project_id="", keyword="", protocols=None, module_ids=None): return self._count("definition", project_id, keyword)
    def count_trash_definitions(self, project_id=""): return self._count("definition", project_id, deleted=True)
    def create_definition(self, **data): return self._save("definition", data)
    def update_definition(self, item_id, **data):
        current = self._get("definition", item_id, True) or {"id": item_id}
        return self._save("definition", {**current, **data}, item_id)
    def delete_definition(self, item_id): return self._delete("definition", item_id)
    def restore_definition(self, item_id): return self._restore("definition", item_id)
    def create_definition_version(self, definition_id, version):
        conn = Database.get_conn(self.db_name); item_id = uuid.uuid4().hex[:12]
        conn.execute("INSERT INTO domain_api_definition_versions VALUES (?, ?, ?, ?)", (item_id, definition_id, version, time.time())); conn.commit()
        return {"id": item_id, "definition_id": definition_id, "version": version}
    def list_definition_versions(self, ref_id):
        rows = Database.get_conn(self.db_name).execute("SELECT * FROM domain_api_definition_versions WHERE definition_id = ?", (ref_id,)).fetchall()
        return [dict(row) for row in rows]

    def _kind_methods(self, kind, singular):
        return

    def get_api_case(self, item_id): return self._get("case", item_id)
    def list_trash_cases(self, project_id="", limit=100): return self._list("case", project_id, limit=limit, include_deleted=True)
    def list_api_cases(self, keyword="", limit=100, offset=0, project_id="", api_definition_id=""): return self._list("case", project_id, keyword, limit, offset)
    def count_api_cases(self, project_id="", keyword="", api_definition_id=""): return self._count("case", project_id, keyword)
    def count_trash_cases(self, project_id=""): return self._count("case", project_id, deleted=True)
    def create_api_case(self, **data): return self._save("case", data)
    def update_api_case(self, item_id, **data): return bool(self._save("case", {**(self._get("case", item_id, True) or {"id": item_id}), **data}, item_id))
    def delete_api_case(self, item_id): return self._delete("case", item_id)
    def restore_case(self, item_id): return self._restore("case", item_id)

    def get_scenario(self, item_id): return self._get("scenario", item_id)
    def list_trash_scenarios(self, project_id="", limit=100): return self._list("scenario", project_id, limit=limit, include_deleted=True)
    def list_scenarios(self, keyword="", limit=100, offset=0, project_id=""): return self._list("scenario", project_id, keyword, limit, offset)
    def count_scenarios(self, project_id="", keyword=""): return self._count("scenario", project_id, keyword)
    def count_trash_scenarios(self, project_id=""): return self._count("scenario", project_id, deleted=True)
    def create_scenario(self, **data): return self._save("scenario", data)
    def update_scenario(self, item_id, **data): return bool(self._save("scenario", {**(self._get("scenario", item_id, True) or {"id": item_id}), **data}, item_id))
    def delete_scenario(self, item_id): return self._delete("scenario", item_id)
    def restore_scenario(self, item_id): return self._restore("scenario", item_id)

    def get_mock(self, item_id): return self._get("mock", item_id)
    def list_trash_mocks(self, project_id="", limit=100): return self._list("mock", project_id, limit=limit, include_deleted=True)
    def list_mocks(self, keyword="", limit=100, offset=0, project_id=""): return self._list("mock", project_id, keyword, limit, offset)
    def count_mocks(self, project_id="", keyword=""): return self._count("mock", project_id, keyword)
    def count_trash_mocks(self, project_id=""): return self._count("mock", project_id, deleted=True)
    def create_mock(self, **data): return self._save("mock", data)
    def update_mock(self, item_id, **data): return bool(self._save("mock", {**(self._get("mock", item_id, True) or {"id": item_id}), **data}, item_id))
    def delete_mock(self, item_id): return self._delete("mock", item_id)
    def restore_mock(self, item_id): return self._restore("mock", item_id)
    def purge_mock(self, item_id): return self._purge("mock", item_id)


apitest_store = ApitestStore()
ApitestRepo = apitest_store
__all__ = ["ApitestStore", "ApitestRepo", "apitest_store"]
