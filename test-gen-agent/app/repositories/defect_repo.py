# app/repositories/defect_repo.py
"""缺陷数据访问层（Phase 3 重构 · 4 层对齐）。

本层只做 SQLite 读写（create/get/update/list/count/stats/软删除/回收站），
输出与旧 app.defects.tracker 完全一致，供 service 层消费。
"""
import time
import uuid
from typing import List, Optional

from app.core.database import Database
from app.repositories.base import BaseRepo

# 缺陷状态 / 严重程度（与旧 app.defects.tracker 保持一致）
STATUS_OPEN = "open"
STATUS_IN_PROGRESS = "in_progress"
STATUS_FIXED = "fixed"
STATUS_CLOSED = "closed"
STATUS_WONT_FIX = "wont_fix"
VALID_STATUSES = {STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_FIXED, STATUS_CLOSED, STATUS_WONT_FIX}

SEVERITY_BLOCKER = "blocker"
SEVERITY_CRITICAL = "critical"
SEVERITY_MAJOR = "major"
SEVERITY_MINOR = "minor"
SEVERITY_TRIVIAL = "trivial"
VALID_SEVERITIES = {
    SEVERITY_BLOCKER, SEVERITY_CRITICAL, SEVERITY_MAJOR, SEVERITY_MINOR, SEVERITY_TRIVIAL,
}


