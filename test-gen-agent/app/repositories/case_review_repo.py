# app/repositories/case_review_repo.py
"""用例评审（case_review）域数据访问层（Phase E · 4 层下沉）。

从 app/cases/review_store.py 下沉：原模块直接持有 SQL（建表 + CRUD），
现收敛到本仓库——Router → Service → Repository → DB。review_store 退化为
兼容门面，其全部公开函数统一委托本仓库，对外行为与旧层完全一致。

承载 testcases.db 三张评审表：
  - case_review_headers      评审头（评审会话主记录）
  - case_review_case_links   评审与用例的关联 + 评审结果
  - case_review_follows      用户关注评审
"""
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.repositories.base import BaseRepo

# ── 评审状态（前端 ReviewStatus）─────────────────────
STATUS_PREPARED = "PREPARED"
STATUS_UNDERWAY = "UNDERWAY"
STATUS_COMPLETED = "COMPLETED"

# ── 用例评审结果（前端 ReviewResult）─────────────────
RESULT_UN_REVIEWED = "UN_REVIEWED"
RESULT_UNDER_REVIEWED = "UNDER_REVIEWED"
RESULT_PASS = "PASS"
RESULT_UN_PASS = "UN_PASS"
RESULT_RE_REVIEWED = "RE_REVIEWED"

# 允许按模块列更新的评审头字段
_REVIEW_UPDATE_FIELDS = {
    "name", "description", "module_id", "project_id", "status",
    "review_pass_rule", "start_time", "end_time",
}


