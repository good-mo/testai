"""工作流状态聚合仓储实现（去 Adapter，直接 SQL）。

修复说明：
  - 消除 WorkflowRepoAdapter 中间层（只做 entity↔dict 翻译，无业务逻辑）
  - 把 workflow_repo 的 SQL 移入此处，成为域内私有实现
  - 聚合重建（from_dict）与持久化在同一个文件内闭环，不再跨文件翻译
  - DB 从 projects.db 统一为 tga.db

修复前调用链：AppService → WorkflowRepoAdapter → workflow_repo → SQLite（4 层）
修复后调用链：AppService → WorkflowRepositoryImpl → SQLite（2 层）
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.domain.workflow.domain.entities.workflow_status import WorkflowStatus
from app.logging_config import get_logger

logger = get_logger(__name__)

# ── 域内常量 ──────────────────────────────────────────
DB_NAME = "tga.db"
TABLE_STATUSES = "workflow_statuses"
TABLE_FLOWS = "workflow_flows"


class WorkflowRepositoryImpl:
    """工作流状态仓储：直接持有 SQL，不再委托 Flat Repository。"""

    def __init__(self):
        self._ensure_tables()

    @staticmethod
    def _conn():
        return Database.get_conn(DB_NAME)

    # ── 建表 ──────────────────────────────────────────────
    @classmethod
    def _ensure_tables(cls) -> None:
        """幂等建表。"""
        conn = cls._conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_statuses (
                    id TEXT PRIMARY KEY,
                    scope_type TEXT DEFAULT 'PROJECT',
                    scope_id TEXT DEFAULT '',
                    scene TEXT DEFAULT 'FUNCTIONAL',
                    name TEXT DEFAULT '',
                    remark TEXT DEFAULT '',
                    pos INTEGER DEFAULT 0,
                    status_definitions TEXT DEFAULT '[]',
                    internal INTEGER DEFAULT 0,
                    create_time REAL,
                    update_time REAL,
                    create_user TEXT DEFAULT 'admin'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_flows (
                    source_status_id TEXT,
                    target_status_id TEXT,
                    PRIMARY KEY (source_status_id, target_status_id)
                )
            """)
            conn.commit()
        except Exception as e:
            logger.warning("workflow 表初始化失败: %s", e)

    # ── 聚合重建 ──────────────────────────────────────────
    @staticmethod
    def _row_to_entity(row: dict) -> WorkflowStatus:
        """数据库行 → 聚合根实体。"""
        defs_raw = row.get("status_definitions") or "[]"
        try:
            status_defs = json.loads(defs_raw) if isinstance(defs_raw, str) else list(defs_raw)
        except Exception:
            status_defs = []
        if not isinstance(status_defs, list):
            status_defs = []

        # 读取流转目标
        conn = Database.get_conn(DB_NAME)
        flow_cur = conn.execute(
            "SELECT target_status_id FROM workflow_flows WHERE source_status_id=?",
            (row["id"],),
        )
        flow_targets = [r["target_status_id"] for r in flow_cur.fetchall()]

        return WorkflowStatus.from_dict({
            "id": row["id"],
            "name": row["name"],
            "scene": row["scene"],
            "remark": row["remark"] or "",
            "internal": bool(row["internal"]),
            "scopeType": row["scope_type"],
            "scopeId": row["scope_id"],
            "pos": row["pos"],
            "statusDefinitions": status_defs,
            "statusFlowTargets": flow_targets,
            "createTime": int((row["create_time"] or 0) * 1000),
            "updateTime": int((row["update_time"] or 0) * 1000),
            "createUser": row["create_user"],
        })

    # ── 读 ────────────────────────────────────────────────
    def list(self, scope_type: str, scope_id: str, scene: str) -> List[WorkflowStatus]:
        conn = self._conn()
        try:
            cur = conn.execute(
                """SELECT * FROM workflow_statuses
                   WHERE scope_type=? AND scope_id=? AND scene=?
                   ORDER BY pos ASC, create_time ASC""",
                (scope_type, scope_id, scene),
            )
            rows = cur.fetchall()
            return [self._row_to_entity(dict(r)) for r in rows]
        except Exception as e:
            logger.warning("list_statuses 失败: %s", e)
            return []

    def get(self, status_id: str) -> Optional[WorkflowStatus]:
        conn = self._conn()
        try:
            cur = conn.execute("SELECT * FROM workflow_statuses WHERE id=?", (status_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_entity(dict(row))
        except Exception:
            return None

    # ── 写 ────────────────────────────────────────────────
    def save(self, status: WorkflowStatus) -> WorkflowStatus:
        """新增或更新状态。"""
        existing = self.get(status.id.value)
        conn = self._conn()
        now = time.time()

        if existing:
            # 更新
            conn.execute(
                """UPDATE workflow_statuses SET name=?, remark=?, status_definitions=?, update_time=? WHERE id=?""",
                (
                    status.name,
                    status.remark,
                    json.dumps(status.status_definitions, ensure_ascii=False),
                    now,
                    status.id.value,
                ),
            )
        else:
            # 新增 - 获取最大 pos
            cur = conn.execute(
                "SELECT MAX(pos) AS max_pos FROM workflow_statuses WHERE scope_type=? AND scope_id=? AND scene=?",
                (status.scope_type, status.scope_id, status.scene),
            )
            row = cur.fetchone()
            max_pos = row["max_pos"] if row and row["max_pos"] is not None else -1
            pos = max_pos + 1

            conn.execute(
                """INSERT INTO workflow_statuses
                   (id, scope_type, scope_id, scene, name, remark, pos, status_definitions,
                    internal, create_time, update_time, create_user)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    status.id.value,
                    status.scope_type,
                    status.scope_id,
                    status.scene,
                    status.name,
                    status.remark,
                    pos,
                    json.dumps(status.status_definitions, ensure_ascii=False),
                    1 if status.is_internal else 0,
                    now,
                    now,
                    status.create_user,
                ),
            )
        conn.commit()

        # 回读权威行
        refreshed = self.get(status.id.value)
        return refreshed if refreshed is not None else status

    def delete(self, status_id: str) -> bool:
        conn = self._conn()
        try:
            conn.execute("DELETE FROM workflow_statuses WHERE id=?", (status_id,))
            conn.execute("DELETE FROM workflow_flows WHERE source_status_id=? OR target_status_id=?",
                         (status_id, status_id))
            conn.commit()
            return True
        except Exception as e:
            logger.warning("delete_status 失败: %s", e)
            return False

    def sort(self, status_ids: List[str]) -> bool:
        """重新排序状态。"""
        conn = self._conn()
        for idx, sid in enumerate(status_ids):
            conn.execute(
                "UPDATE workflow_statuses SET pos=? WHERE id=?",
                (idx, sid),
            )
        conn.commit()
        return True

    def update_flows(self, status_id: str, target_ids: List[str]) -> bool:
        """更新状态流转关系。"""
        conn = self._conn()
        conn.execute("DELETE FROM workflow_flows WHERE source_status_id=?", (status_id,))
        for tid in target_ids:
            conn.execute(
                "INSERT OR IGNORE INTO workflow_flows (source_status_id, target_status_id) VALUES (?,?)",
                (status_id, str(tid)),
            )
        conn.commit()
        return True

    def set_start_status(self, status_id: str, scope_type: str, scope_id: str, scene: str) -> None:
        """确保只保留一个 START 状态。"""
        statuses = self.list(scope_type, scope_id, scene)
        for s in statuses:
            if s.id.value != status_id and s.is_start():
                # 清除该状态的 START 标记
                new_defs = [d for d in s.status_definitions if d != "START"]
                conn = self._conn()
                conn.execute(
                    "UPDATE workflow_statuses SET status_definitions=? WHERE id=?",
                    (json.dumps(new_defs, ensure_ascii=False), s.id.value),
                )
                conn.commit()

    def seed_defaults(self, scope_type: str, scope_id: str, scene: str) -> List[WorkflowStatus]:
        """在范围内播种默认状态（首次访问时）。"""
        existing = self.list(scope_type, scope_id, scene)
        if existing:
            return existing

        defaults = [
            ("新建", "创建后进入的初始状态", ["START"]),
            ("处理中", "正在处理中", []),
            ("已完成", "处理完成", ["END"]),
        ]
        created = []
        conn = self._conn()
        now = time.time()

        for i, (name, remark, defs) in enumerate(defaults):
            sid = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO workflow_statuses
                   (id, scope_type, scope_id, scene, name, remark, pos, status_definitions,
                    internal, create_time, update_time, create_user)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    sid, scope_type, scope_id, scene, name, remark, i,
                    json.dumps(defs, ensure_ascii=False), 1, now, now, "system",
                ),
            )
            conn.commit()
            st = self.get(sid)
            if st:
                created.append(st)

        # 设置流转关系：新建->处理中->已完成
        if len(created) >= 3:
            self.update_flows(created[0].id.value, [created[1].id.value])
            self.update_flows(created[1].id.value, [created[2].id.value])
            self.update_flows(created[2].id.value, [])

        return created


# 模块级单例
workflow_repository = WorkflowRepositoryImpl()

__all__ = ["WorkflowRepositoryImpl", "workflow_repository"]
