"""cases 域 DDD Repository 实现。

直接操作 tga.db，合并原 case_repo.py 的所有 SQL 操作。
消除 Adapter 模式，Service 层统一通过此 Repository 访问数据。
"""
from __future__ import annotations

import csv
import io
import json
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from app.core.database import Database
from app.domain.cases.domain.entities.case import TestCase

# 常量
STATUS_DRAFT = "draft"
STATUS_REVIEW = "review"
STATUS_APPROVED = "approved"
STATUS_DEPRECATED = "deprecated"
VALID_STATUSES = {STATUS_DRAFT, STATUS_REVIEW, STATUS_APPROVED, STATUS_DEPRECATED}

PRIORITY_P0 = "P0"
PRIORITY_P1 = "P1"
PRIORITY_P2 = "P2"
PRIORITY_P3 = "P3"
VALID_PRIORITIES = {PRIORITY_P0, PRIORITY_P1, PRIORITY_P2, PRIORITY_P3}

REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_APPROVED = "approved"
REVIEW_STATUS_REJECTED = "rejected"

CHANGE_CREATED = "created"
CHANGE_UPDATED = "updated"
CHANGE_DELETED = "deleted"
CHANGE_RESTORED = "restored"
CHANGE_VERSION_CREATED = "version_created"
CHANGE_VERSION_ROLLED_BACK = "version_rolled_back"
CHANGE_REVIEW_SUBMITTED = "review_submitted"
CHANGE_REVIEW_APPROVED = "review_approved"
CHANGE_REVIEW_REJECTED = "review_rejected"
CHANGE_IMPORTED = "imported"


