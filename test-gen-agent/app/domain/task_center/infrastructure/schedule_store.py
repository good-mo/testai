"""任务中心定时计划存储。"""
from __future__ import annotations
import time
import uuid
from app.core.database import Database


class ScheduleStore:
    db_name = "tga.db"

    def __init__(self):
        conn = Database.get_conn(self.db_name)
        conn.execute("""CREATE TABLE IF NOT EXISTS domain_task_schedules (
            id TEXT PRIMARY KEY, cron TEXT NOT NULL DEFAULT '', enable INTEGER NOT NULL DEFAULT 1,
            run_mode TEXT NOT NULL DEFAULT 'SERIAL', project_id TEXT NOT NULL DEFAULT '', updated_at REAL NOT NULL)""")
        conn.commit()

    def get_schedule(self, item_id):
        row = Database.get_conn(self.db_name).execute("SELECT * FROM domain_task_schedules WHERE id=?", (item_id,)).fetchone()
        return dict(row) if row else None

    def save_schedule(self, item_id, cron="", enable=True, run_mode="SERIAL", project_id=""):
        conn = Database.get_conn(self.db_name); conn.execute("INSERT INTO domain_task_schedules VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET cron=excluded.cron, enable=excluded.enable, run_mode=excluded.run_mode, project_id=excluded.project_id, updated_at=excluded.updated_at", (item_id or uuid.uuid4().hex[:12], cron, int(enable), run_mode, project_id, time.time())); conn.commit(); return True

    def delete_schedule(self, item_id):
        conn = Database.get_conn(self.db_name); cur = conn.execute("DELETE FROM domain_task_schedules WHERE id=?", (item_id,)); conn.commit(); return cur.rowcount > 0


schedule_store = ScheduleStore()
TestPlanRepo = schedule_store
