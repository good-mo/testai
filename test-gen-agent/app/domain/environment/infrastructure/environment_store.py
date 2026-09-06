"""环境上下文 SQLite 存储。"""
from __future__ import annotations
import json
import time
import uuid
from app.core.database import Database


class EnvironmentStore:
    db_name = "tga.db"
    fields = ("name", "description", "env_type", "status", "endpoint", "docker_compose_path", "container_name", "image", "health_check_url", "owner", "tags", "error_message")

    def __init__(self):
        conn = Database.get_conn(self.db_name)
        conn.execute("""CREATE TABLE IF NOT EXISTS domain_environments (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            env_type TEXT NOT NULL DEFAULT 'docker', status TEXT NOT NULL DEFAULT 'offline',
            endpoint TEXT NOT NULL DEFAULT '', docker_compose_path TEXT NOT NULL DEFAULT '',
            container_name TEXT NOT NULL DEFAULT '', image TEXT NOT NULL DEFAULT '',
            health_check_url TEXT NOT NULL DEFAULT '', owner TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '[]', error_message TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL, updated_at REAL NOT NULL, deleted INTEGER NOT NULL DEFAULT 0)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS domain_environment_alerts (
            id TEXT PRIMARY KEY, env_id TEXT NOT NULL, env_name TEXT NOT NULL DEFAULT '',
            level TEXT NOT NULL, message TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '',
            resolved INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL)""")
        conn.commit()

    @staticmethod
    def _decode(row):
        if not row: return None
        data = dict(row)
        try: data["tags"] = json.loads(data.get("tags") or "[]")
        except (TypeError, json.JSONDecodeError): data["tags"] = []
        return data

    def create(self, data):
        item_id = data.get("id") or uuid.uuid4().hex[:12]; now = time.time(); conn = Database.get_conn(self.db_name)
        values = [item_id] + [json.dumps(data.get(f, []), ensure_ascii=False) if f == "tags" else data.get(f, "") for f in self.fields] + [now, now, 0]
        conn.execute(f"INSERT INTO domain_environments (id, {','.join(self.fields)}, created_at, updated_at, deleted) VALUES ({','.join('?' for _ in values)})", values); conn.commit()
        return self.get(item_id)

    def get(self, item_id, include_deleted=False):
        sql = "SELECT * FROM domain_environments WHERE id = ?" + ("" if include_deleted else " AND deleted = 0")
        return self._decode(Database.get_conn(self.db_name).execute(sql, (item_id,)).fetchone())

    def list(self, search="", status="", env_type=""):
        clauses, params = ["deleted = 0"], []
        if search: clauses.append("name LIKE ?"); params.append(f"%{search}%")
        if status: clauses.append("status = ?"); params.append(status)
        if env_type: clauses.append("env_type = ?"); params.append(env_type)
        rows = Database.get_conn(self.db_name).execute(f"SELECT * FROM domain_environments WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC", params).fetchall()
        return [self._decode(row) for row in rows]

    def update(self, item_id, data):
        fields = {k: data[k] for k in self.fields if k in data}; fields["updated_at"] = time.time()
        if not fields: return self.get(item_id)
        if "tags" in fields: fields["tags"] = json.dumps(fields["tags"], ensure_ascii=False)
        assignments = ",".join(f"{k}=:{k}" for k in fields); fields["id"] = item_id
        conn = Database.get_conn(self.db_name); conn.execute(f"UPDATE domain_environments SET {assignments} WHERE id=:id", fields); conn.commit(); return self.get(item_id)

    def delete(self, item_id, permanent=False):
        conn = Database.get_conn(self.db_name); cur = conn.execute(f"{'DELETE' if permanent else 'UPDATE'} FROM domain_environments {'WHERE id=?' if permanent else 'SET deleted=1 WHERE id=?'}", (item_id,)); conn.commit(); return cur.rowcount > 0
    def list_trash(self):
        rows = Database.get_conn(self.db_name).execute("SELECT * FROM domain_environments WHERE deleted=1 ORDER BY updated_at DESC").fetchall(); return [self._decode(row) for row in rows]
    def restore(self, item_id):
        conn = Database.get_conn(self.db_name); cur = conn.execute("UPDATE domain_environments SET deleted=0 WHERE id=?", (item_id,)); conn.commit(); return cur.rowcount > 0
    def trash(self, item_id): return self.delete(item_id)
    def purge(self, item_id): return self.delete(item_id, permanent=True)

    def create_alert(self, env_id, env_name, level, message, detail=""):
        item = {"id": uuid.uuid4().hex[:12], "env_id": env_id, "env_name": env_name, "level": level, "message": message, "detail": detail, "resolved": 0, "created_at": time.time()}
        conn = Database.get_conn(self.db_name); conn.execute("INSERT INTO domain_environment_alerts VALUES (:id,:env_id,:env_name,:level,:message,:detail,:resolved,:created_at)", item); conn.commit(); return item
    def list_alerts(self, limit=50, level=""):
        sql = "SELECT * FROM domain_environment_alerts WHERE resolved=0"; params=[]
        if level: sql += " AND level=?"; params.append(level)
        rows = Database.get_conn(self.db_name).execute(sql + " ORDER BY created_at DESC LIMIT ?", [*params, max(1, limit)]).fetchall(); return [dict(row) for row in rows]
    def resolve_alert(self, alert_id):
        conn = Database.get_conn(self.db_name); cur = conn.execute("UPDATE domain_environment_alerts SET resolved=1 WHERE id=?", (alert_id,)); conn.commit(); return cur.rowcount > 0
    def get_alerts_stats(self):
        rows = Database.get_conn(self.db_name).execute("SELECT level, COUNT(*) AS count FROM domain_environment_alerts WHERE resolved=0 GROUP BY level").fetchall(); return {row["level"]: row["count"] for row in rows}


environment_store = EnvironmentStore()
EnvironmentRepo = environment_store