class CaseReviewRepo(BaseRepo):
    """用例评审仓库：case_review_headers / case_links / follows 数据访问。"""

    db_name = "testcases.db"

    # ── 建表 ───────────────────────────────────────────
    @classmethod
    def init_table(cls) -> None:
        """幂等建表。"""
        conn = Database.get_conn(cls.db_name)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS case_review_headers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                num INTEGER DEFAULT 1,
                module_id TEXT DEFAULT 'root',
                project_id TEXT DEFAULT '',
                status TEXT DEFAULT 'UNDERWAY',
                review_pass_rule TEXT DEFAULT 'SINGLE',
                pos INTEGER DEFAULT 0,
                start_time REAL DEFAULT 0,
                end_time REAL DEFAULT 0,
                tags TEXT DEFAULT '[]',
                description TEXT DEFAULT '',
                create_time REAL,
                create_user TEXT DEFAULT 'admin',
                update_time REAL,
                update_user TEXT DEFAULT 'admin',
                deleted INTEGER DEFAULT 0,
                reviewers_json TEXT DEFAULT '[]'  -- 评审人 JSON 数组
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_review_headers_deleted
            ON case_review_headers(deleted)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS case_review_case_links (
                id TEXT PRIMARY KEY,
                review_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                status TEXT DEFAULT 'UN_REVIEWED',
                reviewer TEXT DEFAULT '',
                comment TEXT DEFAULT '',
                create_time REAL,
                update_time REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_review_links_review
            ON case_review_case_links(review_id)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS case_review_follows (
                review_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                create_time REAL,
                PRIMARY KEY (review_id, user_id)
            )
        """)
        # 关注去重约束：幂等补齐唯一索引，防止早期表缺少主键时并发产生重复关注
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_case_review_follows
            ON case_review_follows(review_id, user_id)
        """)
        conn.commit()

    # ── 行转换 ────────────────────────────────────────
    @staticmethod
    def header_to_dict(row) -> Dict[str, Any]:
        """评审头数据行 -> dict（解析 tags / reviewers_json JSON 列）。"""
        d = dict(row)
        try:
            d["tags"] = json.loads(d.get("tags") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
        try:
            d["reviewers_json"] = json.loads(d.get("reviewers_json") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["reviewers_json"] = []
        return d

    @classmethod
    def _ensure_reviewers_col(cls) -> None:
        conn = Database.get_conn(cls.db_name)
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(case_review_headers)").fetchall()]
            if "reviewers_json" not in cols:
                conn.execute("ALTER TABLE case_review_headers ADD COLUMN reviewers_json TEXT DEFAULT '[]'")
        except Exception:
            pass

    @classmethod
    def _save_reviewers(cls, review_id: str, reviewers: list) -> None:
        """将评审人数组（字符串 userId 或 dict）写入 reviewers_json 列。"""
        cls._ensure_reviewers_col()
        conn = Database.get_conn(cls.db_name)
        norm = []
        for r in reviewers:
            if isinstance(r, dict):
                norm.append({"userId": r.get("userId", r.get("id", "")),
                             "userName": r.get("userName", r.get("name", r.get("userId", "")))})
            else:
                norm.append({"userId": str(r), "userName": str(r)})
        conn.execute(
            "UPDATE case_review_headers SET reviewers_json=? WHERE id=?",
            (json.dumps(norm, ensure_ascii=False), review_id),
        )
        conn.commit()

    # ── 评审头 CRUD ───────────────────────────────────
    @classmethod
    def create_review(cls, name: str, description: str = "", project_id: str = "",
                      module_id: str = "root", status: str = STATUS_UNDERWAY,
                      review_pass_rule: str = "SINGLE", reviewers: list = None,
                      create_user: str = "admin", tags: list = None,
                      start_time: float = 0, end_time: float = 0) -> Dict[str, Any]:
        """创建评审头并写入默认评审人。"""
        rid = str(uuid.uuid4())
        now = time.time()
        conn = Database.get_conn(cls.db_name)
        conn.execute("""
            INSERT INTO case_review_headers
                (id, name, num, module_id, project_id, status, review_pass_rule, pos,
                 start_time, end_time, tags, description, create_time, create_user,
                 update_time, update_user, deleted)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
        """, (rid, name, 1, module_id, project_id, status, review_pass_rule, 0,
              start_time, end_time, json.dumps(tags or [], ensure_ascii=False),
              description, now, create_user, now, create_user))
        cls._save_reviewers(rid, reviewers or [])
        conn.commit()
        return cls.get_review(rid) or {}

    @classmethod
    def get_review(cls, review_id: str) -> Optional[Dict[str, Any]]:
        conn = Database.get_conn(cls.db_name)
        row = conn.execute(
            "SELECT * FROM case_review_headers WHERE id=? AND deleted=0",
            (review_id,),
        ).fetchone()
        if not row:
            return None
        return cls.header_to_dict(row)

    @classmethod
    def list_reviews(cls, keyword: str = "", project_id: str = "",
                     status: str = "", limit: int = 500,
                     offset: int = 0) -> List[Dict[str, Any]]:
        """分页列出未删除评审（返回全量 + 元信息由路由组装）。"""
        conn = Database.get_conn(cls.db_name)
        sql = "SELECT * FROM case_review_headers WHERE deleted=0"
        params: list = []
        if keyword:
            sql += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if project_id:
            sql += " AND project_id=?"
            params.append(project_id)
        if status:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY update_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(sql, params).fetchall()
        return [cls.header_to_dict(r) for r in rows]

    @classmethod
    def count_reviews(cls, keyword: str = "", project_id: str = "",
                      status: str = "") -> int:
        conn = Database.get_conn(cls.db_name)
        sql = "SELECT COUNT(*) FROM case_review_headers WHERE deleted=0"
        params: list = []
        if keyword:
            sql += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if project_id:
            sql += " AND project_id=?"
            params.append(project_id)
        if status:
            sql += " AND status=?"
            params.append(status)
        return conn.execute(sql, params).fetchone()[0]

    @classmethod
    def update_review(cls, review_id: str,
                      fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新评审头（name/description/module_id/project_id/status/review_pass_rule）。"""
        sets = []
        params = []
        for k, v in fields.items():
            if k in _REVIEW_UPDATE_FIELDS and v is not None:
                sets.append(f"{k}=?")
                params.append(v)
        if not sets:
            return cls.get_review(review_id)
        sets.append("update_time=?")
        params.append(time.time())
        params.append(review_id)
        conn = Database.get_conn(cls.db_name)
        conn.execute(f"UPDATE case_review_headers SET {', '.join(sets)} WHERE id=?", params)
        if "reviewers" in fields:
            cls._save_reviewers(review_id, fields["reviewers"] or [])
        conn.commit()
        return cls.get_review(review_id)

    @classmethod
    def delete_review(cls, review_id: str, soft: bool = True) -> bool:
        """删除评审。硬删除时级联清理关联用例与关注，整体原子。"""
        with Database.transaction(cls.db_name) as conn:
            if soft:
                cur = conn.execute(
                    "UPDATE case_review_headers SET deleted=1, update_time=? WHERE id=?",
                    (time.time(), review_id),
                )
            else:
                cur = conn.execute("DELETE FROM case_review_headers WHERE id=?", (review_id,))
                conn.execute("DELETE FROM case_review_case_links WHERE review_id=?", (review_id,))
                conn.execute("DELETE FROM case_review_follows WHERE review_id=?", (review_id,))
            return cur.rowcount > 0

    @classmethod
    def copy_review(cls, source_id: str,
                    new_name: str = "") -> Optional[Dict[str, Any]]:
        """复制评审（含已关联用例与评审人），整体原子。"""
        src = cls.get_review(source_id)
        if not src:
            return None
        rid = str(uuid.uuid4())
        now = time.time()
        name = new_name or f"{src.get('name', '')} (副本)"
        links = cls.list_links(source_id)
        with Database.transaction(cls.db_name) as conn:
            conn.execute("""
                INSERT INTO case_review_headers
                    (id, name, num, module_id, project_id, status, review_pass_rule, pos,
                     start_time, end_time, tags, description, create_time, create_user,
                     update_time, update_user, deleted, reviewers_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)
            """, (rid, name, src.get("num", 1) + 1, src.get("module_id", "root"),
                  src.get("project_id", ""), STATUS_UNDERWAY, src.get("review_pass_rule", "SINGLE"),
                  src.get("pos", 0), src.get("start_time", 0) or 0, src.get("end_time", 0) or 0,
                  src.get("tags") and json.dumps(src["tags"], ensure_ascii=False) or "[]",
                  src.get("description", ""), now, "admin", now, "admin",
                  json.dumps(src.get("reviewers_json", []), ensure_ascii=False)))
            for link in links:
                conn.execute("""
                    INSERT INTO case_review_case_links
                        (id, review_id, case_id, status, reviewer, comment, create_time, update_time)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (str(uuid.uuid4()), rid, link["case_id"], RESULT_UN_REVIEWED,
                      "", "", now, now))
        return cls.get_review(rid)

    # ── 评审-用例关联 ─────────────────────────────────
    @classmethod
    def list_links(cls, review_id: str) -> List[Dict[str, Any]]:
        conn = Database.get_conn(cls.db_name)
        rows = conn.execute(
            "SELECT * FROM case_review_case_links WHERE review_id=? ORDER BY create_time",
            (review_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def link_cases(cls, review_id: str, case_ids: list) -> int:
        """批量关联用例到评审，已存在跳过，整体原子。"""
        now = time.time()
        added = 0
        with Database.transaction(cls.db_name) as conn:
            for cid in case_ids or []:
                if not cid:
                    continue
                exists = conn.execute(
                    "SELECT 1 FROM case_review_case_links WHERE review_id=? AND case_id=?",
                    (review_id, cid),
                ).fetchone()
                if exists:
                    continue
                conn.execute("""
                    INSERT INTO case_review_case_links
                        (id, review_id, case_id, status, reviewer, comment, create_time, update_time)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (str(uuid.uuid4()), review_id, cid, RESULT_UN_REVIEWED, "", "", now, now))
                added += 1
        return added

    @classmethod
    def unlink_cases(cls, review_id: str, case_ids: list) -> int:
        """批量解除评审与用例关联，整体原子。"""
        removed = 0
        with Database.transaction(cls.db_name) as conn:
            for cid in case_ids or []:
                cur = conn.execute(
                    "DELETE FROM case_review_case_links WHERE review_id=? AND case_id=?",
                    (review_id, cid),
                )
                removed += cur.rowcount
        return removed

    @classmethod
    def list_link_case_ids(cls, review_id: str) -> set:
        """返回评审下已关联（归属）该评审的用例 id 集合。"""
        conn = Database.get_conn(cls.db_name)
        rows = conn.execute(
            "SELECT case_id FROM case_review_case_links WHERE review_id=?",
            (review_id,),
        ).fetchall()
        return {r["case_id"] for r in rows}

    @classmethod
    def update_link_status(cls, review_id: str, case_ids: list, status: str,
                           reviewer: str = "", comment: str = "") -> int:
        """批量更新评审-用例结果（只更新确已关联的用例），整体原子。"""
        now = time.time()
        updated = 0
        with Database.transaction(cls.db_name) as conn:
            for cid in case_ids or []:
                cur = conn.execute("""
                    UPDATE case_review_case_links
                    SET status=?, reviewer=?, comment=?, update_time=?
                    WHERE review_id=? AND case_id=?
                """, (status, reviewer, comment, now, review_id, cid))
                updated += cur.rowcount
        return updated

    @classmethod
    def get_review_case_status(cls, review_id: str) -> Dict[str, int]:
        """评审下用例状态汇总计数。"""
        conn = Database.get_conn(cls.db_name)
        rows = conn.execute(
            "SELECT status, COUNT(*) c FROM case_review_case_links WHERE review_id=? GROUP BY status",
            (review_id,),
        ).fetchall()
        counts = {"passCount": 0, "unPassCount": 0, "unReviewCount": 0,
                  "underReviewedCount": 0, "reReviewedCount": 0, "reviewedCount": 0}
        for r in rows:
            status, c = r["status"], r["c"]
            if status == RESULT_PASS:
                counts["passCount"] += c
                counts["reviewedCount"] += c
            elif status == RESULT_UN_PASS:
                counts["unPassCount"] += c
                counts["reviewedCount"] += c
            elif status == RESULT_UNDER_REVIEWED:
                counts["underReviewedCount"] += c
                counts["reviewedCount"] += c
            elif status == RESULT_RE_REVIEWED:
                counts["reReviewedCount"] += c
                counts["reviewedCount"] += c
            else:
                counts["unReviewCount"] += c
        return counts

    # ── 关注 ───────────────────────────────────────────
    @classmethod
    def is_following(cls, review_id: str, user_id: str) -> bool:
        conn = Database.get_conn(cls.db_name)
        row = conn.execute(
            "SELECT 1 FROM case_review_follows WHERE review_id=? AND user_id=?",
            (review_id, user_id),
        ).fetchone()
        return bool(row)

    @classmethod
    def toggle_follow(cls, review_id: str, user_id: str) -> bool:
        """关注/取消关注评审（事务内原子，防止并发重复关注）。"""
        with Database.transaction(cls.db_name) as conn:
            if cls.is_following(review_id, user_id):
                conn.execute("DELETE FROM case_review_follows WHERE review_id=? AND user_id=?",
                             (review_id, user_id))
                return False
            conn.execute(
                "INSERT OR IGNORE INTO case_review_follows (review_id, user_id, create_time) VALUES (?,?,?)",
                (review_id, user_id, time.time()),
            )
            return True

    # ── 评审模块统计（case_review_headers.module_id 归属）────
    @classmethod
    def count_reviews_by_module(cls, project_id: str = "") -> Dict[str, int]:
        """统计每个评审模块下（直接归属）非删除评审数量。

        返回记录 key 为 module_id；额外含 root / all 两个汇总 key。
        """
        conn = Database.get_conn(cls.db_name)
        if project_id:
            rows = conn.execute(
                "SELECT module_id, COUNT(*) AS c FROM case_review_headers "
                "WHERE deleted = 0 AND (project_id = ? OR project_id = '') "
                "GROUP BY module_id",
                (project_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT module_id, COUNT(*) AS c FROM case_review_headers "
                "WHERE deleted = 0 GROUP BY module_id",
            ).fetchall()
        counts = {}
        total = 0
        for r in rows:
            mid = r["module_id"] or "root"
            counts[mid] = r["c"]
            total += r["c"]
        counts["all"] = total
        counts["root"] = counts.get("root", 0)
        return counts


# 便捷单例（与其它 repo 风格一致）
case_review_repo = CaseReviewRepo


# 确保表存在（导入即建表，与旧 review_store 模块 import 时调用 init_tables 对齐）
CaseReviewRepo.init_table()
