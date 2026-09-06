# app/repositories/case_repo.py
"""用例数据访问层（Phase 3 重构 · 4 层对齐）。

本层是 routers 的 DB 访问唯一入口，替代旧 `app.cases.repository`。
职责：
  - 只做 SQLite 读写（create/get/update/list/count/stats/soft-delete）
  - 输出「归一化」记录，字段形态与旧 app.cases.repository 完全一致：
      tags / structured_cases / metadata 已反序列化为 list/dict，
      并额外从 metadata 提取 test_type 顶层字段。
这样 service 与 router 可以直接消费，不必再自行拼 JSON。

验收口径：本层不改动任何路由行为（零回归由测试套件保证），
并与旧层在相同数据库上的 CRUD 输出逐条一致。
"""
import csv
import io
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.repositories.base import BaseRepo

# 用例状态 / 优先级常量（与旧 app.cases.repository 保持一致）
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

# 评审状态（与旧 app.cases.management 保持一致）
REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_APPROVED = "approved"
REVIEW_STATUS_REJECTED = "rejected"
REVIEW_STATUS_NEED_REVISE = "need_revise"

# 变更动作（与旧 app.cases.management 保持一致）
CHANGE_DELETED = "deleted"
CHANGE_RESTORED = "restored"
CHANGE_VERSION_CREATED = "version_created"
CHANGE_VERSION_ROLLED_BACK = "version_rolled_back"
CHANGE_REVIEW_SUBMITTED = "review_submitted"
CHANGE_REVIEW_APPROVED = "review_approved"
CHANGE_REVIEW_REJECTED = "review_rejected"
CHANGE_IMPORTED = "imported"
CHANGE_EXPORTED = "exported"




