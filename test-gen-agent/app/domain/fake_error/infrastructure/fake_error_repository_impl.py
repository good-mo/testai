"""误报规则聚合仓储实现（去 Adapter，直接 SQL）。

修复说明：
  - 消除 FakeErrorRepoAdapter 中间层：它只做 entity↔dict 翻译，没有业务逻辑
  - 把 fake_error_repo 的 SQL 移入此处，成为域内私有实现
  - 聚合重建（from_dict）与持久化在同一个文件内闭环，不再跨文件翻译

修复前调用链：AppService → FakeErrorRepoAdapter → fake_error_repo → SQLite（4 层）
修复后调用链：AppService → FakeErrorRepositoryImpl → SQLite（2 层）
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.domain.fake_error.domain.entities.error_rule import FakeErrorRule
from app.logging_config import get_logger

logger = get_logger(__name__)

# ── 域内常量（从 fake_error_repo.py 迁入）──────────────────
DB_NAME = "tga.db"  # 统一数据库（不再用 "projects.db"）
TABLE = "fake_error_rules"


def _get_conn() -> sqlite3.Connection:
    return Database.get_conn(DB_NAME)


def _ensure_tables() -> None:
    """幂等建表 + 补列（权威 DDL）。"""
    conn = _get_conn()
    try:
        # 基础表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fake_error_rules (
                id TEXT PRIMARY KEY,
                project_id TEXT DEFAULT '',
                name TEXT DEFAULT '',
                enable INTEGER DEFAULT 1,
                label TEXT DEFAULT '',
                rule TEXT DEFAULT '',
                rule_result TEXT DEFAULT '',
                create_user TEXT DEFAULT '',
                update_time REAL,
                created_at REAL,
                type TEXT DEFAULT '',
                resp_type TEXT DEFAULT '',
                relation TEXT DEFAULT '',
                expression TEXT DEFAULT ''
            )
        """)
        # 补列（幂等）
        cur = conn.execute("PRAGMA table_info(fake_error_rules)")
        existing = {r["name"] for r in cur.fetchall()}
        for col, typ in [
            ("type", "TEXT DEFAULT ''"),
            ("resp_type", "TEXT DEFAULT ''"),
            ("relation", "TEXT DEFAULT ''"),
            ("expression", "TEXT DEFAULT ''"),
        ]:
            if col not in existing:
                conn.execute(f"ALTER TABLE fake_error_rules ADD COLUMN {col} {typ}")
        conn.commit()
    except Exception as e:
        logger.warning("fake_error_rules 初始化失败: %s", e)


class FakeErrorRepositoryImpl:
    """误报规则仓储：直接持有 SQL，不再委托 Flat Repository。"""

    def __init__(self):
        _ensure_tables()

    def next_id(self) -> str:
        return str(uuid.uuid4())

    # ── 聚合重建 ──────────────────────────────────────────
    @staticmethod
    def _row_to_entity(row) -> FakeErrorRule:
        """数据库行 → 聚合根实体。"""
        keys = row.keys()

        def _get(name, default=""):
            return row[name] if name in keys else default

        tag_type = _get("type") or _get("label", "") or ""
        resp_type = _get("resp_type") or ""
        relation = _get("relation") or ""
        expression = _get("expression") or ""

        rule_result = _get("rule_result") or ""
        if not rule_result:
            from app.domain.fake_error.domain.entities.error_rule import build_rule_result
            rule_result = build_rule_result(resp_type, relation, expression)

        return FakeErrorRule(
            rule_id=str(row["id"]),
            project_id=row["project_id"],
            name=row["name"],
            enable=bool(row["enable"]),
            tag_type=tag_type,
            resp_type=resp_type,
            relation=relation,
            expression=expression,
            rule_result=rule_result,
            create_user=row["create_user"],
            create_time=row.get("created_at"),
            update_time=row.get("update_time"),
        )

    # ── 读 ────────────────────────────────────────────────
    def list(self, project_id: str = "") -> List[FakeErrorRule]:
        """列出误报规则。"""
        conn = _get_conn()
        try:
            if project_id:
                cur = conn.execute(
                    "SELECT * FROM fake_error_rules WHERE project_id=? ORDER BY created_at DESC",
                    (project_id,),
                )
            else:
                cur = conn.execute("SELECT * FROM fake_error_rules ORDER BY created_at DESC")
            return [self._row_to_entity(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning("list 失败: %s", e)
            return []

    def get(self, rule_id: str) -> Optional[FakeErrorRule]:
        """获取单个规则。"""
        for r in self.list():
            if r.id.value == rule_id:
                return r
        return None

    def get_enabled_count(self, project_id: str = "") -> int:
        """获取启用中的规则数量。"""
        conn = _get_conn()
        try:
            if project_id:
                cur = conn.execute(
                    "SELECT COUNT(*) AS c FROM fake_error_rules WHERE project_id=? AND enable=1",
                    (project_id,),
                )
            else:
                cur = conn.execute("SELECT COUNT(*) AS c FROM fake_error_rules WHERE enable=1")
            row = cur.fetchone()
            return row["c"] if row else 0
        finally:
            pass

    # ── 写 ────────────────────────────────────────────────
    def save(self, rule: FakeErrorRule) -> FakeErrorRule:
        """保存规则（INSERT OR REPLACE，兼作新增与整体更新）。"""
        conn = _get_conn()
        now = time.time()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO fake_error_rules
                (id, project_id, name, enable, label, rule, rule_result, create_user,
                 type, resp_type, relation, expression, update_time, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    rule.id.value,
                    rule.project_id,
                    rule.name,
                    1 if rule.enable else 0,
                    rule.tag_type,  # label 兼容
                    rule.expression,  # rule 兼容
                    rule.rule_result,
                    rule.create_user,
                    rule.tag_type,
                    rule.resp_type,
                    rule.relation,
                    rule.expression,
                    now, now,
                ),
            )
            conn.commit()
        except Exception as e:
            logger.warning("save 失败: %s", e)
        return rule

    def delete(self, rule_id: str) -> bool:
        """删除规则。"""
        conn = _get_conn()
        try:
            conn.execute("DELETE FROM fake_error_rules WHERE id=?", (rule_id,))
            conn.commit()
            return True
        finally:
            pass

    def update_enable(self, rule_ids: List[str], enable: bool) -> None:
        """批量启用/禁用规则。"""
        conn = _get_conn()
        now = time.time()
        try:
            for rid in rule_ids:
                conn.execute(
                    "UPDATE fake_error_rules SET enable=?, update_time=? WHERE id=?",
                    (1 if enable else 0, now, rid),
                )
            conn.commit()
        finally:
            pass


# 模块级单例
fake_error_repository = FakeErrorRepositoryImpl()

__all__ = ["FakeErrorRepositoryImpl", "fake_error_repository"]