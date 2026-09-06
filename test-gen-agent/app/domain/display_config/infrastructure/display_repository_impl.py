"""展示配置聚合仓储实现（去 Adapter，直接 SQL）。

修复说明：
  - 消除 DisplayRepoAdapter 中间层：它只做 entity↔dict 翻译，没有业务逻辑
  - 把 display_config_repo 的 SQL 移入此处，成为域内私有实现
  - 聚合重建（from_dict）与持久化在同一个文件内闭环，不再跨文件翻译

修复前调用链：AppService → DisplayRepoAdapter → DisplayConfigRepo → SQLite（4 层）
修复后调用链：AppService → DisplayConfigRepositoryImpl → SQLite（2 层）
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.core.database import Database
from app.domain.display_config.domain.entities.display_item import DisplayConfigItem

# ── 域内常量（从 display_config_repo.py 迁入）──────────────────
DB_NAME = "tga.db"  # 统一数据库（不再用 "auth.db"）
TABLE = "page_display_configs"

# 稳定 key 顺序（供 get_all 排序输出）
_ALL_KEYS = [
    "ui.icon", "ui.loginLogo", "ui.loginImage", "ui.logoPlatform",
    "ui.slogan", "ui.title", "ui.style", "ui.theme",
    "ui.helpDoc", "ui.platformName",
]


class DisplayConfigRepositoryImpl:
    """展示配置仓储：直接持有 SQL，不再委托 Flat Repository。"""

    def __init__(self):
        self._ensure_table()

    @staticmethod
    def _conn():
        return Database.get_conn(DB_NAME)

    # ── 建表 ──────────────────────────────────────────────────
    @classmethod
    def _ensure_table(cls) -> None:
        """幂等建表。首次实例化时自动建表。"""
        conn = cls._conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS page_display_configs (
                param_key TEXT PRIMARY KEY,
                param_value TEXT DEFAULT '',
                param_type TEXT DEFAULT 'text',
                file_name TEXT DEFAULT '',
                updated_at REAL
            )
        """)
        conn.commit()

    # ── 聚合重建 ──────────────────────────────────────────────
    @staticmethod
    def _row_to_entity(row: dict) -> DisplayConfigItem:
        """数据库行 → 聚合根实体。"""
        return DisplayConfigItem(
            param_key=row["param_key"],
            param_value=row.get("param_value") or "",
            param_type=row.get("param_type") or "text",
            file_name=row.get("file_name") or "",
            updated_at=row.get("updated_at"),
        )

    @staticmethod
    def _entity_to_row(item: DisplayConfigItem) -> dict:
        """聚合根 → 数据库行。"""
        return {
            "param_key": item.param_key,
            "param_value": item.param_value,
            "param_type": item.param_type,
            "file_name": item.file_name,
        }

    # ── 写 ────────────────────────────────────────────────────
    def save_many(self, items: List[DisplayConfigItem]) -> List[DisplayConfigItem]:
        """批量 upsert 配置项。"""
        now = time.time()
        with Database.transaction(DB_NAME) as conn:
            for item in items:
                row = self._entity_to_row(item)
                conn.execute(
                    """INSERT INTO page_display_configs
                       (param_key, param_value, param_type, file_name, updated_at)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(param_key) DO UPDATE SET
                           param_value=excluded.param_value,
                           param_type=excluded.param_type,
                           file_name=excluded.file_name,
                           updated_at=excluded.updated_at""",
                    (row["param_key"], row["param_value"],
                     row["param_type"], row["file_name"], now),
                )
        return items

    # ── 读 ────────────────────────────────────────────────────
    def get_all(self) -> List[DisplayConfigItem]:
        """按稳定 key 顺序返回全部配置项。"""
        conn = self._conn()
        rows = conn.execute("SELECT * FROM page_display_configs").fetchall()
        stored = {r["param_key"]: dict(r) for r in rows}

        def _key_rank(key: str) -> int:
            try:
                return _ALL_KEYS.index(key)
            except ValueError:
                return len(_ALL_KEYS)

        items = []
        for key in sorted(stored.keys(), key=_key_rank):
            items.append(self._row_to_entity(stored[key]))
        return items

    def get_by_key(self, key: str) -> Optional[DisplayConfigItem]:
        row = self._conn().execute(
            "SELECT * FROM page_display_configs WHERE param_key = ?", (key,)
        ).fetchone()
        return self._row_to_entity(dict(row)) if row else None

    def delete_by_key(self, key: str) -> None:
        self._conn().execute(
            "DELETE FROM page_display_configs WHERE param_key = ?", (key,)
        )
        self._conn().commit()


# 模块级单例
display_config_repository = DisplayConfigRepositoryImpl()