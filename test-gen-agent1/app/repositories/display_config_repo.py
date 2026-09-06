# app/repositories/display_config_repo.py
"""界面配置数据访问层（Phase P2 · auth 占位真实化）。

承载系统「页面/登录页/平台主页」展示配置（display/info + display/save）：
  - 与 TestPilot 语义一致：配置以 `ui.<key>` 参数列表形式存储
  - 文本项直接落 param_value；文件项（icon/loginLogo/loginImage/logoPlatform）
    保存后可访问 URL 至 param_value，fileName 保留原始文件名
  - 原实现 display/info 返回空数组、display/save 空转，现统一落 page_display_configs 表
"""
import time
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.repositories.base import BaseRepo

# 前端页面配置的四个文件类 key（对应 FileParamItem.type=file）
FILE_KEYS = {"ui.icon", "ui.loginLogo", "ui.loginImage", "ui.logoPlatform"}

# 文本类 key 的默认顺序（供 /display/info 稳定排序输出）
_TEXT_KEYS = [
    "ui.slogan", "ui.title", "ui.style", "ui.theme",
    "ui.helpDoc", "ui.platformName",
]
_ALL_KEYS = [
    "ui.icon", "ui.loginLogo", "ui.loginImage", "ui.logoPlatform",
    "ui.slogan", "ui.title", "ui.style", "ui.theme",
    "ui.helpDoc", "ui.platformName",
]


class DisplayConfigRepo(BaseRepo):
    """界面配置仓库：page_display_configs 表（单例全局配置，无 owner）。"""

    db_name = "auth.db"
    table_name = "page_display_configs"

    # ── 建表 ──────────────────────────────────────────────
    @classmethod
    def _ensure_table(cls) -> None:
        conn = Database.get_conn(cls.db_name)
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

    @classmethod
    def save_many(cls, items: List[Dict[str, Any]]) -> None:
        """批量 upsert 界面配置项。items: [{paramKey, paramValue, type, fileName}]。"""
        cls._ensure_table()
        now = time.time()
        with Database.transaction(cls.db_name) as conn:
            for item in items:
                key = str(item.get("paramKey") or "")
                if not key:
                    continue
                value = item.get("paramValue") or ""
                ptype = str(item.get("type") or "text")
                fname = item.get("fileName") or ""
                # 文件项：无实际文件且 paramValue 为空且 original=True 视为清空
                if ptype == "file" and item.get("original") and not item.get("hasFile") and not value:
                    conn.execute(
                        "DELETE FROM page_display_configs WHERE param_key = ?", (key,)
                    )
                    continue
                conn.execute(
                    """INSERT INTO page_display_configs (param_key, param_value, param_type, file_name, updated_at)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(param_key) DO UPDATE SET
                           param_value=excluded.param_value,
                           param_type=excluded.param_type,
                           file_name=excluded.file_name,
                           updated_at=excluded.updated_at""",
                    (key, value, ptype, fname, now),
                )

    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        """按稳定 key 顺序返回全部界面配置项。"""
        cls._ensure_table()
        conn = Database.get_conn(cls.db_name)
        rows = conn.execute(
            "SELECT * FROM page_display_configs"
        ).fetchall()
        stored = {r["param_key"]: r for r in rows}

        def _key_rank(key: str) -> int:
            try:
                return _ALL_KEYS.index(key)
            except ValueError:
                return len(_ALL_KEYS)

        items = []
        for key in sorted(stored.keys(), key=_key_rank):
            r = stored[key]
            items.append({
                "paramKey": r["param_key"],
                "paramValue": r["param_value"] or "",
                "type": r["param_type"] or "text",
                "fileName": r["file_name"] or "",
            })
        return items

    @classmethod
    def get_by_key(cls, key: str) -> Optional[Dict[str, Any]]:
        cls._ensure_table()
        row = cls.query_one(
            "SELECT * FROM page_display_configs WHERE param_key = ?", (key,)
        )
        if not row:
            return None
        return {
            "paramKey": row["param_key"],
            "paramValue": row["param_value"] or "",
            "type": row["param_type"] or "text",
            "fileName": row["file_name"] or "",
        }

    @classmethod
    def delete_by_key(cls, key: str) -> None:
        """删除单个界面配置项（文件项清空场景）。"""
        cls._ensure_table()
        cls.execute("DELETE FROM page_display_configs WHERE param_key = ?", (key,))

    @classmethod
    def clear(cls) -> None:
        """清空全部界面配置（重置场景）。"""
        cls._ensure_table()
        cls.execute("DELETE FROM page_display_configs")

display_config_repo = DisplayConfigRepo
