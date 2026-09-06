"""数据工厂上下文 SQLite 存储。"""
from __future__ import annotations

import json
import time
import uuid
from app.core.database import Database


class DatafactoryStore:
    db_name = "tga.db"

    def __init__(self):
        conn = Database.get_conn(self.db_name)
        conn.execute("""CREATE TABLE IF NOT EXISTS domain_data_templates (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT 'custom', schema_json TEXT NOT NULL DEFAULT '{}',
            deps_json TEXT NOT NULL DEFAULT '[]', tags_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'active', created_at REAL NOT NULL, updated_at REAL NOT NULL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS domain_data_batches (
            id TEXT PRIMARY KEY, template_id TEXT NOT NULL, template_name TEXT NOT NULL DEFAULT '',
            batch_size INTEGER NOT NULL DEFAULT 0, env_key TEXT NOT NULL DEFAULT '',
            data_json TEXT NOT NULL DEFAULT '[]', created_at REAL NOT NULL)""")
        conn.commit()

    @staticmethod
    def _template(row):
        if not row: return None
        data = dict(row)
        for key in ("schema_json", "deps_json", "tags_json"):
            target = key[:-5] if key.endswith("_json") else key
            try: data[target] = json.loads(data.pop(key) or ("{}" if target == "schema" else "[]"))
            except (TypeError, json.JSONDecodeError): data[target] = {} if target == "schema" else []
        data["created_at"] = data.pop("created_at", 0)
        data["updated_at"] = data.pop("updated_at", 0)
        return data

    def get_template(self, item_id):
        return self._template(Database.get_conn(self.db_name).execute("SELECT * FROM domain_data_templates WHERE id = ?", (item_id,)).fetchone())

    def create_template(self, **data):
        item_id = data.get("id") or uuid.uuid4().hex[:12]; now = time.time(); conn = Database.get_conn(self.db_name)
        conn.execute("INSERT INTO domain_data_templates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (item_id, data.get("name", ""), data.get("description", ""), data.get("category", "custom"), json.dumps(data.get("schema", {}), ensure_ascii=False), json.dumps(data.get("deps", []), ensure_ascii=False), json.dumps(data.get("tags", []), ensure_ascii=False), data.get("status", "active"), now, now))
        conn.commit(); return self.get_template(item_id)

    def update_template(self, item_id, **data):
        old = self.get_template(item_id)
        if not old: return None
        merged = {**old, **data}; conn = Database.get_conn(self.db_name)
        conn.execute("UPDATE domain_data_templates SET name=?, description=?, category=?, schema_json=?, deps_json=?, tags_json=?, status=?, updated_at=? WHERE id=?", (merged.get("name", ""), merged.get("description", ""), merged.get("category", "custom"), json.dumps(merged.get("schema", {}), ensure_ascii=False), json.dumps(merged.get("deps", []), ensure_ascii=False), json.dumps(merged.get("tags", []), ensure_ascii=False), merged.get("status", "active"), time.time(), item_id))
        conn.commit(); return self.get_template(item_id)

    def delete_template(self, item_id):
        conn = Database.get_conn(self.db_name); cur = conn.execute("DELETE FROM domain_data_templates WHERE id=?", (item_id,)); conn.commit(); return cur.rowcount > 0

    def list_templates(self, category=None, search=None, limit=100, offset=0):
        clauses, params = [], []
        if category: clauses.append("category=?"); params.append(category)
        if search: clauses.append("name LIKE ?"); params.append(f"%{search}%")
        params.extend([max(1, limit), max(0, offset)]); where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = Database.get_conn(self.db_name).execute(f"SELECT * FROM domain_data_templates{where} ORDER BY updated_at DESC LIMIT ? OFFSET ?", params).fetchall()
        return [self._template(row) for row in rows]

    def generate_data(self, template_id, batch_size, env_key=""):
        template = self.get_template(template_id)
        if not template: return None
        batch_id = uuid.uuid4().hex[:12]; data = [{} for _ in range(max(0, int(batch_size)))]; now = time.time()
        conn = Database.get_conn(self.db_name)
        conn.execute("INSERT INTO domain_data_batches VALUES (?, ?, ?, ?, ?, ?, ?)", (batch_id, template_id, template["name"], len(data), env_key, json.dumps(data), now)); conn.commit()
        return {"id": batch_id, "batch_id": batch_id, "template_id": template_id, "template_name": template["name"], "batch_size": len(data), "env_key": env_key, "data": data}

    def list_batches(self, limit=50):
        rows = Database.get_conn(self.db_name).execute("SELECT * FROM domain_data_batches ORDER BY created_at DESC LIMIT ?", (max(1, limit),)).fetchall()
        return [{**dict(row), "id": row["id"], "data": json.loads(row["data_json"] or "[]")} for row in rows]

    def cleanup_batch(self, item_id):
        conn = Database.get_conn(self.db_name); cur = conn.execute("DELETE FROM domain_data_batches WHERE id=?", (item_id,)); conn.commit(); return cur.rowcount > 0
    def cleanup_by_template(self, template_id, env_key="default"):
        conn = Database.get_conn(self.db_name); cur = conn.execute("DELETE FROM domain_data_batches WHERE template_id=? AND env_key=?", (template_id, env_key)); conn.commit(); return cur.rowcount
    def cleanup_by_env(self, env_key):
        conn = Database.get_conn(self.db_name); cur = conn.execute("DELETE FROM domain_data_batches WHERE env_key=?", (env_key,)); conn.commit(); return cur.rowcount
    def stats(self):
        conn = Database.get_conn(self.db_name)
        return {"templates": conn.execute("SELECT COUNT(*) FROM domain_data_templates").fetchone()[0], "batches": conn.execute("SELECT COUNT(*) FROM domain_data_batches").fetchone()[0]}


datafactory_store = DatafactoryStore()
DatafactoryRepo = datafactory_store
