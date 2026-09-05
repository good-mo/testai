# app/repositories/task_repo.py
"""异步任务队列（tasks 表）数据访问层（4 层下沉）。

从 app/tasks/manager.py 下沉：原 TaskStore 直接在 manager 模块持有
tasks 表建表 + CRUD SQL，现收敛到本仓库——Router/Manager → Service/
Manager 调度 → Repository → DB。

承载 tga.db 的 tasks 表：
  - 任务状态机：pending → running → success/failed/cancelled
  - 跨进程原子认领（claim_next_pending / release_claim）
  - 进程重启恢复（recover_after_restart）
"""
import json
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.database import Database

# 任务状态（与 manager 侧保持一致）
PENDING = "pending"
RUNNING = "running"
SUCCESS = "success"
FAILED = "failed"
CANCELLED = "cancelled"

# 任务表所在逻辑库（统一路由至 tga.db）
_TASK_DB_NAME = "tasks.db"

_SCHEMA_VERSION_COLS = (
    ("handler_name", "TEXT DEFAULT ''"),
    ("handler_args", "TEXT DEFAULT '[]'"),
    ("handler_kwargs", "TEXT DEFAULT '{}'"),
    ("restartable", "INTEGER DEFAULT 0"),
    ("claimed_by", "TEXT DEFAULT ''"),
)


def _get_conn() -> sqlite3.Connection:
    return Database.get_conn(_TASK_DB_NAME)


def _decode(row: sqlite3.Row) -> Dict[str, Any]:
    """DB 行 → dict，result 字段自动反序列化。"""
    data = dict(row)
    if data.get("result"):
        try:
            data["result"] = json.loads(data["result"])
        except (TypeError, ValueError):
            pass
    return data


def ensure_table() -> None:
    """幂等建表 + 补列（权威 DDL，供 schema_registry 引用）。"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at REAL,
            started_at REAL,
            finished_at REAL,
            result TEXT,
            error TEXT,
            coro_name TEXT DEFAULT '',
            args TEXT DEFAULT '[]',
            handler_name TEXT DEFAULT '',
            handler_args TEXT DEFAULT '[]',
            handler_kwargs TEXT DEFAULT '{}',
            restartable INTEGER DEFAULT 0,
            claimed_by TEXT DEFAULT ''
        )
    """)
    conn.commit()
    # 补列（幂等）：旧版本表缺列时增量 ALTER
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    for col, ddl in _SCHEMA_VERSION_COLS:
        if col not in cols:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {ddl}")
    conn.commit()


ensure_table()


def save_task(
    task_id: str,
    status: str = PENDING,
    coro_name: str = "",
    args: list = None,
    handler_name: str = "",
    handler_args: list = None,
    handler_kwargs: dict = None,
    restartable: bool = False,
    created_at: float = None,
) -> None:
    """保存（INSERT OR REPLACE）一条任务记录。"""
    conn = _get_conn()
    now = created_at or time.time()
    conn.execute(
        """INSERT OR REPLACE INTO tasks
           (task_id, status, created_at, coro_name, args,
            handler_name, handler_args, handler_kwargs, restartable)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            task_id, status, now,
            coro_name,
            json.dumps(args or [], ensure_ascii=False, default=str),
            handler_name,
            json.dumps(handler_args or [], ensure_ascii=False, default=str),
            json.dumps(handler_kwargs or {}, ensure_ascii=False, default=str),
            1 if restartable else 0,
        ),
    )
    conn.commit()


def update_status(task_id: str, status: str, **kwargs) -> None:
    """更新任务状态（字段白名单）。"""
    allowed = ("started_at", "finished_at", "result", "error", "claimed_by")
    conn = _get_conn()
    fields = ["status = ?"]
    values: list = [status]
    for key in allowed:
        if key in kwargs:
            fields.append(f"{key} = ?")
            value = kwargs[key]
            if key == "result":
                value = json.dumps(value, ensure_ascii=False, default=str)
            values.append(value)
    values.append(task_id)
    conn.execute(
        f"UPDATE tasks SET {', '.join(fields)} WHERE task_id = ?",
        values,
    )
    conn.commit()


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """按 ID 读取任务。"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
    ).fetchone()
    return _decode(row) if row else None


