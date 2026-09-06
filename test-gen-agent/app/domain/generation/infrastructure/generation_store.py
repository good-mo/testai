"""测试生成上下文运行记录存储。"""
from __future__ import annotations
import json
import time
import uuid
from app.core.database import Database


class GenerationStore:
    db_name = "tga.db"

    def __init__(self):
        conn = Database.get_conn(self.db_name)
        conn.execute("""CREATE TABLE IF NOT EXISTS domain_generation_runs (
            id TEXT PRIMARY KEY, file_path TEXT NOT NULL DEFAULT '', source_code TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'single', generated_tests TEXT NOT NULL DEFAULT '',
            test_result TEXT NOT NULL DEFAULT '{}', coverage_report TEXT NOT NULL DEFAULT '{}',
            performance_report TEXT NOT NULL DEFAULT '{}', retry_count INTEGER NOT NULL DEFAULT 0,
            saved_to TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '', metadata TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL, updated_at REAL NOT NULL)""")
        conn.commit()

    @staticmethod
    def _decode(row):
        if not row: return None
        data = dict(row)
        for key in ("test_result", "coverage_report", "performance_report", "metadata"):
            try: data[key] = json.loads(data[key] or "{}")
            except (TypeError, json.JSONDecodeError): data[key] = {}
        return data

    def save(self, **data):
        item_id = data.get("id") or uuid.uuid4().hex[:16]; now = time.time(); conn = Database.get_conn(self.db_name)
        conn.execute("INSERT INTO domain_generation_runs (id,file_path,source_code,source,generated_tests,test_result,coverage_report,performance_report,retry_count,saved_to,error,metadata,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (item_id, data.get("file_path", ""), data.get("source_code", ""), data.get("source", "single"), data.get("generated_tests", ""), json.dumps(data.get("test_result", {}), ensure_ascii=False, default=str), json.dumps(data.get("coverage_report", {}), ensure_ascii=False, default=str), json.dumps(data.get("performance_report", {}), ensure_ascii=False, default=str), data.get("retry_count", 0), data.get("saved_to", ""), data.get("error", ""), json.dumps(data.get("metadata", {}), ensure_ascii=False, default=str), now, now)); conn.commit(); return self.get(item_id)

    def get(self, item_id): return self._decode(Database.get_conn(self.db_name).execute("SELECT * FROM domain_generation_runs WHERE id=?", (item_id,)).fetchone())
    def update_record(self, item_id, **data):
        if not self.get(item_id): return None
        data["id"] = item_id
        conn = Database.get_conn(self.db_name); conn.execute("DELETE FROM domain_generation_runs WHERE id=?", (item_id,)); conn.commit(); return self.save(**data)
    def list_records(self, file_path=None, source=None, passed=None, search=None, limit=50, offset=0):
        clauses, params = [], []
        if file_path: clauses.append("file_path=?"); params.append(file_path)
        if source: clauses.append("source=?"); params.append(source)
        if search: clauses.append("(file_path LIKE ? OR generated_tests LIKE ?)"); params.extend([f"%{search}%", f"%{search}%"])
        params.extend([max(1, limit), max(0, offset)]); where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = Database.get_conn(self.db_name).execute(f"SELECT * FROM domain_generation_runs{where} ORDER BY updated_at DESC LIMIT ? OFFSET ?", params).fetchall(); return [self._decode(row) for row in rows]
    def count_records(self, **kwargs): return len(self.list_records(limit=100000, **kwargs))
    def delete_by_id(self, item_id):
        conn = Database.get_conn(self.db_name); cur = conn.execute("DELETE FROM domain_generation_runs WHERE id=?", (item_id,)); conn.commit(); return cur.rowcount > 0
    def delete_batch(self, item_ids):
        return sum(self.delete_by_id(item_id) for item_id in item_ids)
    def clear(self, source=None):
        conn = Database.get_conn(self.db_name)
        if source:
            cur = conn.execute("DELETE FROM domain_generation_runs WHERE source=?", (source,))
        else:
            cur = conn.execute("DELETE FROM domain_generation_runs")
        conn.commit(); return cur.rowcount
    def stats(self):
        conn = Database.get_conn(self.db_name); total = conn.execute("SELECT COUNT(*) FROM domain_generation_runs").fetchone()[0]; return {"total": total}


generation_store = GenerationStore()
RunRepo = generation_store
