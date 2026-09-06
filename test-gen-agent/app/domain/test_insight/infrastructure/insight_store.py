"""测试洞察上下文存储。"""
from __future__ import annotations
import sqlite3
from app.db import db_path


class InsightStore:
    def __init__(self):
        self._connection = sqlite3.connect(db_path("tga.db"), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("""CREATE TABLE IF NOT EXISTS test_runs (
            id TEXT PRIMARY KEY, file_path TEXT NOT NULL DEFAULT '', source_hash TEXT NOT NULL DEFAULT '',
            result TEXT NOT NULL DEFAULT '', passed_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0, error_count INTEGER NOT NULL DEFAULT 0,
            coverage REAL NOT NULL DEFAULT 0, env_info TEXT NOT NULL DEFAULT '',
            attribution TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL, created_by TEXT NOT NULL DEFAULT '')""")
        self._connection.commit()

    def _conn(self): return self._connection
    def trace_stats(self):
        row = self._connection.execute("SELECT COUNT(*) AS total, COALESCE(SUM(passed_count),0) AS passed, COALESCE(SUM(failed_count),0) AS failed FROM test_runs").fetchone()
        return dict(row)
    def value(self): return self.trace_stats()
    def incident_avoidance(self): return {"total": 0}
    def assess_risk(self, source_files=None): return {"risk": "unknown", "files": source_files or []}
    def generate_from_description(self, description): return {"description": description}
    def skill_path(self): return {"path": ""}


insight_store = InsightStore()
InsightRepo = insight_store
