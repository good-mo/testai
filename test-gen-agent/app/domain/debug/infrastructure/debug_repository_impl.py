"""调试聚合仓储实现（去 Adapter，直接 SQL）。

修复说明：
  - 消除 DebugRepoAdapter 中间层：它只做 entity↔dict 翻译，没有业务逻辑
  - 把 debug_repo 的 SQL 移入此处，成为域内私有实现
  - 聚合重建（from_dict）与持久化在同一个文件内闭环，不再跨文件翻译

修复前调用链：AppService → DebugRepoAdapter → DebugRepo → SQLite（4 层）
修复后调用链：AppService → DebugRepositoryImpl → SQLite（2 层）
"""
from __future__ import annotations

import json
import time
import uuid
from typing import List, Optional

from app.core.database import Database
from app.domain.debug.domain.entities.debug_item import DebugItem
from app.logging_config import get_logger

logger = get_logger(__name__)

# ── 域内常量（从 debug_repo.py 迁入）──────────────────
DB_NAME = "tga.db"  # 统一数据库（不再用 "apitest.db"）
TABLE = "debug_items"


class DebugRepositoryImpl:
    """调试仓储：直接持有 SQL，不再委托 Flat Repository。"""

    def __init__(self):
        self._ensure_table()

    @staticmethod
    def _conn():
        return Database.get_conn(DB_NAME)

    # ── 建表 ──────────────────────────────────────────────
    @classmethod
    def _ensure_table(cls) -> None:
        """幂等建表。"""
        conn = cls._conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS debug_items (
                id TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                protocol TEXT DEFAULT 'HTTP',
                method TEXT DEFAULT 'GET',
                path TEXT DEFAULT '/',
                url TEXT DEFAULT '/',
                project_id TEXT DEFAULT '',
                module_id TEXT DEFAULT 'root',
                request_data TEXT DEFAULT '{}',
                response_data TEXT DEFAULT '{}',
                create_time REAL,
                update_time REAL,
                create_user TEXT DEFAULT 'admin',
                update_user TEXT DEFAULT 'admin',
                num INTEGER DEFAULT 0
            )
        """)
        conn.commit()

    def next_id(self) -> str:
        return uuid.uuid4().hex[:12]

    # ── 聚合重建 ──────────────────────────────────────────
    @staticmethod
    def _row_to_entity(row: dict) -> DebugItem:
        """数据库行 → 聚合根实体。"""
        try:
            request_data = json.loads(row.get("request_data") or "{}")
        except (json.JSONDecodeError, TypeError):
            request_data = {}
        try:
            response_data = json.loads(row.get("response_data") or "{}")
        except (json.JSONDecodeError, TypeError):
            response_data = {}

        return DebugItem(
            debug_id=row.get("id", ""),
            name=row.get("name", "未命名调试"),
            protocol=row.get("protocol", "HTTP"),
            method=row.get("method", "GET"),
            path=row.get("path", "/"),
            url=row.get("url", row.get("path", "/")),
            project_id=row.get("project_id", ""),
            module_id=row.get("module_id", "root"),
            request_data=request_data,
            response_data=response_data,
            create_user=row.get("create_user", "admin"),
            update_user=row.get("update_user", "admin"),
            num=row.get("num", 0),
            create_time=row.get("create_time"),
            update_time=row.get("update_time"),
        )

    # ── 读 ────────────────────────────────────────────────
    def get(self, debug_id: str) -> Optional[DebugItem]:
        row = self._conn().execute(
            "SELECT * FROM debug_items WHERE id = ?", (debug_id,)
        ).fetchone()
        return self._row_to_entity(dict(row)) if row else None

    def list_all(self) -> List[DebugItem]:
        rows = self._conn().execute(
            "SELECT * FROM debug_items ORDER BY num ASC"
        ).fetchall()
        return [self._row_to_entity(dict(r)) for r in rows]

    # ── 写 ────────────────────────────────────────────────
    def save(self, item: DebugItem) -> DebugItem:
        d = item.to_dict()
        now = time.time()
        self._conn().execute(
            """INSERT OR REPLACE INTO debug_items
               (id, name, protocol, method, path, url, project_id, module_id,
                request_data, response_data, create_time, update_time,
                create_user, update_user, num)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.id.value,
                item.name,
                item.protocol,
                item.method,
                item.path,
                item.url,
                item.project_id,
                item.module_id,
                json.dumps(item.request_data, ensure_ascii=False),
                json.dumps(item.response_data, ensure_ascii=False),
                item.create_time,
                now,
                item._create_user,
                item._update_user,
                item._num,
            ),
        )
        self._conn().commit()
        return item

    def delete(self, debug_id: str) -> bool:
        cursor = self._conn().execute(
            "DELETE FROM debug_items WHERE id = ?", (debug_id,)
        )
        self._conn().commit()
        return cursor.rowcount > 0


# 模块级单例
debug_repository = DebugRepositoryImpl()

__all__ = ["DebugRepositoryImpl", "debug_repository"]
