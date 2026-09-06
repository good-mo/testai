# app/apitest/module_store.py
"""
接口测试模块树存储
===================
为接口定义 / 场景 / 调试提供模块树（增删改查、数量统计）。
模块数据持久化到 apitest.db 的 modules 表。

Repository 下沉说明：
模块树的纯数据访问（CRUD / 级联删除 / 事务移动 / 计数）SQL 已下沉到
app.repositories.apitest_repo.ApitestRepo（L3 Repository 层），本模块退化为
兼容门面：建表 DDL（schema 来源）保留在本模块，CRUD 与 build_module_tree
全部直接委托 ApitestRepo，保证对外行为零回归。
"""
import sqlite3
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.repositories.apitest_repo import ApitestRepo


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（统一使用 Database 连接池）。"""
    return Database.get_conn("apitest.db")


def _init_db() -> None:
    """初始化表结构（使用独立临时连接，不影响共享连接）。"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS modules (
                id TEXT PRIMARY KEY,
                scope TEXT NOT NULL,          -- definition / scenario / debug / functional
                name TEXT NOT NULL,
                parent_id TEXT DEFAULT 'root',
                pos INTEGER DEFAULT 1,
                project_id TEXT DEFAULT '',
                created_at REAL,
                updated_at REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_modules_scope ON modules(scope)
        """)
        conn.commit()
    finally:
        # 不关闭共享连接：由 Database 连接池统一管理，避免破坏连接复用
        pass


_init_db()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row)


def add_module(scope: str, name: str, parent_id: str = "root",
               project_id: str = "") -> Dict[str, Any]:
    """新增模块。"""
    return ApitestRepo.add_module(
        scope=scope, name=name, parent_id=parent_id, project_id=project_id,
    )


def get_module(mod_id: str) -> Optional[Dict[str, Any]]:
    return ApitestRepo.get_module(mod_id)


def list_modules(scope: str, project_id: str = "") -> List[Dict[str, Any]]:
    """列出指定作用域的全部模块，可带 project_id 过滤。"""
    return ApitestRepo.list_modules(scope, project_id=project_id)


def update_module(mod_id: str, name: str) -> bool:
    return ApitestRepo.update_module(mod_id, name=name)


def delete_module(mod_id: str) -> bool:
    return ApitestRepo.delete_module(mod_id)


def move_module(drag_node_id: str, drop_node_id: str, drop_position: int = 0) -> bool:
    return ApitestRepo.move_module(
        drag_node_id, drop_node_id, drop_position=drop_position,
    )


def count_modules(scope: str) -> int:
    return ApitestRepo.count_modules(module_type=scope)


def build_module_tree(scope: str, include_api: bool = True, project_id: str = "") -> List[Dict[str, Any]]:
    """构建模块树（含根节点和 API 定义节点、计数）。

    include_api=False 时仅返回模块节点（不含 API 定义节点）。
    委托 ApitestRepo（Repository 层已下沉实现）。
    """
    return ApitestRepo.build_module_tree(
        scope, include_api=include_api, project_id=project_id,
    )
