"""后台任务队列的 SQLite 存储。"""
from __future__ import annotations
import json
import time
from app.core.database import Database


class TaskQueueStore:
    db_name = "tga.db"

    def ensure_table(self):
        Database.get_conn(self.db_name).execute("""CREATE TABLE IF NOT EXISTS domain_tasks (
            id TEXT PRIMARY KEY, status TEXT NOT NULL, coro_name TEXT NOT NULL DEFAULT '',
            args TEXT NOT NULL DEFAULT '[]', handler_name TEXT NOT NULL DEFAULT '',
            handler_args TEXT NOT NULL DEFAULT '[]', handler_kwargs TEXT NOT NULL DEFAULT '{}',
            restartable INTEGER NOT NULL DEFAULT 0, worker_id TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL, updated_at REAL NOT NULL)""")
        Database.get_conn(self.db_name).commit()

    @staticmethod
    def _decode(row):
        if not row: return None
        data = dict(row)
        for key in ("args", "handler_args", "handler_kwargs"):
            try: data[key] = json.loads(data[key] or ("{}" if key == "handler_kwargs" else "[]"))
            except (TypeError, json.JSONDecodeError): data[key] = {} if key == "handler_kwargs" else []
        return data

    def save_task(self, task_id, **data):
        now = time.time(); conn = Database.get_conn(self.db_name)
        conn.execute("INSERT INTO domain_tasks (id,status,coro_name,args,handler_name,handler_args,handler_kwargs,restartable,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at", (task_id, data.get("status", "PENDING"), data.get("coro_name", ""), json.dumps(data.get("args", [])), data.get("handler_name", ""), json.dumps(data.get("handler_args", [])), json.dumps(data.get("handler_kwargs", {})), int(data.get("restartable", False)), now, now)); conn.commit()

    def update_status(self, task_id, status, **kwargs):
        allowed = {"status": status, "updated_at": time.time()}; allowed.update({k: kwargs[k] for k in ("error", "worker_id") if k in kwargs}); assignments = ",".join(f"{k}=:{k}" for k in allowed); allowed["id"] = task_id; conn = Database.get_conn(self.db_name); conn.execute(f"UPDATE domain_tasks SET {assignments} WHERE id=:id", allowed); conn.commit()
    def get_task(self, task_id): return self._decode(Database.get_conn(self.db_name).execute("SELECT * FROM domain_tasks WHERE id=?", (task_id,)).fetchone())
    def list_recent(self, limit=50): return [self._decode(row) for row in Database.get_conn(self.db_name).execute("SELECT * FROM domain_tasks ORDER BY updated_at DESC LIMIT ?", (max(1, limit),)).fetchall()]
    def list_pending(self): return [self._decode(row) for row in Database.get_conn(self.db_name).execute("SELECT * FROM domain_tasks WHERE status='PENDING' ORDER BY created_at").fetchall()]
    def delete_task(self, task_id):
        conn = Database.get_conn(self.db_name); cur = conn.execute("DELETE FROM domain_tasks WHERE id=?", (task_id,)); conn.commit(); return cur.rowcount > 0
    def claim_next_pending(self, worker_id=""):
        row = Database.get_conn(self.db_name).execute("SELECT id FROM domain_tasks WHERE status='PENDING' ORDER BY created_at LIMIT 1").fetchone()
        if not row: return None
        self.update_status(row["id"], "RUNNING", worker_id=worker_id); return self.get_task(row["id"])
    def release_claim(self, task_id): self.update_status(task_id, "PENDING", worker_id="")
    def recover_after_restart(self): return (self.list_pending(), [])
    def recover_pending(self): return self.list_pending()
    def mark_abandoned(self, reason="进程重启，任务未完成"): return []

    def _get_conn(self): return Database.get_conn(self.db_name)
    def _decode_row(self, row): return self._decode(row)


task_repo = TaskQueueStore()
