# app/repositories/workflow_repo.py
"""工作流状态数据访问层（Service 层覆盖补齐 · 业务域缺口）。

承接原 app.projects.workflow_store 的全部 SQLite 读写：
  - workflow_statuses / workflow_flows 两表的建表、CRUD、流转、定义标记、播种
数据存储在 projects.db（经 Database 连接池统一解析）。

本层是 workflow 域数据访问唯一权威出口，供 app.services.workflow_service 消费。
"""
import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database
from app.logging_config import get_logger

logger = get_logger(__name__)

# 工作流状态表的逻辑库名（与旧 workflow_store 保持一致）
DB_NAME = "projects.db"


def _get_conn() -> sqlite3.Connection:
    return Database.get_conn(DB_NAME)


def ensure_tables() -> None:
    """幂等建表（权威 DDL，供 schema_registry / 迁移兜底引用）。"""
    conn = _get_conn()
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


ensure_tables()


def _norm_defs(defs) -> str:
    """归一化 statusDefinitions 为 JSON 数组字符串。"""
    if isinstance(defs, str):
        return defs
    if isinstance(defs, list):
        return json.dumps([str(d) for d in defs if d])
    return "[]"


def _norm_flows(flows) -> str:
    if isinstance(flows, str):
        return flows
    if isinstance(flows, list):
        return json.dumps([str(f) for f in flows if f])
    return "[]"


def _row_to_status(row) -> Dict[str, Any]:
    """将 DB 行转换为前端期望的 WorkFlowType 结构。"""
    defs_raw = row["status_definitions"] or "[]"
    try:
        status_defs = json.loads(defs_raw) if isinstance(defs_raw, str) else list(defs_raw)
    except Exception:
        status_defs = []
    if not isinstance(status_defs, list):
        status_defs = []

    return {
        "id": row["id"],
        "name": row["name"],
        "scene": row["scene"],
        "remark": row["remark"] or "",
        "internal": bool(row["internal"]),
        "scopeType": row["scope_type"],
        "scopeId": row["scope_id"],
        "pos": row["pos"],
        "statusDefinitions": status_defs,
        "statusFlowTargets": [],
        "createTime": int((row["create_time"] or 0) * 1000),
        "updateTime": int((row["update_time"] or 0) * 1000),
        "createUser": row["create_user"],
    }


def list_statuses(scope_type: str, scope_id: str, scene: str) -> List[Dict[str, Any]]:
    """获取指定范围下的工作流状态列表。"""
    conn = _get_conn()
    try:
        cur = conn.execute(
            """SELECT * FROM workflow_statuses
               WHERE scope_type=? AND scope_id=? AND scene=?
               ORDER BY pos ASC, create_time ASC""",
            (scope_type, scope_id, scene),
        )
        rows = cur.fetchall()
        statuses = [_row_to_status(r) for r in rows]

        # 补充每个状态的 statusFlowTargets（从 workflow_flows 表读取）
        for st in statuses:
            sid = st["id"]
            flow_cur = conn.execute(
                "SELECT target_status_id FROM workflow_flows WHERE source_status_id=?",
                (sid,),
            )
            st["statusFlowTargets"] = [r["target_status_id"] for r in flow_cur.fetchall()]
        return statuses
    except Exception as e:
        logger.warning("list_statuses 失败: %s", e)
        return []


def get_status(status_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.execute("SELECT * FROM workflow_statuses WHERE id=?", (status_id,))
        row = cur.fetchone()
        if not row:
            return None
        return _row_to_status(row)
    except Exception:
        return None


def add_status(
    name: str,
    scene: str,
    scope_id: str,
    scope_type: str = "PROJECT",
    remark: str = "",
    all_transfer_to: bool = False,
    status_id: str = "",
    pos: Optional[int] = None,
) -> Dict[str, Any]:
    """创建工作流状态。

    status_id / pos 可选：DDD 适配层显式传入聚合根 id 与位置以便回读一致；
    缺省时沿用历史行为（自动 uuid + max(pos)+1）。
    """

    conn = _get_conn()
    now = time.time()
    sid = status_id or str(uuid.uuid4())

    # 获取最大 pos
    if pos is None:
        cur = conn.execute(
            "SELECT MAX(pos) AS max_pos FROM workflow_statuses WHERE scope_type=? AND scope_id=? AND scene=?",
            (scope_type, scope_id, scene),
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
            sid, scope_type, scope_id, scene, name, remark, pos, "[]",
            0, now, now, "admin",
        ),
    )
    conn.commit()

    # all_transfer_to 仅在创建处透传预留，当前不落额外流转（与旧 store 一致）
    status = get_status(sid)
    return status or {"id": sid, "name": name}


