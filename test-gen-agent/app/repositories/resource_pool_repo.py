# app/repositories/resource_pool_repo.py
"""资源池数据访问层（Phase 3 重构 · 4 层对齐）。

resource_pools 表为独立自洽小域，直接下沉直连 SQL，
收敛 test_resources 中内联的 SQL，统一数据访问入口。
"""
import time
import uuid
from typing import Dict, List, Optional

from app.repositories.base import BaseRepo

# 表结构：与其他模块（method_compat / seed_all_data）保持一致
_SCHEMA = """
    CREATE TABLE IF NOT EXISTS resource_pools (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        enable INTEGER DEFAULT 1,
        created_at REAL,
        updated_at REAL
    )
"""


class ResourcePoolRepo(BaseRepo):
    """资源池数据访问层。

    db_name 统一路由到 tga.db（Phase 6 合并库）。
    """

    db_name = "tga.db"
    table_name = "resource_pools"

    # ── 建表 ────────────────────────────────────────────
    @classmethod
    def ensure_table(cls) -> None:
        conn = cls.get_conn()
        conn.execute(_SCHEMA)
        conn.commit()

    # ── CRUD ────────────────────────────────────────────
    @classmethod
    def create(cls, name: str = "未命名资源池", description: str = "",
               enable: bool = True, pool_id: str = "") -> dict:
        """新增资源池，返回 {id}。

        pool_id 可选：DDD 聚合接线时传入聚合根的 id，保证返回 id == 落库 id；
        缺省时由本层生成（向后兼容既有调用方）。
        """
        cls.ensure_table()
        pool_id = pool_id or str(uuid.uuid4())
        now = time.time()
        cls.execute(
            "INSERT INTO resource_pools (id, name, description, enable, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?)",
            (pool_id, name, description, 1 if enable else 0, now, now),
        )
        return {"id": pool_id}

    @classmethod
    def get_all(cls, keyword: str = "") -> List[Dict]:
        """按关键字（可选）倒序获取全部资源池。"""
        cls.ensure_table()
        if keyword:
            return cls.query_all(
                "SELECT * FROM resource_pools WHERE name LIKE ? ORDER BY created_at DESC",
                (f"%{keyword}%",),
            )
        return cls.query_all(
            "SELECT * FROM resource_pools ORDER BY created_at DESC"
        )

    @classmethod
    def get_by_id(cls, pool_id: str) -> Optional[dict]:
        """按 ID 查询单个资源池。"""
        cls.ensure_table()
        return cls.query_one(
            "SELECT * FROM resource_pools WHERE id = ?", (pool_id,)
        )

    @classmethod
    def update(cls, pool_id: str, data: dict) -> bool:
        """按 ID 动态更新（仅处理白名单字段）。"""
        cls.ensure_table()
        allowed = ("name", "description", "enable")
        sets: list[str] = []
        params: list = []
        for key in allowed:
            if key in data:
                if key == "enable":
                    sets.append("enable = ?")
                    params.append(1 if bool(data[key]) else 0)
                else:
                    sets.append(f"{key} = ?")
                    params.append(data[key])
        if not sets:
            return False
        sets.append("updated_at = ?")
        params.append(time.time())
        params.append(pool_id)
        cursor = cls.execute(
            f"UPDATE resource_pools SET {', '.join(sets)} WHERE id = ?", tuple(params)
        )
        return cursor.rowcount > 0

    @classmethod
    def delete(cls, pool_id: str) -> bool:
        """按 ID 删除资源池。"""
        cls.ensure_table()
        cursor = cls.execute(
            "DELETE FROM resource_pools WHERE id = ?", (pool_id,)
        )
        return cursor.rowcount > 0

    @classmethod
    def set_enable(cls, pool_id: str, enable: bool) -> bool:
        """设置资源池启用状态。"""
        cls.ensure_table()
        cursor = cls.execute(
            "UPDATE resource_pools SET enable = ?, updated_at = ? WHERE id = ?",
            (1 if enable else 0, time.time(), pool_id),
        )
        return cursor.rowcount > 0


resource_pool_repo = ResourcePoolRepo