class DefectRepo(BaseRepo):
    db_name = "defects.db"
    table_name = "defects"

    # 建表守卫：首访连接时懒触发一次建表（defects + defect_comments）。
    # 收敛到 get_conn()，让 get / get_checked / get_comment / list_comments /
    # purge / update 等在冷启动空库下自动建表，杜绝 no such table。
    _schema_ensured = False

    # ── 建表 ──────────────────────────────────────────────
    @classmethod
    def _ensure_table(cls) -> None:
        conn = Database.get_conn(cls.db_name)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS defects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                severity TEXT DEFAULT 'major',
                status TEXT DEFAULT 'open',
                file_path TEXT DEFAULT '',
                test_case_id TEXT DEFAULT '',
                error_snippet TEXT DEFAULT '',
                created_at REAL,
                updated_at REAL,
                assignee TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                deleted INTEGER DEFAULT 0,
                deleted_at REAL
            )
        """)
        # 兼容旧库：为已存在的缺陷表补充 tags 列（无 tags 列时执行 ALTER TABLE）
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(defects)")}
        if "tags" not in existing_cols:
            conn.execute("ALTER TABLE defects ADD COLUMN tags TEXT DEFAULT '[]'")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS defect_comments (
                id TEXT PRIMARY KEY,
                bug_id TEXT NOT NULL,
                parent_id TEXT DEFAULT '',
                content TEXT DEFAULT '',
                create_user TEXT DEFAULT '',
                reply_user TEXT DEFAULT '',
                notifier TEXT DEFAULT '',
                create_time REAL,
                update_time REAL,
                deleted INTEGER DEFAULT 0
            )
        """)
        conn.commit()

    @classmethod
    def get_conn(cls):
        """返回连接前确保缺陷相关表存在（首访懒触发一次）。

        缺陷与评论表在同一 _ensure_table 内幂等创建，统一入口可覆盖所有
        BaseRepo 查询/写路径，避免此前 get / list_comments 等无守卫方法
        在冷启动空库下直接触发 no such table: defects / defect_comments。
        """
        if not cls._schema_ensured:
            cls._ensure_table()
            cls._schema_ensured = True
        return Database.get_conn(cls.db_name)

    @classmethod
    def _build_filters(cls, status: str = "", severity: str = "",
                       include_deleted: bool = False) -> tuple:
        """构造 WHERE 子句与参数（与旧 tracker 同源）。"""
        clause = " WHERE 1=1"
        params: list = []
        if not include_deleted:
            clause += " AND (deleted IS NULL OR deleted = 0)"
        if status and status in VALID_STATUSES:
            clause += " AND status = ?"
            params.append(status)
        if severity and severity in VALID_SEVERITIES:
            clause += " AND severity = ?"
            params.append(severity)
        return clause, params

    # ── CRUD ──────────────────────────────────────────────
    @classmethod
    def create(cls, data: dict) -> dict:
        """创建缺陷（与 tracker.create_defect 输出一致）。"""
        cls._ensure_table()
        defect_id = data.get("id") or uuid.uuid4().hex[:12]
        now = time.time()
        import json as _json
        tags = data.get("tags") or []
        if isinstance(tags, str):
            try:
                tags = _json.loads(tags)
            except Exception:
                tags = []
        # 严重程度枚举校验：非法值不静默写脏，落到默认 major
        severity = data.get("severity", SEVERITY_MAJOR)
        if severity not in VALID_SEVERITIES:
            severity = SEVERITY_MAJOR
        record = {
            "id": defect_id,
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "severity": severity,
            "status": data.get("status", STATUS_OPEN),
            "file_path": data.get("file_path", ""),
            "test_case_id": data.get("test_case_id", ""),
            "error_snippet": data.get("error_snippet", ""),
            "created_at": now,
            "updated_at": now,
            "assignee": data.get("assignee", ""),
            "tags": _json.dumps(tags, ensure_ascii=False),
            "deleted": 0,
        }
        cls.execute(
            """INSERT INTO defects
               (id, title, description, severity, status, file_path,
                test_case_id, error_snippet, created_at, updated_at, assignee, tags, deleted)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            tuple(record.values()),
        )
        return cls.get_by_id(defect_id) or record

    @classmethod
    def get(cls, defect_id: str) -> Optional[dict]:
        """获取单个缺陷（不做软删除过滤）。"""
        return cls.get_by_id(defect_id)

    @classmethod
    def get_checked(cls, defect_id: str) -> Optional[dict]:
        """获取未删除的缺陷。"""
        return cls.query_one(
            "SELECT * FROM defects WHERE id=? AND (deleted IS NULL OR deleted=0)",
            (defect_id,),
        )

    @classmethod
    def list(cls, status: str = "", severity: str = "", limit: int = 100,
             offset: int = 0, include_deleted: bool = False) -> List[dict]:
        """分页列出缺陷。"""
        cls._ensure_table()
        clause, params = cls._build_filters(status=status, severity=severity,
                                             include_deleted=include_deleted)
        query = "SELECT * FROM defects" + clause
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params = list(params) + [int(limit), int(offset)]
        return cls.query_all(query, tuple(params))

    @classmethod
    def count(cls, status: str = "", severity: str = "",
              include_deleted: bool = False) -> int:
        """统计符合条件的缺陷数。"""
        cls._ensure_table()
        clause, params = cls._build_filters(status=status, severity=severity,
                                             include_deleted=include_deleted)
        row = cls.query_one(
            "SELECT COUNT(*) AS cnt FROM defects" + clause, tuple(params),
        )
        return row["cnt"] if row else 0

    @classmethod
    def update(cls, defect_id: str, data: dict) -> Optional[dict]:
        """更新缺陷，校验非法状态/严重程度时抛 ValueError。"""
        existing = cls.get(defect_id)
        if not existing:
            return None

        allowed = {"title", "description", "severity", "status", "file_path",
                   "test_case_id", "error_snippet", "assignee", "tags"}
        updates = {k: v for k, v in data.items() if k in allowed and v is not None}

        if "status" in updates and updates["status"] not in VALID_STATUSES:
            raise ValueError(f"无效状态: {updates['status']}")
        if "severity" in updates and updates["severity"] not in VALID_SEVERITIES:
            raise ValueError(f"无效严重程度: {updates['severity']}")
        if "tags" in updates:
            import json as _json
            if isinstance(updates["tags"], (list, tuple)):
                updates["tags"] = _json.dumps(list(updates["tags"]), ensure_ascii=False)

        if not updates:
            return existing

        updates["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [defect_id]
        cls.execute(
            f"UPDATE defects SET {set_clause} WHERE id = ?", tuple(values),
        )
        return cls.get(defect_id)

    @classmethod
    def delete(cls, defect_id: str, permanent: bool = False) -> bool:
        """删除缺陷。默认软删除，permanent=True 彻底删除。"""
        cls._ensure_table()
        if permanent:
            cursor = cls.execute("DELETE FROM defects WHERE id = ?", (defect_id,))
            return cursor.rowcount > 0
        cursor = cls.execute(
            "UPDATE defects SET deleted=1, deleted_at=? WHERE id=?",
            (time.time(), defect_id),
        )
        return cursor.rowcount > 0

    @classmethod
    def soft_delete(cls, defect_id: str) -> bool:
        """软删除缺陷，移入回收站。"""
        return cls.delete(defect_id, permanent=False)

    @classmethod
    def purge(cls, defect_id: str) -> bool:
        """从回收站彻底删除。"""
        return cls.delete(defect_id, permanent=True)

    @classmethod
    def restore(cls, defect_id: str) -> bool:
        """从回收站恢复。"""
        cls._ensure_table()
        cursor = cls.execute(
            "UPDATE defects SET deleted=0, deleted_at=NULL WHERE id=? AND deleted=1",
            (defect_id,),
        )
        return cursor.rowcount > 0

    @classmethod
    def list_trash(cls, limit: int = 100, offset: int = 0) -> List[dict]:
        """列出回收站缺陷。"""
        cls._ensure_table()
        return cls.query_all(
            "SELECT * FROM defects WHERE deleted=1 "
            "ORDER BY deleted_at DESC LIMIT ? OFFSET ?",
            (int(limit), int(offset)),
        )

    @classmethod
    def count_trash(cls) -> int:
        """统计回收站数量。"""
        cls._ensure_table()
        row = cls.query_one("SELECT COUNT(*) AS cnt FROM defects WHERE deleted=1")
        return row["cnt"] if row else 0

    @classmethod
    def get_stats(cls) -> dict:
        """获取缺陷统计。"""
        conn = cls.get_conn()
        total = conn.execute(
            "SELECT COUNT(*) FROM defects WHERE (deleted IS NULL OR deleted=0)"
        ).fetchone()[0]
        trash = conn.execute("SELECT COUNT(*) FROM defects WHERE deleted=1").fetchone()[0]
        by_status = {s: 0 for s in sorted(VALID_STATUSES)}
        for row in conn.execute(
            "SELECT status, COUNT(*) AS cnt FROM defects "
            "WHERE (deleted IS NULL OR deleted=0) GROUP BY status"
        ):
            if row["status"] in by_status:
                by_status[row["status"]] = row["cnt"]
        return {"total": total, "trash": trash, "by_status": by_status}

    # ── 评论 ──────────────────────────────────────────────
    @classmethod
    def create_comment(cls, bug_id: str, content: str = "", parent_id: str = "",
                       create_user: str = "", reply_user: str = "", notifier: str = "") -> dict:
        """创建缺陷评论。"""
        cls._ensure_table()
        comment_id = str(uuid.uuid4())
        now = time.time()
        cls.execute(
            """INSERT INTO defect_comments
               (id, bug_id, parent_id, content, create_user, reply_user,
                notifier, create_time, update_time, deleted)
               VALUES (?,?,?,?,?,?,?,?,?,0)""",
            (comment_id, bug_id, parent_id, content, create_user,
             reply_user, notifier, now, now),
        )
        return cls.get_comment(comment_id)

    @classmethod
    def get_comment(cls, comment_id: str) -> Optional[dict]:
        return cls.query_one(
            "SELECT * FROM defect_comments WHERE id=? AND deleted=0",
            (comment_id,),
        )

    @classmethod
    def list_comments(cls, bug_id: str) -> List[dict]:
        return cls.query_all(
            "SELECT * FROM defect_comments WHERE bug_id=? AND deleted=0 "
            "ORDER BY create_time ASC",
            (bug_id,),
        )

    @classmethod
    def update_comment(cls, comment_id: str, content: str) -> Optional[dict]:
        existing = cls.get_comment(comment_id)
        if not existing:
            return None
        cls.execute(
            "UPDATE defect_comments SET content=?, update_time=? WHERE id=?",
            (content, time.time(), comment_id),
        )
        return cls.get_comment(comment_id)

    @classmethod
    def delete_comment(cls, comment_id: str) -> bool:
        cls._ensure_table()
        cursor = cls.execute(
            "UPDATE defect_comments SET deleted=1, update_time=? WHERE id=?",
            (time.time(), comment_id),
        )
        cls.execute(
            "UPDATE defect_comments SET deleted=1, update_time=? WHERE parent_id=?",
            (time.time(), comment_id),
        )
        return cursor.rowcount > 0



    # ── 自动创建（测试失败触发）────────────────────────────
    @classmethod
    def auto_create_from_result(cls, file_path: str, test_result: dict,
                                test_case_id: str = "") -> Optional[dict]:
        """测试失败时自动创建缺陷（迁移自旧 app.defects.tracker）。"""
        if test_result.get("passed"):
            return None

        stderr = test_result.get("stderr", "") or ""
        stdout = test_result.get("stdout", "") or ""
        combined = stderr + "\n" + stdout

        # 根据错误类型判断严重程度
        severity = SEVERITY_MAJOR
        if any(k in combined.lower() for k in ("error", "traceback", "failed")):
            severity = SEVERITY_CRITICAL
        if any(k in combined.lower() for k in ("exception", "segmentation")):
            severity = SEVERITY_BLOCKER

        # 提取错误摘要
        title = f"测试失败: {file_path}"
        if "AssertionError" in combined:
            title = f"断言失败: {file_path}"
        elif "ImportError" in combined or "ModuleNotFoundError" in combined:
            title = f"导入错误: {file_path}"
        elif "TypeError" in combined:
            title = f"类型错误: {file_path}"
        elif "SyntaxError" in combined:
            title = f"语法错误: {file_path}"

        return cls.create({
            "title": title,
            "description": f"测试自动检测到失败。\n\n文件: {file_path}\n\n输出:\n```\n{combined[:2000]}\n```",
            "severity": severity,
            "file_path": file_path,
            "test_case_id": test_case_id,
            "error_snippet": combined[:500],
        })

# 兼容旧接口
defect_repo = DefectRepo