def update_status(
    status_id: str,
    name: str = "",
    remark: str = "",
    all_transfer_to: bool = False,
    status_definitions: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    now = time.time()
    cur = conn.execute("SELECT * FROM workflow_statuses WHERE id=?", (status_id,))
    row = cur.fetchone()
    if not row:
        return None

    conn.execute(
        """UPDATE workflow_statuses SET name=?, remark=?, update_time=? WHERE id=?""",
        (name or row["name"], remark or row["remark"], now, status_id),
    )

    if status_definitions is not None:
        conn.execute(
            "UPDATE workflow_statuses SET status_definitions=? WHERE id=?",
            (_norm_defs(status_definitions), status_id),
        )
    conn.commit()
    return get_status(status_id)


def delete_status(status_id: str) -> bool:
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM workflow_statuses WHERE id=?", (status_id,))
        conn.execute("DELETE FROM workflow_flows WHERE source_status_id=? OR target_status_id=?",
                     (status_id, status_id))
        conn.commit()
        return True
    except Exception as e:
        logger.warning("delete_status 失败: %s", e)
        return False


def set_definition(status_id: str, definition_id: str, enable: bool) -> bool:
    """设置状态的初始态/结束态标记。

    definition_id: "START" 表示设为初始态, "END" 表示设为结束态。
    """
    conn = _get_conn()
    cur = conn.execute("SELECT * FROM workflow_statuses WHERE id=?", (status_id,))
    row = cur.fetchone()
    if not row:
        return False

    try:
        defs = json.loads(row["status_definitions"] or "[]")
        if not isinstance(defs, list):
            defs = []
    except Exception:
        defs = []

    if enable:
        if definition_id == "START":
            # 只能有一个 START 状态，清除其他状态的 START
            conn.execute(
                "SELECT id, status_definitions FROM workflow_statuses WHERE scope_type=? AND scope_id=? AND scene=?",
                (row["scope_type"], row["scope_id"], row["scene"]),
            )
            for r in conn.fetchall():
                try:
                    old_defs = json.loads(r["status_definitions"] or "[]")
                except Exception:
                    old_defs = []
                if isinstance(old_defs, list) and "START" in old_defs and r["id"] != status_id:
                    new_defs = [d for d in old_defs if d != "START"]
                    conn.execute(
                        "UPDATE workflow_statuses SET status_definitions=? WHERE id=?",
                        (_norm_defs(new_defs), r["id"]),
                    )
        if definition_id not in defs:
            defs.append(definition_id)
    else:
        defs = [d for d in defs if d != definition_id]

    conn.execute(
        "UPDATE workflow_statuses SET status_definitions=? WHERE id=?",
        (_norm_defs(defs), status_id),
    )
    conn.commit()
    return True


def sort_statuses(status_ids: List[str]) -> bool:
    """重新排序状态。"""
    conn = _get_conn()
    for idx, sid in enumerate(status_ids):
        conn.execute(
            "UPDATE workflow_statuses SET pos=? WHERE id=?",
            (idx, sid),
        )
    conn.commit()
    return True


def update_flows(status_id: str, target_ids: List[str]) -> bool:
    """更新状态流转关系。"""
    conn = _get_conn()
    conn.execute("DELETE FROM workflow_flows WHERE source_status_id=?", (status_id,))
    for tid in target_ids:
        conn.execute(
            "INSERT OR IGNORE INTO workflow_flows (source_status_id, target_status_id) VALUES (?,?)",
            (status_id, str(tid)),
        )
    conn.commit()
    return True


def seed_default_statuses(scope_type: str, scope_id: str, scene: str) -> List[Dict[str, Any]]:
    """在范围内播种默认状态（首次访问时）。"""
    existing = list_statuses(scope_type, scope_id, scene)
    if existing:
        return existing

    defaults = [
        ("新建", "创建后进入的初始状态", ["START"]),
        ("处理中", "正在处理中", []),
        ("已完成", "处理完成", ["END"]),
    ]
    created = []
    for i, (name, remark, defs) in enumerate(defaults):
        sid = str(uuid.uuid4())
        conn = _get_conn()
        now = time.time()
        conn.execute(
            """INSERT INTO workflow_statuses
               (id, scope_type, scope_id, scene, name, remark, pos, status_definitions,
                internal, create_time, update_time, create_user)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                sid, scope_type, scope_id, scene, name, remark, i,
                _norm_defs(defs), 1, now, now, "system",
            ),
        )
        conn.commit()
        st = get_status(sid)
        if st:
            created.append(st)

    # 设置流转关系：新建->处理中->已完成
    if len(created) >= 3:
        update_flows(created[0]["id"], [created[1]["id"]])
        update_flows(created[1]["id"], [created[2]["id"]])
        update_flows(created[2]["id"], [])

    return created


__all__ = [
    "ensure_tables",
    "list_statuses",
    "get_status",
    "add_status",
    "update_status",
    "delete_status",
    "set_definition",
    "sort_statuses",
    "update_flows",
    "seed_default_statuses",
]
