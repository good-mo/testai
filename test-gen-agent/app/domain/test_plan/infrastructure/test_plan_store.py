"""测试计划上下文 SQLite 存储。

为 test_plan_app_service 中"薄委托"方法提供本地存储实现，替代对
app.repositories.test_plan_repo 的旧依赖。聚合级操作仍由
test_plan_repository_impl 中的仓储适配器负责；本文件覆盖模块树、
布局、定时、关联用例等旁路查询/统计类方法。
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Optional

from app.core.database import Database


class TestPlanStore:
    db_name = "tga.db"

    def __init__(self) -> None:
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_test_plans ("
            "id TEXT PRIMARY KEY, name TEXT, description TEXT, priority TEXT, "
            "module_id TEXT, project_id TEXT, created_by TEXT, status TEXT DEFAULT 'draft', "
            "tags TEXT DEFAULT '[]', start_time REAL, end_time REAL, pass_threshold REAL DEFAULT 0, "
            "test_planning INTEGER DEFAULT 1, auto_update_status INTEGER DEFAULT 0, "
            "repeat_case INTEGER DEFAULT 0, type TEXT DEFAULT 'FUNCTIONAL', group_id TEXT DEFAULT '', "
            "created_at REAL, updated_at REAL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_test_plan_modules ("
            "id TEXT PRIMARY KEY, name TEXT NOT NULL, parent_id TEXT DEFAULT 'root', "
            "project_id TEXT DEFAULT '', created_at REAL NOT NULL, updated_at REAL NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_test_plan_schedules ("
            "id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, cron TEXT DEFAULT '', "
            "enable INTEGER DEFAULT 1, run_mode TEXT DEFAULT 'SERIAL', "
            "project_id TEXT DEFAULT '', created_at REAL NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_test_plan_cases ("
            "id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, case_id TEXT NOT NULL, "
            "case_type TEXT DEFAULT 'functional', status TEXT DEFAULT 'pending', "
            "execute_time REAL DEFAULT 0, created_at REAL NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_dashboard_layouts ("
            "id TEXT PRIMARY KEY, org_id TEXT NOT NULL, user_id TEXT NOT NULL, "
            "layout TEXT DEFAULT '[]', created_at REAL NOT NULL, updated_at REAL NOT NULL)"
        )
        conn.commit()

    # ── 计划主体 ──────────────────────────────────────
    def get_plan(self, plan_id):
        r = Database.get_conn(self.db_name).execute("SELECT * FROM domain_test_plans WHERE id=?", (plan_id,)).fetchone()
        return self._d(r) if r else None

    def _d(self, r):
        if not r:
            return None
        x = dict(r)
        try:
            x["tags"] = json.loads(x.get("tags") or "[]")
        except Exception:
            x["tags"] = []
        return x

    def list_plans(self, keyword="", status="", project_id="", module_ids=None, limit=100, offset=0, type="", group_id=""):
        q = "SELECT * FROM domain_test_plans WHERE 1=1"
        p = []
        if keyword:
            q += " AND name LIKE ?"
            p.append(f"%{keyword}%")
        if status:
            q += " AND status=?"
            p.append(status)
        if project_id:
            q += " AND project_id=?"
            p.append(project_id)
        p += [max(1, limit), max(0, offset)]
        return [self._d(r) for r in Database.get_conn(self.db_name).execute(q + " ORDER BY updated_at DESC LIMIT ? OFFSET ?", p).fetchall()]

    def count_plans(self, **kw):
        return len(self.list_plans(**{k: v for k, v in kw.items() if k in ("keyword", "status", "project_id", "module_ids", "limit", "offset", "type", "group_id")}, limit=100000))

    def update_plan(self, plan_id, **d):
        old = self.get_plan(plan_id)
        if not old:
            return None
        x = {**old, **d}
        c = Database.get_conn(self.db_name)
        c.execute(
            "UPDATE domain_test_plans SET name=?,description=?,priority=?,module_id=?,status=?,tags=?,pass_threshold=?,updated_at=? WHERE id=?",
            (x.get("name", ""), x.get("description", ""), x.get("priority", ""), x.get("module_id", ""), x.get("status", "draft"), json.dumps(x.get("tags", [])), x.get("pass_threshold", 0), time.time(), plan_id),
        )
        c.commit()
        return self.get_plan(plan_id)

    def delete_plan(self, plan_id):
        c = Database.get_conn(self.db_name)
        cur = c.execute("DELETE FROM domain_test_plans WHERE id=?", (plan_id,))
        c.commit()
        return cur.rowcount > 0

    def archive_plan(self, plan_id):
        return bool(self.update_plan(plan_id, status="archived"))

    def get_plan_statistics(self, plan_id):
        return {"plan_id": plan_id, "total": 0}

    def get_plans_statistics(self, ids):
        return {i: self.get_plan_statistics(i) for i in ids}

    # ── 模块树 ────────────────────────────────────────
    def list_modules(self):
        rows = Database.get_conn(self.db_name).execute("SELECT * FROM domain_test_plan_modules ORDER BY created_at ASC").fetchall()
        return [dict(r) for r in rows]

    def create_module(self, name, parent_id="root", project_id=""):
        item_id = uuid.uuid4().hex[:12]
        now = time.time()
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO domain_test_plan_modules VALUES (?, ?, ?, ?, ?, ?)",
            (item_id, name, parent_id, project_id, now, now),
        )
        conn.commit()
        return {"id": item_id, "name": name, "parent_id": parent_id, "project_id": project_id}

    def update_module(self, module_id, name="", **kwargs):
        if name:
            Database.get_conn(self.db_name).execute("UPDATE domain_test_plan_modules SET name=?, updated_at=? WHERE id=?", (name, time.time(), module_id))
            Database.get_conn(self.db_name).commit()
        return True

    def delete_module(self, module_id):
        Database.get_conn(self.db_name).execute("DELETE FROM domain_test_plan_modules WHERE id=?", (module_id,))
        Database.get_conn(self.db_name).commit()
        return True

    def move_module(self, drag_node_id, drop_node_id, drop_position=0):
        # 占位：模块树移动逻辑
        return True

    def count_plans_by_module(self, project_id=""):
        q = "SELECT COUNT(*) AS n FROM domain_test_plans WHERE module_id IS NOT NULL AND module_id != ''"
        p = []
        if project_id:
            q += " AND project_id=?"
            p.append(project_id)
        r = Database.get_conn(self.db_name).execute(q, p).fetchone()
        return {"total": int(r["n"]) if r else 0}

    # ── 布局 ──────────────────────────────────────────
    def save_dashboard_layout(self, org_id, user_id, layout):
        item_id = f"{org_id}_{user_id}"
        now = time.time()
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT OR REPLACE INTO domain_dashboard_layouts VALUES (?, ?, ?, ?, ?)",
            (item_id, org_id, user_id, json.dumps(layout), now, now),
        )
        conn.commit()
        return True

    def load_dashboard_layout(self, org_id, user_id):
        r = Database.get_conn(self.db_name).execute("SELECT layout FROM domain_dashboard_layouts WHERE org_id=? AND user_id=?", (org_id, user_id)).fetchone()
        return json.loads(r["layout"]) if r else []

    # ── 定时 ──────────────────────────────────────────
    def save_schedule(self, plan_id, cron="", enable=True, run_mode="SERIAL", project_id=""):
        item_id = uuid.uuid4().hex[:12]
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO domain_test_plan_schedules VALUES (?, ?, ?, ?, ?, ?, ?)",
            (item_id, plan_id, cron, int(enable), run_mode, project_id, time.time()),
        )
        conn.commit()
        return {"id": item_id, "plan_id": plan_id}

    def get_schedule(self, plan_id):
        r = Database.get_conn(self.db_name).execute("SELECT * FROM domain_test_plan_schedules WHERE plan_id=?", (plan_id,)).fetchone()
        return dict(r) if r else None

    def get_schedules(self, plan_ids):
        if not plan_ids:
            return {}
        placeholders = ",".join("?" for _ in plan_ids)
        rows = Database.get_conn(self.db_name).execute(f"SELECT * FROM domain_test_plan_schedules WHERE plan_id IN ({placeholders})", plan_ids).fetchall()
        result = {}
        for r in rows:
            result.setdefault(r["plan_id"], []).append(dict(r))
        return result

    def delete_schedule(self, plan_id):
        Database.get_conn(self.db_name).execute("DELETE FROM domain_test_plan_schedules WHERE plan_id=?", (plan_id,))
        Database.get_conn(self.db_name).commit()
        return True

    # ── 关联用例 ──────────────────────────────────────
    def add_plan_case(self, plan_id, case_id, case_type="functional"):
        item_id = uuid.uuid4().hex[:12]
        conn = Database.get_conn(self.db_name)
        conn.execute(
            "INSERT INTO domain_test_plan_cases VALUES (?, ?, ?, ?, ?, ?, ?)",
            (item_id, plan_id, case_id, case_type, "pending", 0, time.time()),
        )
        conn.commit()
        return {"rel_id": item_id, "plan_id": plan_id, "case_id": case_id}

    def remove_plan_case(self, rel_id):
        Database.get_conn(self.db_name).execute("DELETE FROM domain_test_plan_cases WHERE id=?", (rel_id,))
        Database.get_conn(self.db_name).commit()
        return True

    def list_plan_cases(self, plan_id):
        rows = Database.get_conn(self.db_name).execute("SELECT * FROM domain_test_plan_cases WHERE plan_id=? ORDER BY execute_time ASC", (plan_id,)).fetchall()
        return [dict(r) for r in rows]

    def update_plan_case_status(self, rel_id, status):
        Database.get_conn(self.db_name).execute("UPDATE domain_test_plan_cases SET status=? WHERE id=?", (status, rel_id))
        Database.get_conn(self.db_name).commit()
        return True

    def update_rel_pos(self, rel_id, pos):
        Database.get_conn(self.db_name).execute("UPDATE domain_test_plan_cases SET execute_time=? WHERE id=?", (pos, rel_id))
        Database.get_conn(self.db_name).commit()
        return True


DB_NAME = "tga.db"
TestPlanRepo = TestPlanStore()
__all__ = ["TestPlanStore", "TestPlanRepo", "DB_NAME"]
