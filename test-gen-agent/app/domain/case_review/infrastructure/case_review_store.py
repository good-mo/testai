"""用例评审上下文 SQLite 存储。"""

from __future__ import annotations

import json
import time
import uuid

from app.core.database import Database


class CaseReviewStore:
    db_name = "tga.db"

    def __init__(self) -> None:
        conn = Database.get_conn(self.db_name)
        conn.execute("""CREATE TABLE IF NOT EXISTS case_review_headers (
            id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '', num INTEGER NOT NULL DEFAULT 1,
            module_id TEXT NOT NULL DEFAULT 'root', project_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'UNDERWAY', review_pass_rule TEXT NOT NULL DEFAULT 'SINGLE',
            pos INTEGER NOT NULL DEFAULT 0, start_time REAL DEFAULT 0, end_time REAL DEFAULT 0,
            tags TEXT NOT NULL DEFAULT '[]', description TEXT NOT NULL DEFAULT '',
            create_time REAL NOT NULL, create_user TEXT NOT NULL DEFAULT 'admin',
            update_time REAL NOT NULL, update_user TEXT NOT NULL DEFAULT 'admin',
            deleted INTEGER NOT NULL DEFAULT 0, reviewers_json TEXT NOT NULL DEFAULT '[]')""")
        conn.execute("""CREATE TABLE IF NOT EXISTS case_review_links (
            review_id TEXT NOT NULL, case_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'UNDER_REVIEWED',
            reviewer TEXT NOT NULL DEFAULT '', comment TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(review_id, case_id))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS case_review_followers (
            review_id TEXT NOT NULL, user_id TEXT NOT NULL, PRIMARY KEY(review_id, user_id))""")
        conn.commit()

    @staticmethod
    def _decode(row):
        if not row:
            return None
        data = dict(row)
        for field in ("tags", "reviewers_json"):
            try:
                data[field] = json.loads(data.get(field) or "[]")
            except (TypeError, json.JSONDecodeError):
                data[field] = []
        data["deleted"] = bool(data.get("deleted"))
        return data

    def get_review(self, review_id):
        row = Database.get_conn(self.db_name).execute(
            "SELECT * FROM case_review_headers WHERE id = ? AND deleted = 0", (review_id,)
        ).fetchone()
        return self._decode(row)

    def list_links(self, review_id):
        rows = Database.get_conn(self.db_name).execute(
            "SELECT * FROM case_review_links WHERE review_id = ?", (review_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def list_link_case_ids(self, review_id):
        return [row["case_id"] for row in self.list_links(review_id)]

    def create_review(self, **data):
        review_id = data.get("id") or str(uuid.uuid4())
        now = time.time()
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO case_review_headers "
            "(id, name, project_id, module_id, status, description, create_time, update_time) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (review_id, data.get("name", ""), data.get("project_id", ""),
             data.get("module_id", "root"), data.get("status", "UNDERWAY"),
             data.get("description", ""), now, now),
        )
        conn.commit()
        return self.get_review(review_id)

    def update_review(self, review_id, fields):
        fields = {k: v for k, v in fields.items() if v is not None}
        if not fields:
            return self.get_review(review_id)
        fields["update_time"] = time.time()
        assignments = ", ".join(f"{key} = :{key}" for key in fields)
        fields["id"] = review_id
        conn = Database.get_conn(self.db_name)
        conn.execute(f"UPDATE case_review_headers SET {assignments} WHERE id = :id", fields)
        conn.commit()
        return self.get_review(review_id)

    def delete_review(self, review_id, soft=True):
        conn = Database.get_conn(self.db_name)
        if soft:
            cur = conn.execute("UPDATE case_review_headers SET deleted = 1 WHERE id = ?", (review_id,))
        else:
            cur = conn.execute("DELETE FROM case_review_headers WHERE id = ?", (review_id,))
        conn.commit()
        return cur.rowcount > 0

    def copy_review(self, source_id, new_name=""):
        source = self.get_review(source_id)
        if not source:
            return None
        copy = dict(source)
        copy.update(id=str(uuid.uuid4()), name=new_name or f"{source['name']}-副本")
        return self.create_review(**copy)

    def link_cases(self, review_id, case_ids):
        conn = Database.get_conn(self.db_name)
        for case_id in case_ids:
            conn.execute("INSERT OR IGNORE INTO case_review_links(review_id, case_id) VALUES (?, ?)", (review_id, str(case_id)))
        conn.commit()
        return self.list_links(review_id)

    def unlink_cases(self, review_id, case_ids):
        conn = Database.get_conn(self.db_name)
        for case_id in case_ids:
            conn.execute("DELETE FROM case_review_links WHERE review_id = ? AND case_id = ?", (review_id, str(case_id)))
        conn.commit()
        return True

    def update_link_status(self, review_id, case_ids, status, reviewer="", comment=""):
        conn = Database.get_conn(self.db_name)
        for case_id in case_ids:
            conn.execute("UPDATE case_review_links SET status = ?, reviewer = ?, comment = ? WHERE review_id = ? AND case_id = ?", (status, reviewer, comment, review_id, str(case_id)))
        conn.commit()
        return self.list_links(review_id)

    def list_reviews(self, keyword="", project_id="", status="", limit=100, offset=0):
        clauses, params = ["deleted = 0"], []
        if keyword:
            clauses.append("name LIKE ?"); params.append(f"%{keyword}%")
        if project_id:
            clauses.append("project_id = ?"); params.append(project_id)
        if status:
            clauses.append("status = ?"); params.append(status)
        params.extend([max(1, limit), max(0, offset)])
        rows = Database.get_conn(self.db_name).execute(f"SELECT * FROM case_review_headers WHERE {' AND '.join(clauses)} ORDER BY update_time DESC LIMIT ? OFFSET ?", params).fetchall()
        return [self._decode(row) for row in rows]

    def count_reviews(self, keyword="", project_id="", status=""):
        return len(self.list_reviews(keyword, project_id, status, limit=100000))

    def get_review_case_status(self, review_id):
        rows = self.list_links(review_id)
        counts = {"passCount": 0, "unPassCount": 0, "reReviewedCount": 0, "underReviewedCount": 0, "unReviewCount": 0, "reviewedCount": 0}
        for row in rows:
            status = row.get("status", "UNDER_REVIEWED")
            key = {"PASS": "passCount", "UN_PASS": "unPassCount", "RE_REVIEWED": "reReviewedCount", "UNDER_REVIEWED": "underReviewedCount"}.get(status, "unReviewCount")
            counts[key] += 1
            if key != "underReviewedCount": counts["reviewedCount"] += 1
        return counts

    def is_following(self, review_id, user_id):
        return Database.get_conn(self.db_name).execute("SELECT 1 FROM case_review_followers WHERE review_id = ? AND user_id = ?", (review_id, user_id)).fetchone() is not None

    def toggle_follow(self, review_id, user_id):
        conn = Database.get_conn(self.db_name)
        if self.is_following(review_id, user_id):
            conn.execute("DELETE FROM case_review_followers WHERE review_id = ? AND user_id = ?", (review_id, user_id)); result = False
        else:
            conn.execute("INSERT OR IGNORE INTO case_review_followers VALUES (?, ?)", (review_id, user_id)); result = True
        conn.commit()
        return result

    def count_reviews_by_module(self, project_id=""):
        rows = self.list_reviews(project_id=project_id, limit=100000)
        result = {}
        for row in rows: result[row.get("module_id", "root")] = result.get(row.get("module_id", "root"), 0) + 1
        return result


case_review_store = CaseReviewStore()
CaseReviewRepo = case_review_store