class CaseRepository:
    """cases 域 Repository 实现，直接操作 tga.db。"""
    
    db_name = "tga.db"
    table_name = "test_cases"
    _schema_ensured = False
    _mindmap_cache: Dict[str, tuple] = {}
    _MINDMAP_CACHE_TTL = 10.0

    # ── 工具方法 ──────────────────────────────────────────────
    @classmethod
    def _mgmt_id(cls) -> str:
        return uuid.uuid4().hex[:12]

    @classmethod
    def next_id(cls) -> str:
        return uuid.uuid4().hex[:12]

    @classmethod
    def get_conn(cls):
        if not cls._schema_ensured:
            cls._ensure_table()
            cls._schema_ensured = True
        return Database.get_conn(cls.db_name)

    @classmethod
    def execute(cls, sql: str, params: tuple = ()) -> Any:
        conn = cls.get_conn()
        return conn.execute(sql, params)

    @classmethod
    def query_one(cls, sql: str, params: tuple = ()) -> Optional[dict]:
        conn = cls.get_conn()
        conn.row_factory = lambda cursor, row: {
            desc[0]: row[idx] for idx, desc in enumerate(cursor.description)
        }
        cur = conn.execute(sql, params)
        return cur.fetchone()

    @classmethod
    def query_all(cls, sql: str, params: tuple = ()) -> List[dict]:
        conn = cls.get_conn()
        conn.row_factory = lambda cursor, row: {
            desc[0]: row[idx] for idx, desc in enumerate(cursor.description)
        }
        cur = conn.execute(sql, params)
        return cur.fetchall()

    @classmethod
    def _normalize_record(cls, data: dict) -> dict:
        """把裸数据库行转成归一化形态。"""
        out = dict(data)
        try:
            out["tags"] = json.loads(out.get("tags") or "[]")
        except (json.JSONDecodeError, TypeError):
            out["tags"] = []
        try:
            out["metadata"] = json.loads(out.get("metadata") or "{}")
        except (json.JSONDecodeError, TypeError):
            out["metadata"] = {}
        try:
            raw_sc = out.get("structured_cases") or "[]"
            sc = json.loads(raw_sc)
            if isinstance(sc, str):
                sc = json.loads(sc)
            if not isinstance(sc, list):
                sc = []
            out["structured_cases"] = sc
        except (json.JSONDecodeError, TypeError):
            out["structured_cases"] = []
        if isinstance(out.get("metadata"), dict):
            out["test_type"] = out["metadata"].get("test_type", "")
        if out.get("last_result"):
            try:
                out["last_result"] = json.loads(out["last_result"])
            except (json.JSONDecodeError, TypeError):
                pass
        return out

    # ── 建表 ──────────────────────────────────────────────────
    @classmethod
    def _ensure_table(cls) -> None:
        conn = Database.get_conn(cls.db_name)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                source_code TEXT DEFAULT '',
                test_code TEXT DEFAULT '',
                file_path TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                status TEXT DEFAULT 'draft',
                priority TEXT DEFAULT 'P2',
                requirement_ref TEXT DEFAULT '',
                created_at REAL,
                updated_at REAL,
                last_result TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                structured_cases TEXT DEFAULT '[]'
            )
        """)
        conn.commit()

    @classmethod
    def _ensure_management_tables(cls) -> None:
        from app.cases.management import _init_management_tables
        _init_management_tables()

    @classmethod
    def _build_filters(cls, status=None, priority=None, tag=None,
                       search=None, test_type=None, module_id=None) -> tuple:
        clause = " WHERE 1=1"
        params: List = []
        if status and status in VALID_STATUSES:
            clause += " AND status = ?"
            params.append(status)
        else:
            clause += " AND (status IS NULL OR status != ?)"
            params.append(STATUS_DEPRECATED)
        if priority and priority in VALID_PRIORITIES:
            clause += " AND priority = ?"
            params.append(priority)
        if tag:
            clause += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')
        if test_type:
            clause += " AND metadata LIKE ?"
            params.append(f'%"test_type": "{test_type}"%')
        if search:
            clause += " AND (title LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if module_id and module_id != "root":
            clause += " AND metadata LIKE ?"
            params.append(f'%"module_id": "{module_id}"%')
        return clause, params

    # ── 核心 CRUD ─────────────────────────────────────────────
    def find_by_id(self, case_id: str) -> Optional[Test]:
        row = self.query_one(
            "SELECT * FROM test_cases WHERE id=? AND status != ?",
            (case_id, STATUS_DEPRECATED),
        )
        return TestCase.from_dict(self._normalize_record(row)) if row else None

    def find_deleted(self, case_id: str) -> Optional[Test]:
        for r in self._raw_trash():
            if str(r.get("case_id")) == str(case_id):
                return self._mark_deleted(TestCase.from_dict(r))
        return None

    @staticmethod
    def _mark_deleted(case: Test) -> Test:
        case._deleted = True
        return case

    def _raw_trash(self) -> List[dict]:
        rows = self.list_trash_cases()
        out = []
        for r in rows:
            item = dict(r)
            cd = item.get("case_data")
            if isinstance(cd, str):
                try:
                    cd = json.loads(cd)
                except Exception:
                    cd = {}
            if isinstance(cd, dict):
                merged = dict(cd)
                merged["case_id"] = item.get("case_id")
                out.append(merged)
            else:
                item["case_id"] = item.get("case_id")
                out.append(item)
        return out

    def save(self, case: Test) -> Test:
        d = case.to_dict()
        d["id"] = case.id.value
        result = self.create(d)
        return TestCase.from_dict(result) if result else case

    def update(self, case: Test) -> bool:
        d = case.to_dict()
        persist = {k: v for k, v in d.items() if k not in (
            "id", "reviews", "version", "created_at",
        )}
        persist.pop("test_type", None)
        return bool(self.update_case(case.id.value, persist))

    def soft_delete(self, case_id: str, deleted_by: str = "", reason: str = "") -> bool:
        return bool(self.trash_case(case_id, deleted_by=deleted_by, reason=reason))

    def restore(self, case_id: str, operator: str = "") -> bool:
        return bool(self.restore_case(case_id, operator=operator))

    def list_deleted(self, limit: int = 100, offset: int = 0) -> Tuple[List[Test], int]:
        all_rows = self._raw_trash()
        total = len(all_rows)
        return [self._mark_deleted(TestCase.from_dict(r)) for r in all_rows[offset:offset + limit]], total

    def list_cases(self, *, status: str = "", priority: str = "", tag: str = "",
                   search: str = "", test_type: str = "", module_id: str = "",
                   limit: int = 100, offset: int = 0) -> Tuple[List[Test], int]:
        rows = self.list_cases_raw(
            status=status or None, priority=priority or None, tag=tag or None,
            search=search or None, test_type=test_type or None,
            module_id=module_id or None, limit=limit, offset=offset,
        )
        total = self.count_cases(
            status=status or None, priority=priority or None, tag=tag or None,
            search=search or None, test_type=test_type or None,
            module_id=module_id or None,
        )
        return [TestCase.from_dict(r) for r in rows], total

    # ── 版本 / 变更 ───────────────────────────────────────────
    def create_version(self, case_id: str, snapshot: dict, version: int,
                       operator: str = "", change_desc: str = "") -> int:
        return self.create_version_impl(case_id, created_by=operator, change_desc=change_desc)

    def record_change(self, case_id: str, action: str, field: str = "",
                      old_value: str = "", new_value: str = "", operator: str = "") -> None:
        self.record_change_impl(case_id, action, field=field,
                                old_value=old_value, new_value=new_value, operator=operator)

    def invalidate_mindmap_cache(self) -> None:
        self._mindmap_cache.clear()
        try:
            from app.cases.management import invalidate_mindmap_cache as _m_inv
            _m_inv()
        except Exception:
            pass

    # ── 评审 ──────────────────────────────────────────────────
    def submit_review_record(self, case_id: str, reviewer: str = "",
                             comment: str = "") -> dict:
        self._ensure_management_tables()
        rev_id = self._mgmt_id()
        self.execute(
            """INSERT INTO case_reviews
               (id, case_id, review_status, reviewer, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (rev_id, case_id, REVIEW_STATUS_PENDING, reviewer, comment, time.time()),
        )
        return {"id": rev_id, "case_id": case_id, "review_status": REVIEW_STATUS_PENDING}

    def approve_review_record(self, case_id: str, reviewer: str = "",
                              comment: str = "") -> dict:
        self._ensure_management_tables()
        with Database.transaction(self.db_name) as conn:
            conn.execute(
                """UPDATE case_reviews
                   SET review_status=?, reviewer=?, comment=?, reviewed_at=?
                   WHERE case_id=?""",
                (REVIEW_STATUS_APPROVED, reviewer, comment, time.time(), case_id),
            )
            conn.execute("UPDATE test_cases SET status=?, updated_at=? WHERE id=?",
                         (STATUS_APPROVED, time.time(), case_id))
        return {"case_id": case_id, "review_status": REVIEW_STATUS_APPROVED}

    def reject_review_record(self, case_id: str, reviewer: str = "",
                             comment: str = "",
                             review_status: str = REVIEW_STATUS_REJECTED) -> dict:
        self._ensure_management_tables()
        with Database.transaction(self.db_name) as conn:
            conn.execute(
                """UPDATE case_reviews
                   SET review_status=?, reviewer=?, comment=?, reviewed_at=?
                   WHERE case_id=?""",
                (review_status, reviewer, comment, time.time(), case_id),
            )
            conn.execute("UPDATE test_cases SET status=?, updated_at=? WHERE id=?",
                         (STATUS_DRAFT, time.time(), case_id))
        return {"case_id": case_id, "review_status": review_status}

    def get_reviews(self, case_id: str) -> list:
        return self.query_all(
            "SELECT * FROM case_reviews WHERE case_id=? ORDER BY created_at DESC",
            (case_id,),
        )

    # ── 关联 ──────────────────────────────────────────────────
    def add_relation(self, case_id: str, related_case_id: str,
                     relation_type: str = "related") -> dict:
        return self.add_relation_impl(case_id, related_case_id, relation_type)

    def remove_relation(self, case_id: str, related_id: str) -> bool:
        return self.remove_relation_impl(case_id, related_id)

    def list_relations(self, case_id: str) -> list:
        return self.list_relations_impl(case_id)

    # ── 依赖 ──────────────────────────────────────────────────
    def add_dependency(self, case_id: str, depends_on: str,
                       dep_type: str = "before", description: str = "") -> dict:
        return self.add_dependency_impl(case_id, depends_on, dep_type, description)

    def remove_dependency(self, case_id: str, depends_on: str) -> bool:
        return self.remove_dependency_impl(case_id, depends_on)

    def list_dependencies(self, case_id: str) -> list:
        return self.list_dependencies_impl(case_id)

    # ── 导入导出 ──────────────────────────────────────────────
    def export_excel(self, cases: list) -> bytes:
        return self.export_excel_impl(cases)

    def export_mindmap(self, cases: list = None) -> str:
        return self.export_mindmap_impl(cases)

    def import_excel(self, content: str, operator: str = "") -> dict:
        return self.import_excel_impl(content, operator)

    def import_mindmap(self, content: str, operator: str = "") -> dict:
        return self.import_mindmap_impl(content, operator)

    # ══════════════════════════════════════════════════════════
    # 以下为原 case_repo.py 的完整实现（直接 SQL）
    # ══════════════════════════════════════════════════════════

    @classmethod
    def get(cls, case_id: str) -> Optional[dict]:
        row = cls.query_one(
            "SELECT * FROM test_cases WHERE id=? AND status != ?",
            (case_id, STATUS_DEPRECATED),
        )
        return cls._normalize_record(row) if row else None

    @classmethod
    def create(cls, data: dict) -> dict:
        cls._ensure_table()
        case_id = data.get("id") or str(uuid.uuid4())
        now = time.time()
        metadata = data.get("metadata") or "{}"
        if isinstance(metadata, str):
            try:
                metadata_dict = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata_dict = {}
        elif isinstance(metadata, dict):
            metadata_dict = dict(metadata)
        else:
            metadata_dict = {}
        test_type = data.get("test_type", "functional")
        if test_type:
            metadata_dict["test_type"] = test_type
        record = {
            "id": case_id,
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "source_code": data.get("source_code", ""),
            "test_code": data.get("test_code", ""),
            "file_path": data.get("file_path", ""),
            "tags": json.dumps(data.get("tags", []), ensure_ascii=False),
            "status": data.get("status", STATUS_DRAFT),
            "priority": data.get("priority", PRIORITY_P2),
            "requirement_ref": data.get("requirement_ref", ""),
            "created_at": now,
            "updated_at": now,
            "last_result": json.dumps(data.get("last_result"), ensure_ascii=False)
                if isinstance(data.get("last_result"), (dict, list))
                else (data.get("last_result") or ""),
            "metadata": json.dumps(metadata_dict, ensure_ascii=False),
            "structured_cases": json.dumps(data.get("structured_cases", []), ensure_ascii=False),
        }
        cols = list(record.keys())
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO test_cases ({', '.join(cols)}) VALUES ({placeholders})"
        cls.execute(sql, tuple(record.values()))
        return cls.get(case_id) or record

    @classmethod
    def update_case(cls, case_id: str, data: dict) -> Optional[dict]:
        existing = cls.get(case_id)
        if not existing:
            return None
        updates = dict(data)
        updates["updated_at"] = time.time()
        if "test_type" in updates:
            test_type = updates.pop("test_type")
            try:
                meta = json.loads(existing.get("metadata") or "{}") \
                    if isinstance(existing.get("metadata"), str) \
                    else dict(existing.get("metadata") or {})
            except (json.JSONDecodeError, TypeError):
                meta = {}
            meta["test_type"] = test_type
            updates["metadata"] = json.dumps(meta, ensure_ascii=False)
        if "status" in updates and updates["status"] not in VALID_STATUSES:
            raise ValueError(f"无效状态: {updates['status']}")
        if "priority" in updates and updates["priority"] not in VALID_PRIORITIES:
            raise ValueError(f"无效优先级: {updates['priority']}")
        for field in ("tags", "metadata", "structured_cases", "last_result"):
            if field in updates and isinstance(updates[field], (list, dict)):
                updates[field] = json.dumps(updates[field], ensure_ascii=False)
            elif field == "last_result" and field in updates and updates[field] is None:
                updates[field] = ""
        allowed = [
            "title", "description", "source_code", "test_code", "file_path",
            "tags", "status", "priority", "requirement_ref",
            "last_result", "metadata", "structured_cases", "updated_at",
        ]
        set_pairs = []
        values = []
        for k, v in updates.items():
            if k in allowed:
                set_pairs.append(f"{k}=?")
                values.append(v)
        if not set_pairs:
            return cls.get(case_id)
        values.append(case_id)
        sql = f"UPDATE test_cases SET {', '.join(set_pairs)} WHERE id=?"
        cls.execute(sql, tuple(values))
        return cls.get(case_id)

    @classmethod
    def list_cases_raw(cls, status=None, priority=None, tag=None, search=None,
                       test_type=None, module_id=None,
                       limit: int = 100, offset: int = 0) -> List[dict]:
        clause, params = cls._build_filters(
            status=status, priority=priority, tag=tag,
            search=search, test_type=test_type, module_id=module_id,
        )
        query = "SELECT * FROM test_cases" + clause
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params = list(params) + [int(limit), int(offset)]
        rows = cls.query_all(query, tuple(params))
        return [cls._normalize_record(r) for r in rows]

    @classmethod
    def count_cases(cls, status=None, priority=None, tag=None, search=None,
                    test_type=None, module_id=None) -> int:
        clause, params = cls._build_filters(
            status=status, priority=priority, tag=tag,
            search=search, test_type=test_type, module_id=module_id,
        )
        row = cls.query_one("SELECT COUNT(*) AS cnt FROM test_cases" + clause, tuple(params))
        return row["cnt"] if row else 0

    @classmethod
    def get_stats(cls) -> dict:
        conn = cls.get_conn()
        total = conn.execute("SELECT COUNT(*) FROM test_cases").fetchone()[0]
        by_status = {s: 0 for s in sorted(VALID_STATUSES)}
        for row in conn.execute("SELECT status, COUNT(*) AS cnt FROM test_cases GROUP BY status"):
            if row["status"] in by_status:
                by_status[row["status"]] = row["cnt"]
        by_priority = {p: 0 for p in sorted(VALID_PRIORITIES)}
        for row in conn.execute("SELECT priority, COUNT(*) AS cnt FROM test_cases GROUP BY priority"):
            if row["priority"] in by_priority:
                by_priority[row["priority"]] = row["cnt"]
        return {"total": total, "by_status": by_status, "by_priority": by_priority}

    @classmethod
    def delete(cls, case_id: str) -> bool:
        cls._ensure_management_tables()
        with Database.transaction(cls.db_name) as conn:
            cls._delete_child_records(conn, case_id)
        cls.invalidate_mindmap_cache()
        cursor = cls.execute("DELETE FROM test_cases WHERE id=?", (case_id,))
        return cursor.rowcount > 0

    @classmethod
    def _delete_child_records(cls, conn, case_id: str) -> None:
        conn.execute("DELETE FROM case_relations WHERE case_id=? OR related_case_id=?", (case_id, case_id))
        conn.execute("DELETE FROM case_dependencies WHERE case_id=? OR depends_on=?", (case_id, case_id))
        conn.execute("DELETE FROM case_reviews WHERE case_id=?", (case_id,))
        conn.execute("DELETE FROM case_versions WHERE case_id=?", (case_id,))
        conn.execute("DELETE FROM case_change_logs WHERE case_id=?", (case_id,))
        conn.execute("DELETE FROM case_requirements WHERE case_id=?", (case_id,))
        conn.execute("DELETE FROM case_trash WHERE case_id=?", (case_id,))

    @classmethod
    def record_change_impl(cls, case_id: str, action: str, field: str = "",
                           old_value: str = "", new_value: str = "", operator: str = "") -> None:
        cls._ensure_management_tables()
        try:
            cls.execute(
                """INSERT INTO case_change_logs
                   (id, case_id, action, field, old_value, new_value, operator, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (cls._mgmt_id(), case_id, action, field, old_value, new_value, operator, time.time()),
            )
        except Exception:
            pass

    @classmethod
    def create_version_impl(cls, case_id: str, created_by: str = "", change_desc: str = "") -> int:
        case = cls.get(case_id)
        if not case:
            return 0
        cls._ensure_management_tables()
        row = cls.query_one("SELECT MAX(version) AS max_v FROM case_versions WHERE case_id=?", (case_id,))
        version = (row["max_v"] if row and row.get("max_v") else 0) + 1
        snapshot = json.dumps({
            "title": case.get("title", ""),
            "description": case.get("description", ""),
            "source_code": case.get("source_code", ""),
            "test_code": case.get("test_code", ""),
            "file_path": case.get("file_path", ""),
            "tags": case.get("tags", []),
            "status": case.get("status", "draft"),
            "priority": case.get("priority", "P2"),
            "requirement_ref": case.get("requirement_ref", ""),
            "test_type": case.get("test_type", ""),
            "structured_cases": case.get("structured_cases", []),
        }, ensure_ascii=False)
        cls.execute(
            """INSERT INTO case_versions
               (id, case_id, version, snapshot, created_at, created_by, change_desc)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (cls._mgmt_id(), case_id, version, snapshot, time.time(), created_by, change_desc),
        )
        cls.record_change_impl(case_id, CHANGE_VERSION_CREATED, operator=created_by,
                               new_value=f"v{version}", field="version")
        return version

    @classmethod
    def add_relation_impl(cls, case_id: str, related_case_id: str, relation_type: str = "related") -> dict:
        if case_id == related_case_id:
            raise ValueError("不能关联自身")
        if not cls.get(case_id) or not cls.get(related_case_id):
            raise ValueError("用例不存在")
        cls._ensure_management_tables()
        existing = cls.query_one(
            """SELECT id FROM case_relations WHERE case_id=? AND related_case_id=? AND relation_type=?""",
            (case_id, related_case_id, relation_type),
        )
        if existing:
            return {"id": existing["id"], "duplicated": True}
        rel_id = cls._mgmt_id()
        cls.execute(
            """INSERT INTO case_relations (id, case_id, related_case_id, relation_type, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (rel_id, case_id, related_case_id, relation_type, time.time()),
        )
        cls.record_change_impl(case_id, CHANGE_UPDATED, field="relation",
                               new_value=f"关联[{relation_type}]: {related_case_id}")
        return {"id": rel_id, "duplicated": False}

    @classmethod
    def remove_relation_impl(cls, case_id: str, related_id: str) -> bool:
        cls._ensure_management_tables()
        cursor = cls.execute(
            """DELETE FROM case_relations WHERE case_id=? AND related_case_id=? AND relation_type='related'""",
            (case_id, related_id),
        )
        return cursor.rowcount > 0

    @classmethod
    def list_relations_impl(cls, case_id: str) -> list:
        cls._ensure_management_tables()
        return cls.query_all(
            """SELECT r.*, c.title AS related_title FROM case_relations r
               LEFT JOIN test_cases c ON c.id = r.related_case_id WHERE r.case_id = ?""",
            (case_id,),
        )

    @classmethod
    def add_dependency_impl(cls, case_id: str, depends_on: str,
                            dep_type: str = "before", description: str = "") -> dict:
        if case_id == depends_on:
            raise ValueError("不能依赖自身")
        if not cls.get(case_id) or not cls.get(depends_on):
            raise ValueError("用例不存在")
        cls._ensure_management_tables()
        existing = cls.query_one(
            "SELECT id FROM case_dependencies WHERE case_id=? AND depends_on=?",
            (case_id, depends_on),
        )
        if existing:
            return {"id": existing["id"], "duplicated": True}
        dep_id = cls._mgmt_id()
        cls.execute(
            """INSERT INTO case_dependencies (id, case_id, depends_on, dep_type, description, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (dep_id, case_id, depends_on, dep_type, description, time.time()),
        )
        cls.record_change_impl(case_id, CHANGE_UPDATED, field="dependency",
                               new_value=f"依赖[{dep_type}]: {depends_on}")
        return {"id": dep_id, "duplicated": False}

    @classmethod
    def remove_dependency_impl(cls, case_id: str, depends_on: str) -> bool:
        cls._ensure_management_tables()
        cursor = cls.execute(
            "DELETE FROM case_dependencies WHERE case_id=? AND depends_on=?",
            (case_id, depends_on),
        )
        return cursor.rowcount > 0

    @classmethod
    def list_dependencies_impl(cls, case_id: str) -> list:
        cls._ensure_management_tables()
        return cls.query_all(
            """SELECT d.*, c.title AS dep_title FROM case_dependencies d
               LEFT JOIN test_cases c ON c.id = d.depends_on WHERE d.case_id = ?""",
            (case_id,),
        )

    @classmethod
    def trash_case(cls, case_id: str, deleted_by: str = "", reason: str = "") -> bool:
        case = cls.get(case_id)
        if not case:
            return False
        cls._ensure_management_tables()
        with Database.transaction(cls.db_name) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO case_trash (id, case_id, case_data, deleted_at, deleted_by, reason)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (cls._mgmt_id(), case_id, json.dumps(case, ensure_ascii=False),
                 time.time(), deleted_by, reason),
            )
            conn.execute("UPDATE test_cases SET status=?, updated_at=? WHERE id=?",
                         (STATUS_DEPRECATED, time.time(), case_id))
        cls.record_change_impl(case_id, CHANGE_DELETED, operator=deleted_by, new_value=reason)
        cls.invalidate_mindmap_cache()
        return True

    @classmethod
    def restore_case(cls, case_id: str, operator: str = "") -> bool:
        cls._ensure_management_tables()
        trash = cls.query_one("SELECT * FROM case_trash WHERE case_id=?", (case_id,))
        if not trash:
            return False
        with Database.transaction(cls.db_name) as conn:
            conn.execute("UPDATE test_cases SET status=?, updated_at=? WHERE id=?",
                         (STATUS_DRAFT, time.time(), case_id))
            conn.execute("DELETE FROM case_trash WHERE case_id=?", (case_id,))
        cls.record_change_impl(case_id, CHANGE_RESTORED, operator=operator)
        cls.invalidate_mindmap_cache()
        return True

    @classmethod
    def list_trash_cases(cls) -> list:
        cls._ensure_management_tables()
        rows = cls.query_all("SELECT * FROM case_trash ORDER BY deleted_at DESC")
        result = []
        for r in rows:
            item = dict(r)
            try:
                item["case_data"] = json.loads(item.get("case_data") or "{}")
            except json.JSONDecodeError:
                item["case_data"] = {}
            result.append(item)
        return result

    @classmethod
    def list_case_versions(cls, case_id: str) -> list:
        cls._ensure_management_tables()
        return cls.query_all(
            "SELECT * FROM case_versions WHERE case_id=? ORDER BY version DESC",
            (case_id,),
        )

    @classmethod
    def get_case_version(cls, case_id: str, version: int) -> Optional[dict]:
        cls._ensure_management_tables()
        row = cls.query_one(
            "SELECT * FROM case_versions WHERE case_id=? AND version=?",
            (case_id, version),
        )
        if not row:
            return None
        item = dict(row)
        try:
            item["snapshot"] = json.loads(item.get("snapshot") or "{}")
        except json.JSONDecodeError:
            item["snapshot"] = {}
        return item

    @classmethod
    def rollback_case(cls, case_id: str, version: int, operator: str = "") -> bool:
        version_data = cls.get_case_version(case_id, version)
        if not version_data:
            return False
        snapshot = version_data["snapshot"]
        cls.create_version_impl(case_id, created_by=operator, change_desc="回滚前自动保存")
        cls.update_case(case_id, {
            "title": snapshot.get("title", ""),
            "description": snapshot.get("description", ""),
            "source_code": snapshot.get("source_code", ""),
            "test_code": snapshot.get("test_code", ""),
            "file_path": snapshot.get("file_path", ""),
            "tags": snapshot.get("tags", []),
            "status": snapshot.get("status", STATUS_DRAFT),
            "priority": snapshot.get("priority", "P2"),
            "requirement_ref": snapshot.get("requirement_ref", ""),
            "structured_cases": snapshot.get("structured_cases", []),
        })
        cls.record_change_impl(case_id, CHANGE_VERSION_ROLLED_BACK, operator=operator,
                               old_value=f"v{version}", new_value="current")
        return True

    @classmethod
    def list_case_changes(cls, case_id: str, limit: int = 50) -> list:
        cls._ensure_management_tables()
        return cls.query_all(
            """SELECT * FROM case_change_logs WHERE case_id=? ORDER BY created_at DESC LIMIT ?""",
            (case_id, int(limit)),
        )

    @classmethod
    def count_case_changes(cls, case_id: str) -> int:
        cls._ensure_management_tables()
        row = cls.query_one(
            "SELECT COUNT(*) AS cnt FROM case_change_logs WHERE case_id=?",
            (case_id,))
        return row["cnt"] if row else 0

    @classmethod
    def add_requirement(cls, case_id: str, requirement_id: str,
                        requirement_type: str = "jira",
                        requirement_title: str = "",
                        requirement_url: str = "") -> dict:
        if not cls.get(case_id):
            raise ValueError("用例不存在")
        cls._ensure_management_tables()
        existing = cls.query_one(
            "SELECT id FROM case_requirements WHERE case_id=? AND requirement_id=?",
            (case_id, requirement_id),
        )
        if existing:
            return {"id": existing["id"], "duplicated": True}
        req_id = cls._mgmt_id()
        with Database.transaction(cls.db_name) as conn:
            conn.execute(
                """INSERT INTO case_requirements
                   (id, case_id, requirement_id, requirement_type,
                    requirement_title, requirement_url, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (req_id, case_id, requirement_id, requirement_type,
                 requirement_title, requirement_url, time.time()),
            )
            conn.execute(
                "UPDATE test_cases SET requirement_ref=?, updated_at=? WHERE id=?",
                (requirement_id, time.time(), case_id))
        cls.record_change_impl(case_id, CHANGE_UPDATED, field="requirement",
                               new_value=f"{requirement_type}: {requirement_id}")
        return {"id": req_id, "duplicated": False}

    @classmethod
    def remove_requirement(cls, case_id: str, requirement_id: str) -> bool:
        cls._ensure_management_tables()
        cursor = cls.execute(
            "DELETE FROM case_requirements WHERE case_id=? AND requirement_id=?",
            (case_id, requirement_id))
        return cursor.rowcount > 0

    @classmethod
    def list_requirements(cls, case_id: str) -> list:
        cls._ensure_management_tables()
        return cls.query_all(
            "SELECT * FROM case_requirements WHERE case_id=? ORDER BY created_at DESC",
            (case_id,),
        )

    @classmethod
    def get_full_info(cls, case_id: str) -> Optional[dict]:
        case = cls.get(case_id)
        if not case:
            return None
        case["relations"] = cls.list_relations_impl(case_id)
        case["dependencies"] = cls.list_dependencies_impl(case_id)
        case["reviews"] = cls.get_reviews(case_id)
        case["versions"] = cls.list_case_versions(case_id)
        case["changes"] = cls.list_case_changes(case_id)
        case["requirements"] = cls.list_requirements(case_id)
        return case

    @classmethod
    def _mindmap_tree(cls, project_filter: str = "") -> dict:
        cases = cls.list_cases_raw(limit=1000)
        if project_filter:
            cases = [c for c in cases if project_filter in (c.get("file_path") or "")]
        tree = {"id": "root", "text": "测试用例库", "children": []}
        type_groups: Dict[str, List[dict]] = {}
        for c in cases:
            tt = c.get("test_type") or "functional"
            type_groups.setdefault(tt, []).append(c)
        test_type_names = {
            "functional": "功能测试", "api": "接口测试", "ui": "UI 测试",
            "performance": "性能测试", "security": "安全测试",
            "compatibility": "兼容性测试", "reliability": "可靠性测试",
        }
        for tt, tcases in type_groups.items():
            type_node = {"id": f"type_{tt}", "text": f"{test_type_names.get(tt, tt)} ({len(tcases)})", "children": []}
            for prio in ["P0", "P1", "P2", "P3"]:
                pcases = [c for c in tcases if (c.get("priority") or "P2") == prio]
                if pcases:
                    prio_node = {"id": f"prio_{prio}", "text": f"{prio} 优先级 ({len(pcases)})", "children": []}
                    for c in pcases:
                        prio_node["children"].append({
                            "id": c["id"], "text": c.get("title", ""),
                            "status": c.get("status", "draft"), "case_id": c["id"], "type": "case",
                        })
                    type_node["children"].append(prio_node)
            tree["children"].append(type_node)
        return tree

    @classmethod
    def get_mindmap(cls, project_filter: str = "") -> dict:
        cache_key = f"mindmap:{project_filter}"
        now = time.time()
        entry = cls._mindmap_cache.get(cache_key)
        if entry is not None and (now - entry[0]) < cls._MINDMAP_CACHE_TTL:
            return entry[1]
        tree = cls._mindmap_tree(project_filter)
        cls._mindmap_cache[cache_key] = (time.time(), tree)
        return tree

    @classmethod
    def export_excel_impl(cls, cases: list) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "标题", "描述", "类型", "优先级", "状态", "标签", "文件路径", "需求关联", "创建时间"])
        for c in cases:
            tags = ",".join(c.get("tags") or [])
            writer.writerow([
                c.get("id", ""), c.get("title", ""), c.get("description", ""),
                c.get("test_type", "functional"), c.get("priority", "P2"),
                c.get("status", "draft"), tags, c.get("file_path", ""),
                c.get("requirement_ref", ""),
                datetime.fromtimestamp(c.get("created_at") or 0).strftime("%Y-%m-%d %H:%M:%S"),
            ])
        return ("\ufeff" + output.getvalue()).encode("utf-8")

    @classmethod
    def export_mindmap_impl(cls, cases: list = None) -> str:
        return json.dumps(cls.get_mindmap(), ensure_ascii=False, indent=2)

    @classmethod
    def _import_one(cls, title: str, description: str = "", file_path: str = "",
                    tags: Optional[List[str]] = None, status: str = STATUS_DRAFT,
                    priority: str = PRIORITY_P2, test_type: str = "",
                    requirement_ref: str = "", operator: str = "") -> Optional[dict]:
        if not title:
            return None
        if priority not in VALID_PRIORITIES:
            priority = PRIORITY_P2
        case = cls.create({
            "title": title, "description": description, "file_path": file_path,
            "tags": tags or [], "status": status, "priority": priority,
            "test_type": test_type, "requirement_ref": requirement_ref,
        })
        if case:
            cid = case.get("id", "")
            try:
                cls.record_change_impl(cid, CHANGE_CREATED, field="title", new_value=title, operator=operator)
                cls.create_version_impl(cid, created_by=operator or "system", change_desc="初始版本")
                cls.record_change_impl(cid, CHANGE_IMPORTED, operator=operator)
            except Exception:
                pass
        return case

    @classmethod
    def import_excel_impl(cls, content: str, operator: str = "") -> dict:
        reader = csv.DictReader(io.StringIO(content))
        imported = 0
        errors: List[str] = []
        for row in reader:
            try:
                title = (row.get("标题") or row.get("title") or "").strip()
                if not title:
                    continue
                test_type = (row.get("类型") or row.get("test_type") or "functional").strip()
                priority = (row.get("优先级") or row.get("priority") or "P2").strip()
                tags_str = (row.get("标签") or row.get("tags") or "").strip()
                tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
                cls._import_one(
                    title=title,
                    description=row.get("描述") or row.get("description") or "",
                    file_path=row.get("文件路径") or row.get("file_path") or "",
                    tags=tags, priority=priority, test_type=test_type,
                    requirement_ref=row.get("需求关联") or row.get("requirement_ref") or "",
                    operator=operator,
                )
                imported += 1
            except Exception as e:
                errors.append(f"行 {reader.line_num}: {e}")
        cls.invalidate_mindmap_cache()
        return {"imported": imported, "errors": errors}

    @classmethod
    def import_mindmap_impl(cls, content: str, operator: str = "") -> dict:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return {"imported": 0, "errors": [f"JSON 解析失败: {e}"]}
        imported = 0
        errors: List[str] = []

        def walk_node(node, parent_type=""):
            nonlocal imported
            text = node.get("text", "")
            node_type = node.get("type", "")
            case_id = node.get("case_id", "")
            children = node.get("children", [])
            try:
                if node_type == "case" and case_id:
                    if cls.get(case_id):
                        return
                    cls._import_one(title=text, test_type=parent_type or "functional", operator=operator)
                    imported += 1
                elif case_id:
                    if not cls.get(case_id):
                        cls._import_one(title=text, operator=operator)
                        imported += 1
            except Exception as e:
                errors.append(f"节点「{text}」: {e}")
            for child in children:
                walk_node(child, parent_type=node.get("id", "") or parent_type)

        walk_node(data)
        cls.invalidate_mindmap_cache()
        return {"imported": imported, "errors": errors}


# 单例
case_repository = CaseRepository()