class CaseRepo(BaseRepo):
    db_name = "testcases.db"
    table_name = "test_cases"

    # 变更动作（与旧 cases.management 保持一致）
    CHANGE_CREATED = "created"
    CHANGE_UPDATED = "updated"

    # 建表守卫：首访连接时懒触发一次主表创建。
    # 收敛到 get_conn()（BaseRepo.query_one/query_all/execute 统一入口），
    # 冷启动空库下 get / list_cases / update / soft_delete / get_stats 等
    # 任意公开方法都会先建出 test_cases 表，杜绝 no such table: test_cases。
    _schema_ensured = False

    # ── 归一化 ──────────────────────────────────────────────
    @classmethod
    def _normalize_record(cls, data: dict) -> dict:
        """把裸数据库行转成与旧 app.cases.repository._row_to_dict 一致的形态。"""
        out = dict(data)
        # tags
        try:
            out["tags"] = json.loads(out.get("tags") or "[]")
        except (json.JSONDecodeError, TypeError):
            out["tags"] = []
        # metadata
        try:
            out["metadata"] = json.loads(out.get("metadata") or "{}")
        except (json.JSONDecodeError, TypeError):
            out["metadata"] = {}
        # structured_cases（兼容双重编码）
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
        # test_type 从 metadata 提取
        if isinstance(out.get("metadata"), dict):
            out["test_type"] = out["metadata"].get("test_type", "")
        # last_result 反序列化
        if out.get("last_result"):
            try:
                out["last_result"] = json.loads(out["last_result"])
            except (json.JSONDecodeError, TypeError):
                pass
        return out

    @classmethod
    def get_by_id(cls, record_id: Any, id_col: str = "id") -> Optional[dict]:
        """按 ID 查询（归一化输出）。"""
        row = cls.query_one(
            f"SELECT * FROM {cls.table_name} WHERE {id_col}=?", (record_id,)
        )
        return cls._normalize_record(row) if row else None

    @classmethod
    def get(cls, case_id: str) -> Optional[dict]:
        """获取未删除（非回收站 deprecated）用例。"""
        row = cls.query_one(
            "SELECT * FROM test_cases WHERE id=? AND status != ?",
            (case_id, STATUS_DEPRECATED),
        )
        return cls._normalize_record(row) if row else None

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
    def get_conn(cls):
        """返回 testcases.db 连接；首访懒触发主表建表守卫。

        主表 test_cases 的 DDL 在仓库内联（_ensure_table），管理类辅助表
        （case_relations 等）由 _ensure_management_tables 按需建。此守卫
        只负责主表——它在 BaseRepo 的 query/execute 统一入口上触发，让所有
        公开方法（含此前无守卫的 get/list_cases/update/soft_delete/get_stats）
        在冷启动空库下都能自动建表。
        """
        if not cls._schema_ensured:
            cls._ensure_table()
            cls._schema_ensured = True
        return Database.get_conn(cls.db_name)

    @classmethod
    def _build_filters(cls, status=None, priority=None, tag=None,
                       search=None, test_type=None, module_id=None) -> tuple:
        """构造 WHERE 子句与参数（与旧 app.cases.repository 同源）。"""
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

    # ── CRUD ────────────────────────────────────────────────
    @classmethod
    def create(cls, data: dict) -> dict:
        """创建用例（输出归一化）。"""
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
            "structured_cases": json.dumps(
                data.get("structured_cases", []), ensure_ascii=False),
        }
        cols = list(record.keys())
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO test_cases ({', '.join(cols)}) VALUES ({placeholders})"
        cls.execute(sql, tuple(record.values()))
        return cls.get(case_id) or record

    @classmethod
    def update(cls, case_id: str, data: dict) -> Optional[dict]:
        """更新用例（输出归一化；校验状态/优先级）。"""
        existing = cls.get(case_id)
        if not existing:
            return None

        updates = dict(data)
        updates["updated_at"] = time.time()

        # test_type 合并进 metadata
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
    def list_cases(cls, status=None, priority=None, tag=None, search=None,
                   test_type=None, module_id=None,
                   limit: int = 100, offset: int = 0) -> List[dict]:
        """分页列出未删除用例，updated_at 倒序。"""
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
        """统计符合条件的用例数（数据库侧聚合）。"""
        clause, params = cls._build_filters(
            status=status, priority=priority, tag=tag,
            search=search, test_type=test_type, module_id=module_id,
        )
        row = cls.query_one("SELECT COUNT(*) AS cnt FROM test_cases" + clause,
                            tuple(params))
        return row["cnt"] if row else 0

    @classmethod
    def get_stats(cls) -> dict:
        """获取用例库统计（含回收站口径与旧层一致：total 为全表）。"""
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
    def soft_delete(cls, case_id: str) -> Optional[dict]:
        """软删除：置为 deprecated（回收站），不物理删除。"""
        return cls.update(case_id, {"status": STATUS_DEPRECATED})

    @classmethod
    def hard_delete(cls, case_id: str) -> bool:
        """物理删除。

        与 purge_case 一致：先清理各关联子表（case_relations /
        case_dependencies / case_reviews / case_versions /
        case_change_logs / case_requirements / case_trash）再删主表，
        避免 FOREIGN KEY constraint failed。
        """
        cls._ensure_management_tables()
        with Database.transaction(cls.db_name) as conn:
            cls._delete_child_records(conn, case_id)
        cls.invalidate_mindmap_cache()
        return bool(cls.delete(case_id))

    @classmethod
    def _delete_child_records(cls, conn, case_id: str) -> None:
        """删除用例的所有关联子表记录（须在事务中调用）。

        覆盖所有引用 test_cases(id) 的子表：
          case_relations/case_dependencies/case_reviews/case_versions/
          case_requirements（带 FK），以及 case_change_logs/case_trash
          （无 FK 但逻辑上从属于该用例）。任一步失败整体回滚。
        """
        conn.execute(
            "DELETE FROM case_relations WHERE case_id=? OR related_case_id=?",
            (case_id, case_id))
        conn.execute(
            "DELETE FROM case_dependencies WHERE case_id=? OR depends_on=?",
            (case_id, case_id))
        conn.execute("DELETE FROM case_reviews WHERE case_id=?", (case_id,))
        conn.execute("DELETE FROM case_versions WHERE case_id=?", (case_id,))
        conn.execute("DELETE FROM case_change_logs WHERE case_id=?", (case_id,))
        conn.execute("DELETE FROM case_requirements WHERE case_id=?", (case_id,))
        conn.execute("DELETE FROM case_trash WHERE case_id=?", (case_id,))

    # ════ 用例域辅助表 数据访问（去空壳化：下沉为仓库直连 SQL）═══
    # 输出与旧 app.cases.management.* 逐一对齐，由对齐测试守护零回归。
    # 说明：脑图 / Excel / XMind 导入导出属「业务编排 + 文件格式」，非
    # 纯表 SQL，仍委托 cases.management 编排层（Repository 不做该副作用）。

    @classmethod
    def _ensure_management_tables(cls) -> None:
        """确保用例高级管理辅助表存在。

        case_relations/case_dependencies/case_reviews/case_versions/
        case_change_logs/case_trash/case_requirements 的表结构由
        app.cases.management._init_management_tables 单一权威建表
        （schema_registry 唯一来源，避免跨模块 DDL 漂移）。仓库层只做
        数据访问，不再重复 CREATE TABLE。
        """
        from app.cases.management import _init_management_tables
        _init_management_tables()

    @classmethod
    def _ensure_tables(cls) -> None:
        cls._ensure_table()
        cls._ensure_management_tables()

    @classmethod
    def _mgmt_id(cls) -> str:
        return uuid.uuid4().hex[:12]

    # ════ 变更记录 / 版本 ════
    @classmethod
    def record_change(cls, case_id: str, action: str, field: str = "",
                      old_value: str = "", new_value: str = "",
                      operator: str = "") -> None:
        """记录用例变更日志（直连 SQL）。"""
        cls._ensure_management_tables()
        try:
            cls.execute(
                """INSERT INTO case_change_logs
                   (id, case_id, action, field, old_value, new_value, operator, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (cls._mgmt_id(), case_id, action, field, old_value,
                 new_value, operator, time.time()),
            )
        except Exception:
            pass

    @classmethod
    def create_version(cls, case_id: str, created_by: str = "",
                       change_desc: str = "") -> int:
        """创建用例版本快照（直连 SQL）。"""
        case = cls.get(case_id)
        if not case:
            return 0
        cls._ensure_management_tables()
        row = cls.query_one(
            "SELECT MAX(version) AS max_v FROM case_versions WHERE case_id=?",
            (case_id,),
        )
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
            (cls._mgmt_id(), case_id, version, snapshot, time.time(),
             created_by, change_desc),
        )
        cls.record_change(case_id, CHANGE_VERSION_CREATED, operator=created_by,
                          new_value=f"v{version}", field="version")
        return version

    # 脑图缓存（Repository 内部直连缓存；同时清空旧 management 缓存，
    # 确保新旧链路数据一致，避免零回归漂移）
    _mindmap_cache: Dict[str, tuple] = {}  # cache_key -> (timestamp, tree)
    _MINDMAP_CACHE_TTL = 10.0  # 秒

    @classmethod
    def invalidate_mindmap_cache(cls) -> None:
        cls._mindmap_cache.clear()
        try:
            from app.cases.management import invalidate_mindmap_cache as _m_inv
            _m_inv()
        except Exception:
            pass

    # ════ 用例关联 ════
    @classmethod
    def add_relation(cls, case_id: str, related_case_id: str,
                     relation_type: str = "related") -> dict:
        if case_id == related_case_id:
            raise ValueError("不能关联自身")
        if not cls.get(case_id) or not cls.get(related_case_id):
            raise ValueError("用例不存在")
        cls._ensure_management_tables()
        existing = cls.query_one(
            """SELECT id FROM case_relations
               WHERE case_id=? AND related_case_id=? AND relation_type=?""",
            (case_id, related_case_id, relation_type),
        )
        if existing:
            return {"id": existing["id"], "duplicated": True}
        rel_id = cls._mgmt_id()
        cls.execute(
            """INSERT INTO case_relations
               (id, case_id, related_case_id, relation_type, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (rel_id, case_id, related_case_id, relation_type, time.time()),
        )
        cls.record_change(case_id, cls.CHANGE_UPDATED, field="relation",
                          new_value=f"关联[{relation_type}]: {related_case_id}")
        return {"id": rel_id, "duplicated": False}

    @classmethod
    def remove_relation(cls, case_id: str, related_id: str) -> bool:
        """移除用例关联（与旧 remove_case_relation 默认 relation_type='related' 一致）。"""
        cls._ensure_management_tables()
        cursor = cls.execute(
            """DELETE FROM case_relations
               WHERE case_id=? AND related_case_id=? AND relation_type='related'""",
            (case_id, related_id),
        )
        return cursor.rowcount > 0

    @classmethod
    def list_relations(cls, case_id: str) -> list:
        cls._ensure_management_tables()
        return cls.query_all(
            """SELECT r.*, c.title AS related_title
               FROM case_relations r
               LEFT JOIN test_cases c ON c.id = r.related_case_id
               WHERE r.case_id = ?""",
            (case_id,),
        )

    # ════ 评审 ════
    @classmethod
    def submit_review(cls, case_id: str, reviewer: str = "",
                      comment: str = "") -> dict:
        if not cls.get(case_id):
            raise ValueError("用例不存在")
        cls._ensure_management_tables()
        rev_id = cls._mgmt_id()
        cls.execute(
            """INSERT INTO case_reviews
               (id, case_id, review_status, reviewer, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (rev_id, case_id, REVIEW_STATUS_PENDING, reviewer, comment, time.time()),
        )
        cls.update(case_id, {"status": STATUS_REVIEW})
        cls.record_change(case_id, CHANGE_REVIEW_SUBMITTED, operator=reviewer,
                          new_value=comment)
        return {"id": rev_id, "case_id": case_id, "review_status": REVIEW_STATUS_PENDING}

    @classmethod
    def approve_review(cls, case_id: str, reviewer: str = "",
                       comment: str = "") -> dict:
        cls._ensure_management_tables()
        with Database.transaction(cls.db_name) as conn:
            conn.execute(
                """UPDATE case_reviews
                   SET review_status=?, reviewer=?, comment=?, reviewed_at=?
                   WHERE case_id=?""",
                (REVIEW_STATUS_APPROVED, reviewer, comment, time.time(), case_id),
            )
            conn.execute("UPDATE test_cases SET status=?, updated_at=? WHERE id=?",
                         (STATUS_APPROVED, time.time(), case_id))
        cls.record_change(case_id, CHANGE_REVIEW_APPROVED, operator=reviewer)
        return {"case_id": case_id, "review_status": REVIEW_STATUS_APPROVED}

    @classmethod
    def reject_review(cls, case_id: str, reviewer: str = "",
                      comment: str = "") -> dict:
        cls._ensure_management_tables()
        with Database.transaction(cls.db_name) as conn:
            conn.execute(
                """UPDATE case_reviews
                   SET review_status=?, reviewer=?, comment=?, reviewed_at=?
                   WHERE case_id=?""",
                (REVIEW_STATUS_REJECTED, reviewer, comment, time.time(), case_id),
            )
            conn.execute("UPDATE test_cases SET status=?, updated_at=? WHERE id=?",
                         (STATUS_DRAFT, time.time(), case_id))
        cls.record_change(case_id, CHANGE_REVIEW_REJECTED, operator=reviewer,
                          new_value=comment)
        return {"case_id": case_id, "review_status": REVIEW_STATUS_REJECTED}

    @classmethod
    def get_reviews(cls, case_id: str) -> list:
        cls._ensure_management_tables()
        return cls.query_all(
            "SELECT * FROM case_reviews WHERE case_id=? ORDER BY created_at DESC",
            (case_id,),
        )

    # ════ 依赖 ════
    @classmethod
    def add_dependency(cls, case_id: str, depends_on: str,
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
            """INSERT INTO case_dependencies
               (id, case_id, depends_on, dep_type, description, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (dep_id, case_id, depends_on, dep_type, description, time.time()),
        )
        cls.record_change(case_id, cls.CHANGE_UPDATED, field="dependency",
                          new_value=f"依赖[{dep_type}]: {depends_on}")
        return {"id": dep_id, "duplicated": False}

    @classmethod
    def remove_dependency(cls, case_id: str, depends_on: str) -> bool:
        cls._ensure_management_tables()
        cursor = cls.execute(
            "DELETE FROM case_dependencies WHERE case_id=? AND depends_on=?",
            (case_id, depends_on),
        )
        return cursor.rowcount > 0

    @classmethod
    def list_dependencies(cls, case_id: str) -> list:
        cls._ensure_management_tables()
        return cls.query_all(
            """SELECT d.*, c.title AS dep_title
               FROM case_dependencies d
               LEFT JOIN test_cases c ON c.id = d.depends_on
               WHERE d.case_id = ?""",
            (case_id,),
        )

    # ════ 回收站 ════
    @classmethod
    def trash_case(cls, case_id: str, deleted_by: str = "",
                   reason: str = "") -> bool:
        case = cls.get(case_id)
        if not case:
            return False
        cls._ensure_management_tables()
        with Database.transaction(cls.db_name) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO case_trash
                   (id, case_id, case_data, deleted_at, deleted_by, reason)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (cls._mgmt_id(), case_id, json.dumps(case, ensure_ascii=False),
                 time.time(), deleted_by, reason),
            )
            conn.execute("UPDATE test_cases SET status=?, updated_at=? WHERE id=?",
                         (STATUS_DEPRECATED, time.time(), case_id))
        cls.record_change(case_id, CHANGE_DELETED, operator=deleted_by,
                          new_value=reason)
        cls.invalidate_mindmap_cache()
        return True

    @classmethod
    def restore_case(cls, case_id: str, operator: str = "") -> bool:
        cls._ensure_management_tables()
        trash = cls.query_one(
            "SELECT * FROM case_trash WHERE case_id=?", (case_id,))
        if not trash:
            return False
        with Database.transaction(cls.db_name) as conn:
            conn.execute("UPDATE test_cases SET status=?, updated_at=? WHERE id=?",
                         (STATUS_DRAFT, time.time(), case_id))
            conn.execute("DELETE FROM case_trash WHERE case_id=?", (case_id,))
        cls.record_change(case_id, CHANGE_RESTORED, operator=operator)
        cls.invalidate_mindmap_cache()
        return True

    @classmethod
    def purge_case(cls, case_id: str) -> bool:
        """从回收站彻底删除用例（连同各关联表数据）。"""
        cls._ensure_management_tables()
        with Database.transaction(cls.db_name) as conn:
            cls._delete_child_records(conn, case_id)
        cls.invalidate_mindmap_cache()
        return bool(cls.delete(case_id))

    @classmethod
    def list_trash_cases(cls) -> list:
        cls._ensure_management_tables()
        rows = cls.query_all(
            "SELECT * FROM case_trash ORDER BY deleted_at DESC")
        result = []
        for r in rows:
            item = dict(r)
            try:
                item["case_data"] = json.loads(item.get("case_data") or "{}")
            except json.JSONDecodeError:
                item["case_data"] = {}
            result.append(item)
        return result

    # ════ 版本管理 ════
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
    def rollback_case(cls, case_id: str, version: int,
                      operator: str = "") -> bool:
        version_data = cls.get_case_version(case_id, version)
        if not version_data:
            return False
        snapshot = version_data["snapshot"]
        cls.create_version(case_id, created_by=operator, change_desc="回滚前自动保存")
        cls.update(case_id, {
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
        cls.record_change(case_id, CHANGE_VERSION_ROLLED_BACK, operator=operator,
                          old_value=f"v{version}", new_value="current")
        return True

    @classmethod
    def list_case_changes(cls, case_id: str, limit: int = 50) -> list:
        cls._ensure_management_tables()
        return cls.query_all(
            """SELECT * FROM case_change_logs
               WHERE case_id=? ORDER BY created_at DESC LIMIT ?""",
            (case_id, int(limit)),
        )

    @classmethod
    def count_case_changes(cls, case_id: str) -> int:
        cls._ensure_management_tables()
        row = cls.query_one(
            "SELECT COUNT(*) AS cnt FROM case_change_logs WHERE case_id=?",
            (case_id,))
        return row["cnt"] if row else 0

    # ════ 需求关联 ════
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
        cls.record_change(case_id, cls.CHANGE_UPDATED, field="requirement",
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

    # ════ 完整信息（组合各下沉读取，不委托旧层）════
    @classmethod
    def get_full_info(cls, case_id: str) -> Optional[dict]:
        case = cls.get(case_id)
        if not case:
            return None
        case["relations"] = cls.list_relations(case_id)
        case["dependencies"] = cls.list_dependencies(case_id)
        case["reviews"] = cls.get_reviews(case_id)
        case["versions"] = cls.list_case_versions(case_id)
        case["changes"] = cls.list_case_changes(case_id)
        case["requirements"] = cls.list_requirements(case_id)
        return case

    # ════ 脑图 / 导入导出（Repository 内部直连 SQL，不委托 cases.management）════

    @classmethod
    def _mindmap_tree(cls, project_filter: str = "") -> dict:
        """构建用例脑图树（Repository 层实现，直连 SQL 读取）。

        结构：项目(无)/测试类型 → 优先级 → 用例列表，与旧 management 层输出一致。
        """
        cases = cls.list_cases(limit=1000)
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
            type_node = {"id": f"type_{tt}",
                         "text": f"{test_type_names.get(tt, tt)} ({len(tcases)})",
                         "children": []}
            for prio in ["P0", "P1", "P2", "P3"]:
                pcases = [c for c in tcases if (c.get("priority") or "P2") == prio]
                if pcases:
                    prio_node = {"id": f"prio_{prio}",
                                 "text": f"{prio} 优先级 ({len(pcases)})",
                                 "children": []}
                    for c in pcases:
                        prio_node["children"].append({
                            "id": c["id"], "text": c.get("title", ""),
                            "status": c.get("status", "draft"),
                            "case_id": c["id"], "type": "case",
                        })
                    type_node["children"].append(prio_node)
            tree["children"].append(type_node)
        return tree

    @classmethod
    def get_mindmap(cls, project_filter: str = "") -> dict:
        """获取用例脑图树，带 10s 内存缓存。"""
        import time as _t
        cache_key = f"mindmap:{project_filter}"
        now = _t.time()
        entry = cls._mindmap_cache.get(cache_key)
        if entry is not None and (now - entry[0]) < cls._MINDMAP_CACHE_TTL:
            return entry[1]
        tree = cls._mindmap_tree(project_filter)
        cls._mindmap_cache[cache_key] = (_t.time(), tree)
        return tree

    @classmethod
    def export_excel(cls, cases: list) -> bytes:
        """导出用例为 Excel 兼容 CSV（带 BOM）。"""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "标题", "描述", "类型", "优先级", "状态",
                         "标签", "文件路径", "需求关联", "创建时间"])
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
    def export_mindmap(cls, cases: list = None) -> str:
        """导出全库用例为 XMind 兼容 JSON。"""
        return json.dumps(cls.get_mindmap(), ensure_ascii=False, indent=2)

    @classmethod
    def _import_one(cls, title: str, description: str = "", file_path: str = "",
                    tags: Optional[List[str]] = None, status: str = STATUS_DRAFT,
                    priority: str = PRIORITY_P2, test_type: str = "",
                    requirement_ref: str = "", operator: str = "") -> Optional[dict]:
        """创建单条导入用例。

        与旧层 create_case + 显式 imported 记录的审计语义对齐：
        写入后补 created / 初始版本 / imported 变更，保证导入用例在
        变更记录与版本历史中可见（零回归）。
        """
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
                cls.record_change(cid, cls.CHANGE_CREATED, field="title",
                                  new_value=title, operator=operator)
                cls.create_version(cid, created_by=operator or "system",
                                   change_desc="初始版本")
                cls.record_change(cid, CHANGE_IMPORTED, operator=operator)
            except Exception:
                pass
        return case

    @classmethod
    def import_excel(cls, content: str, operator: str = "") -> dict:
        """从 Excel（CSV 文本）导入用例。"""
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
    def import_mindmap(cls, content: str, operator: str = "") -> dict:
        """从 XMind JSON 导入用例。"""
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
                    cls._import_one(title=text, test_type=parent_type or "functional",
                                    operator=operator)
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


# 兼容旧接口（CaseService 等引用）
case_repo = CaseRepo
