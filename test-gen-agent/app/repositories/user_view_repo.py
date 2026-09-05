# app/repositories/user_view_repo.py
"""用户视图（user-view）数据访问层（Phase 4 重构 · 4 层对齐）。

从 app/routers/user_view_store.py 下沉：原 router 目录直接持有 SQL（建表 + CRUD），
现收敛到本仓库——Router → Service → Repository → DB。Service 层（app/services/
user_view_service.py）统一对外提供业务入口，Router 不再直连数据访问。

承载 user_views 表（统一 tga.db）：
  - 每条自定义视图存一行，视图的 name / searchMode / conditions 等以 JSON 整体保存
    （视图字段随前端演进可变，不做逐列强绑定）
  - 内部视图（internalViews，如 all_data）由 Router 层动态生成，不落库
"""
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.repositories.base import BaseRepo

DB_NAME = "tga.db"


class UserViewRepo(BaseRepo):
    """用户视图仓库：user_views 表数据访问。"""

    db_name = DB_NAME
    table_name = "user_views"

    # ── 建表 ──────────────────────────────────────────────
    @classmethod
    def init_table(cls) -> None:
        """幂等建表。"""
        conn = Database.get_conn(cls.db_name)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_views (
                id TEXT PRIMARY KEY,
                view_type TEXT NOT NULL,
                scope_id TEXT DEFAULT '',
                user_id TEXT DEFAULT 'admin',
                name TEXT DEFAULT '',
                search_mode TEXT DEFAULT 'AND',
                pos INTEGER DEFAULT 0,
                payload TEXT DEFAULT '{}',
                create_time REAL,
                update_time REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_views_scope
            ON user_views(view_type, scope_id)
        """)
        conn.commit()

    @classmethod
    def _ensure_table(cls) -> None:
        cls.init_table()

    # ── 行转换 ────────────────────────────────────────────
    @staticmethod
    def _to_view(row) -> Dict[str, Any]:
        """把数据行还原为前端视图对象（payload 中保留自定义字段）。"""
        payload = {}
        try:
            payload = json.loads(row["payload"] or "{}")
        except Exception:
            payload = {}
        payload.update({
            "id": row["id"],
            "viewType": row["view_type"],
            "scopeId": row["scope_id"] or "",
            "userId": row["user_id"] or "admin",
            "name": row["name"] or payload.get("name", ""),
            "searchMode": row["search_mode"] or payload.get("searchMode", "AND"),
            "pos": row["pos"] if row["pos"] is not None else payload.get("pos", 0),
            "internal": False,
            "createTime": row["create_time"],
            "updateTime": row["update_time"],
        })
        return payload

    # ── CRUD ──────────────────────────────────────────────
    @classmethod
    def list_custom_views(cls, view_type: str, scope_id: str = "") -> List[Dict[str, Any]]:
        """按 view_type+scope_id 读取全部自定义视图，按 pos 升序。"""
        cls._ensure_table()
        conn = Database.get_conn(cls.db_name)
        rows = conn.execute(
            "SELECT * FROM user_views WHERE view_type=? AND scope_id=? ORDER BY pos ASC",
            (view_type, scope_id or ""),
        ).fetchall()
        return [cls._to_view(r) for r in rows]

    @classmethod
    def get_custom_view(cls, view_id: str) -> Optional[Dict[str, Any]]:
        """按视图 id 读取单条自定义视图；不存在返回 None。"""
        if not view_id:
            return None
        cls._ensure_table()
        conn = Database.get_conn(cls.db_name)
        row = conn.execute(
            "SELECT * FROM user_views WHERE id = ?", (view_id,)
        ).fetchone()
        return cls._to_view(row) if row else None

    @classmethod
    def _next_pos(cls, view_type: str, scope_id: str) -> int:
        conn = Database.get_conn(cls.db_name)
        row = conn.execute(
            "SELECT COALESCE(MAX(pos), 0) AS m FROM user_views WHERE view_type=? AND scope_id=?",
            (view_type, scope_id or ""),
        ).fetchone()
        return int(row["m"]) if row and row["m"] is not None else 0

    @classmethod
    def add_custom_view(cls, view_type: str, scope_id: str, body: Dict[str, Any],
                        user_id: str = "admin", new_id: str = "") -> Dict[str, Any]:
        """新增自定义视图并落库，返回前端视图对象。"""
        cls._ensure_table()
        vid = (new_id or body.get("id") or str(uuid.uuid4()))
        now = time.time()
        name = body.get("name", "") or ""
        search_mode = body.get("searchMode", "AND") or "AND"
        pos = body.get("pos") if body.get("pos") is not None else cls._next_pos(view_type, scope_id) + 1
        # payload：保留视图全量字段（conditions、自定义筛选、name 等），便于 get/list 读回
        payload = dict(body)
        payload["id"] = vid
        payload["viewType"] = view_type
        payload["scopeId"] = scope_id or ""
        payload["userId"] = user_id
        payload["name"] = name
        payload["searchMode"] = search_mode
        payload["internal"] = False
        payload["pos"] = pos
        payload["createTime"] = int(now * 1000)
        payload["updateTime"] = int(now * 1000)

        conn = Database.get_conn(cls.db_name)
        conn.execute(
            """INSERT OR REPLACE INTO user_views
               (id, view_type, scope_id, user_id, name, search_mode, pos, payload,
                create_time, update_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (vid, view_type, scope_id or "", user_id, name, search_mode, pos,
             json.dumps(payload, ensure_ascii=False), now, now),
        )
        conn.commit()
        return payload

    @classmethod
    def update_custom_view(cls, view_id: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """按视图 id 更新（合并 body 字段）；不存在返回 None。"""
        if not view_id:
            return None
        existing = cls.get_custom_view(view_id)
        if not existing:
            return None
        merged = dict(existing)
        for k, v in (body or {}).items():
            if k is None:
                continue
            merged[k] = v
        # 同步顶层列
        name = merged.get("name", "") or ""
        search_mode = merged.get("searchMode", "AND") or "AND"
        pos = merged.get("pos", existing.get("pos", 0))
        now = time.time()
        merged["updateTime"] = int(now * 1000)

        conn = Database.get_conn(cls.db_name)
        conn.execute(
            """UPDATE user_views SET name=?, search_mode=?, pos=?, payload=?,
               scope_id=?, update_time=?
               WHERE id=?""",
            (name, search_mode, pos if pos is not None else 0,
             json.dumps(merged, ensure_ascii=False),
             merged.get("scopeId", existing.get("scopeId", "")),
             now, view_id),
        )
        conn.commit()
        return merged

    @classmethod
    def delete_custom_view(cls, view_id: str) -> bool:
        """按视图 id 删除；返回是否存在并删除。"""
        if not view_id:
            return False
        cls._ensure_table()
        conn = Database.get_conn(cls.db_name)
        cur = conn.execute("DELETE FROM user_views WHERE id = ?", (view_id,))
        conn.commit()
        return cur.rowcount > 0


# 便捷单例（与其它 repo 风格一致）
user_view_repo = UserViewRepo


# 确保表存在（导入即建表，与旧 user_view_store 模块 import 时调用 init_table 对齐）
UserViewRepo.init_table()