def list_recent(limit: int = 50) -> List[Dict[str, Any]]:
    """获取最近任务列表（created_at 降序）。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [_decode(r) for r in rows]


def list_pending() -> List[Dict[str, Any]]:
    """返回所有 pending 状态任务。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE status = ? ORDER BY created_at ASC",
        (PENDING,),
    ).fetchall()
    return [_decode(r) for r in rows]


def delete_task(task_id: str) -> bool:
    """物理删除任务记录。"""
    if not task_id:
        return False
    conn = _get_conn()
    cur = conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
    conn.commit()
    return cur.rowcount > 0


def claim_next_pending(worker_id: str = "") -> Optional[Dict[str, Any]]:
    """原子认领一个 pending 任务（跨进程安全）。"""
    conn = _get_conn()
    row = conn.execute(
        """UPDATE tasks SET claimed_by = ?, started_at = ?
           WHERE task_id = (
               SELECT task_id FROM tasks
               WHERE status = ? AND (claimed_by = '' OR claimed_by IS NULL)
               ORDER BY created_at ASC LIMIT 1
           )
           RETURNING *""",
        (worker_id, time.time(), PENDING),
    ).fetchone()
    if row:
        conn.commit()
        return _decode(row)
    return None


def release_claim(task_id: str) -> None:
    """释放任务认领（恢复为未认领的 pending 状态）。"""
    conn = _get_conn()
    conn.execute(
        "UPDATE tasks SET claimed_by = '' WHERE task_id = ? AND status = ?",
        (task_id, PENDING),
    )
    conn.commit()


def recover_after_restart() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """重启后任务恢复。返回 (restartable_tasks, abandoned_tasks)。"""
    conn = _get_conn()
    # 1. running 状态任务：无法恢复，标记 failed。
    running_rows = conn.execute(
        "SELECT * FROM tasks WHERE status = ?", (RUNNING,)
    ).fetchall()
    if running_rows:
        conn.execute(
            "UPDATE tasks SET status = ?, finished_at = ?, error = ?, "
            "claimed_by = '' WHERE status = ?",
            (FAILED, time.time(),
             "进程重启，运行中的任务已被中断", RUNNING),
        )

    # 2. pending + restartable=1：保留 pending，等新 worker 认领。
    restartable_rows = conn.execute(
        "SELECT * FROM tasks WHERE status = ? AND restartable = 1",
        (PENDING,),
    ).fetchall()

    # 3. pending + restartable=0：无法重建，标记 failed。
    abandoned_rows = conn.execute(
        "SELECT * FROM tasks WHERE status = ? AND "
        "(restartable IS NULL OR restartable = 0)",
        (PENDING,),
    ).fetchall()
    if abandoned_rows:
        conn.execute(
            "UPDATE tasks SET status = ?, finished_at = ?, error = ?, "
            "claimed_by = '' WHERE status = ? AND "
            "(restartable IS NULL OR restartable = 0)",
            (FAILED, time.time(), "进程重启，任务未完成（无法恢复）",
             PENDING),
        )
    conn.commit()
    return (
        [_decode(r) for r in restartable_rows],
        [_decode(r) for r in abandoned_rows]
        + [_decode(r) for r in running_rows],
    )


def recover_pending() -> List[Dict[str, Any]]:
    """返回 pending/running 任务（deprecated 兼容）。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM tasks WHERE status IN (?, ?)",
        (PENDING, RUNNING),
    ).fetchall()
    return [_decode(r) for r in rows]


def mark_abandoned() -> List[Dict[str, Any]]:
    """将不可恢复残留任务标记为 failed（deprecated 兼容）。"""
    _, abandoned = recover_after_restart()
    return abandoned


__all__ = [
    "PENDING", "RUNNING", "SUCCESS", "FAILED", "CANCELLED",
    "ensure_table", "save_task", "update_status", "get_task",
    "list_recent", "list_pending", "delete_task",
    "claim_next_pending", "release_claim",
    "recover_after_restart", "recover_pending", "mark_abandoned",
]
