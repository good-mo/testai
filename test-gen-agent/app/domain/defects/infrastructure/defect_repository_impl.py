"""缺陷聚合仓储实现（去 Adapter，直接 SQL）。

修复说明：
  - 消除 DefectRepoAdapter 中间层（只做 entity↔dict 翻译，无业务逻辑）
  - 把 defect_repo 的 SQL 移入此处，成为域内私有实现
  - 聚合重建（from_dict）与持久化在同一个文件内闭环，不再跨文件翻译
  - DB 从 defects.db 统一为 tga.db

修复前调用链：AppService → DefectRepoAdapter → DefectRepo → SQLite（4 层）
修复后调用链：AppService → DefectRepositoryImpl → SQLite（2 层）
"""
from __future__ import annotations

import json
import time
import uuid
from typing import List, Optional, Tuple

from app.core.database import Database
from app.domain.defects.domain.entities.defect import Defect
from app.logging_config import get_logger

logger = get_logger(__name__)

# ── 域内常量 ──────────────────────────────────────────
DB_NAME = "tga.db"
TABLE_DEFECTS = "defects"
TABLE_COMMENTS = "defect_comments"

# 缺陷状态 / 严重程度
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


class DefectRepositoryImpl:
    """缺陷仓储：直接持有 SQL，不再委托 Flat Repository。"""

    def __init__(self):
        self._ensure_tables()

    @staticmethod
    def _conn():
        return Database.get_conn(DB_NAME)

    # ── 建表 ──────────────────────────────────────────────
    @classmethod
    def _ensure_tables(cls) -> None:
        """幂等建表。"""
        conn = cls._conn()
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
        # 兼容旧库：为已存在的缺陷表补充 tags 列
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

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ── 聚合重建 ──────────────────────────────────────────
    @staticmethod
    def _row_to_entity(row: dict) -> Defect:
        """数据库行 → 聚合根实体。"""
        return Defect.from_dict(dict(row))

    # ── 读 ────────────────────────────────────────────────
    def find_by_id(self, defect_id: str, include_deleted: bool = False) -> Optional[Defect]:
        conn = self._conn()
        if include_deleted:
            # 回收站 / 全部：直接查主表（含已删除行）
            for r in self.list_trash(limit=9999, offset=0)[0]:
                if str(r.id.value) == str(defect_id):
                    return r
            return None
        row = conn.execute(
            "SELECT * FROM defects WHERE id=? AND (deleted IS NULL OR deleted=0)",
            (defect_id,)
        ).fetchone()
        return self._row_to_entity(dict(row)) if row else None

    def list(self, *, status: str = "", severity: str = "", limit: int = 100,
             offset: int = 0) -> Tuple[List[Defect], int]:
        conn = self._conn()
        clause = " WHERE 1=1 AND (deleted IS NULL OR deleted = 0)"
        params: list = []
        if status and status in VALID_STATUSES:
            clause += " AND status = ?"
            params.append(status)
        if severity and severity in VALID_SEVERITIES:
            clause += " AND severity = ?"
            params.append(severity)
        
        query = "SELECT * FROM defects" + clause
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params = list(params) + [int(limit), int(offset)]
        rows = conn.execute(query, tuple(params)).fetchall()
        items = [self._row_to_entity(dict(r)) for r in rows]
        
        # Count
        count_query = "SELECT COUNT(*) AS cnt FROM defects" + clause
        count_params = params[:-2]  # Remove limit and offset
        count_row = conn.execute(count_query, tuple(count_params)).fetchone()
        total = count_row["cnt"] if count_row else 0
        
        return items, total

    def list_trash(self, limit: int = 100, offset: int = 0) -> Tuple[List[Defect], int]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM defects WHERE deleted=1 ORDER BY deleted_at DESC LIMIT ? OFFSET ?",
            (int(limit), int(offset))
        ).fetchall()
        items = [self._row_to_entity(dict(r)) for r in rows]
        
        count_row = conn.execute("SELECT COUNT(*) AS cnt FROM defects WHERE deleted=1").fetchone()
        total = count_row["cnt"] if count_row else 0
        
        return items, total

    def stats(self) -> dict:
        conn = self._conn()
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

    # ── 写 ────────────────────────────────────────────────
    def save(self, defect: Defect) -> Defect:
        """创建缺陷。"""
        conn = self._conn()
        d = defect.to_dict()
        defect_id = defect.id.value
        now = time.time()
        
        tags = d.get("tags") or []
        if isinstance(tags, list):
            tags = json.dumps(tags, ensure_ascii=False)
        
        # 严重程度枚举校验
        severity = d.get("severity", SEVERITY_MAJOR)
        if severity not in VALID_SEVERITIES:
            severity = SEVERITY_MAJOR
        
        conn.execute(
            """INSERT INTO defects
               (id, title, description, severity, status, file_path,
                test_case_id, error_snippet, created_at, updated_at, assignee, tags, deleted)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                defect_id,
                d.get("title", ""),
                d.get("description", ""),
                severity,
                d.get("status", STATUS_OPEN),
                d.get("file_path", ""),
                d.get("test_case_id", ""),
                d.get("error_snippet", ""),
                now,
                now,
                d.get("assignee", ""),
                tags,
                0,
            ),
        )
        conn.commit()
        
        # 回读
        row = conn.execute("SELECT * FROM defects WHERE id=?", (defect_id,)).fetchone()
        return self._row_to_entity(dict(row)) if row else defect

    def update(self, defect: Defect) -> Optional[Defect]:
        """更新缺陷。"""
        conn = self._conn()
        d = defect.to_dict()
        defect_id = defect.id.value
        
        existing = conn.execute("SELECT * FROM defects WHERE id=?", (defect_id,)).fetchone()
        if not existing:
            return None
        
        updates = {}
        for key in ("title", "description", "severity", "status", "file_path",
                    "test_case_id", "error_snippet", "assignee"):
            if key in d and d[key] is not None:
                updates[key] = d[key]
        
        if "tags" in d and d["tags"] is not None:
            tags = d["tags"]
            if isinstance(tags, list):
                tags = json.dumps(tags, ensure_ascii=False)
            updates["tags"] = tags
        
        if not updates:
            return defect
        
        updates["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [defect_id]
        conn.execute(f"UPDATE defects SET {set_clause} WHERE id = ?", tuple(values))
        conn.commit()
        
        # 回读
        row = conn.execute("SELECT * FROM defects WHERE id=?", (defect_id,)).fetchone()
        return self._row_to_entity(dict(row)) if row else None

    def soft_delete(self, defect_id: str) -> bool:
        conn = self._conn()
        cursor = conn.execute(
            "UPDATE defects SET deleted=1, deleted_at=? WHERE id=?",
            (time.time(), defect_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def restore(self, defect_id: str) -> bool:
        conn = self._conn()
        cursor = conn.execute(
            "UPDATE defects SET deleted=0, deleted_at=NULL WHERE id=? AND deleted=1",
            (defect_id,),
        )
        conn.commit()
        return cursor.rowcount > 0

    def purge(self, defect_id: str) -> bool:
        conn = self._conn()
        cursor = conn.execute("DELETE FROM defects WHERE id = ?", (defect_id,))
        conn.commit()
        return cursor.rowcount > 0

    def permanent_delete(self, defect_id: str) -> bool:
        return self.purge(defect_id)

    # ── 评论 ──────────────────────────────────────────────
    def list_comments(self, bug_id: str) -> List[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM defect_comments WHERE bug_id=? AND deleted=0 ORDER BY create_time ASC",
            (bug_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def create_comment(self, bug_id: str, content: str = "", parent_id: str = "",
                       create_user: str = "", reply_user: str = "", notifier: str = "") -> dict:
        conn = self._conn()
        comment_id = str(uuid.uuid4())
        now = time.time()
        conn.execute(
            """INSERT INTO defect_comments
               (id, bug_id, parent_id, content, create_user, reply_user,
                notifier, create_time, update_time, deleted)
               VALUES (?,?,?,?,?,?,?,?,?,0)""",
            (comment_id, bug_id, parent_id, content, create_user,
             reply_user, notifier, now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM defect_comments WHERE id=? AND deleted=0",
            (comment_id,)
        ).fetchone()
        return dict(row) if row else {}

    def update_comment(self, comment_id: str, content: str) -> Optional[dict]:
        conn = self._conn()
        existing = conn.execute(
            "SELECT * FROM defect_comments WHERE id=? AND deleted=0",
            (comment_id,)
        ).fetchone()
        if not existing:
            return None
        conn.execute(
            "UPDATE defect_comments SET content=?, update_time=? WHERE id=?",
            (content, time.time(), comment_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM defect_comments WHERE id=? AND deleted=0",
            (comment_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete_comment(self, comment_id: str) -> bool:
        conn = self._conn()
        cursor = conn.execute(
            "UPDATE defect_comments SET deleted=1, update_time=? WHERE id=?",
            (time.time(), comment_id),
        )
        conn.execute(
            "UPDATE defect_comments SET deleted=1, update_time=? WHERE parent_id=?",
            (time.time(), comment_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    # ── 自动创建 ──────────────────────────────────────────
    def auto_create_from_result(self, file_path: str, test_result: dict,
                                test_case_id: str = "") -> Optional[dict]:
        """测试失败时自动创建缺陷。"""
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

        # 创建缺陷
        defect = Defect(
            defect_id=self.next_id(),
            title=title,
            description=f"测试自动检测到失败。\n\n文件: {file_path}\n\n输出:\n```\n{combined[:2000]}\n```",
            severity=severity,
            file_path=file_path,
            test_case_id=test_case_id,
            error_snippet=combined[:500],
        )
        saved = self.save(defect)
        return saved.to_dict()


# 模块级单例
defect_repository = DefectRepositoryImpl()

__all__ = ["DefectRepositoryImpl", "defect_repository", "VALID_SEVERITIES"]
