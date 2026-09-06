# app/repositories/debug_repo.py
"""调试数据访问层（Phase 3 重构 · 4 层对齐）。

本层是 debug_items 表的唯一数据访问入口。
只做 SQLite CRUD，输出归一化的调试项记录（camelCase），
供 service 层直接消费，不承载任何业务决策。
"""
import json
import time
from typing import List

from app.core.database import Database
from app.repositories.base import BaseRepo


class DebugRepo(BaseRepo):
    """debug_items 表数据访问。

    表结构独立（仅适配 debug 路由使用），字段为 snake_case；
    对外输出统一转为 camelCase（与旧 app.adapters.domains.debug 的内存形态一致）。
    """
    db_name = "apitest.db"
    table_name = "debug_items"

    # 建表守卫：首访连接时懒触发一次建表。
    # debug_items 无显式守卫，load_all/save/delete 直接裸查，统一收敛到
    # get_conn() 即可让冷启动空库自动建表。
    _schema_ensured = False

    # ── 建表 ──────────────────────────────────────────────
    @classmethod
    def ensure_table(cls) -> None:
        """初始化调试数据表（幂等）。直接用 Database 连接，避免与守卫递归。"""
        conn = Database.get_conn(cls.db_name)
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

    @classmethod
    def get_conn(cls):
        """返回连接前确保 debug_items 表存在（首访懒触发一次）。

        ensure_table 幂等（CREATE TABLE IF NOT EXISTS），统一入口覆盖
        load_all / save / delete 三条原先无守卫的裸查/裸写路径。
        """
        if not cls._schema_ensured:
            cls.ensure_table()
            cls._schema_ensured = True
        return Database.get_conn(cls.db_name)

    # ── 归一化 ──────────────────────────────────────────────
    @classmethod
    def _normalize_row(cls, row: dict) -> dict:
        """把裸数据库行（snake_case）转成 camelCase 调试项。"""
        try:
            request_data = json.loads(row.get("request_data") or "{}")
        except (json.JSONDecodeError, TypeError):
            request_data = {}
        try:
            response_data = json.loads(row.get("response_data") or "{}")
        except (json.JSONDecodeError, TypeError):
            response_data = {}
        return {
            "id": row.get("id", ""),
            "name": row.get("name", "未命名调试"),
            "protocol": row.get("protocol", "HTTP"),
            "method": row.get("method", "GET"),
            "path": row.get("path", "/"),
            "url": row.get("url", row.get("path", "/")),
            "projectId": row.get("project_id", ""),
            "moduleId": row.get("module_id", "root"),
            "request": request_data,
            "response": response_data,
            "createTime": row.get("create_time", int(time.time() * 1000)),
            "updateTime": row.get("update_time", int(time.time() * 1000)),
            "createUser": row.get("create_user", "admin"),
            "updateUser": row.get("update_user", "admin"),
            "num": row.get("num", 0),
        }

    @classmethod
    def _to_row(cls, item: dict) -> dict:
        """把 camelCase 调试项映射为数据库行的 snake_case 字段。"""
        return {
            "id": item.get("id", ""),
            "name": item.get("name", "未命名调试"),
            "protocol": item.get("protocol", "HTTP"),
            "method": item.get("method", "GET"),
            "path": item.get("path", "/"),
            "url": item.get("url", "/"),
            "project_id": item.get("projectId", ""),
            "module_id": item.get("moduleId", "root"),
            "request_data": json.dumps(item.get("request", {}), ensure_ascii=False),
            "response_data": json.dumps(item.get("response", {}), ensure_ascii=False),
            "create_time": item.get("createTime", int(time.time() * 1000)),
            "update_time": item.get("updateTime", int(time.time() * 1000)),
            "create_user": item.get("createUser", "admin"),
            "update_user": item.get("updateUser", "admin"),
            "num": item.get("num", 0),
        }

    # ── 查询 ──────────────────────────────────────────────
    @classmethod
    def load_all(cls) -> List[dict]:
        """加载全部调试项，按 num 升序。"""
        conn = cls.get_conn()
        rows = conn.execute(
            f"SELECT * FROM {cls.table_name} ORDER BY num ASC"
        ).fetchall()
        return [cls._normalize_row(dict(r)) for r in rows]

    # ── 写入 ──────────────────────────────────────────────
    @classmethod
    def save(cls, item: dict) -> None:
        """保存调试项（INSERT OR REPLACE）。"""
        row = cls._to_row(item)
        conn = cls.get_conn()
        cols = list(row.keys())
        placeholders = ", ".join(["?"] * len(cols))
        sql = (
            f"INSERT OR REPLACE INTO {cls.table_name} ({', '.join(cols)}) "
            f"VALUES ({placeholders})"
        )
        conn.execute(sql, tuple(row.values()))
        conn.commit()

    @classmethod
    def delete(cls, debug_id: str) -> None:
        """按 ID 删除调试项。"""
        conn = cls.get_conn()
        conn.execute(
            f"DELETE FROM {cls.table_name} WHERE id = ?", (debug_id,)
        )
        conn.commit()


debug_repo = DebugRepo
