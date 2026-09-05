# -*- coding: utf-8 -*-
"""app.cases.management.trash 子模块（自 management.py 拆出，行为不变）。"""

import json
from typing import Any, Dict, List

from app.cases.management._base import (
    CHANGE_DELETED,
    CHANGE_RESTORED,
    _gen_id,
    _get_base_case,
    _get_conn,
    _now,
    _record_change,
    logger,
)
from app.cases.management.mindmap import invalidate_mindmap_cache
from app.core.database import Database


def soft_delete_case(case_id: str, deleted_by: str = "",
                     reason: str = "") -> bool:
    """软删除用例：放入回收站。"""
    case = _get_base_case(case_id)
    if not case:
        return False
    # 写入回收站 + 更新用例状态置于同一事务，保证原子性
    with Database.transaction("testcases.db") as conn:
        conn.execute(
            """INSERT OR REPLACE INTO case_trash
               (id, case_id, case_data, deleted_at, deleted_by, reason)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (_gen_id(), case_id, json.dumps(case, ensure_ascii=False),
             _now(), deleted_by, reason),
        )
        conn.execute("UPDATE test_cases SET status = ?, updated_at = ? WHERE id = ?",
                     ("deprecated", _now(), case_id))
    try:
        _record_change(case_id, CHANGE_DELETED, operator=deleted_by, new_value=reason)
    except Exception as e:
        logger.warning("记录删除日志失败 [case=%s, err=%s]", case_id, e)
    invalidate_mindmap_cache()
    return True

def restore_case(case_id: str, operator: str = "") -> bool:
    """从回收站恢复用例。

    恢复状态与清空回收站记录置于同一事务，保证原子性。
    """
    conn = _get_conn()
    trash = conn.execute(
        "SELECT * FROM case_trash WHERE case_id = ?", (case_id,)
    ).fetchone()
    if not trash:
        return False
    with Database.transaction("testcases.db") as conn:
        # 恢复状态为草稿
        conn.execute("UPDATE test_cases SET status = ?, updated_at = ? WHERE id = ?",
                     ("draft", _now(), case_id))
        conn.execute("DELETE FROM case_trash WHERE case_id = ?", (case_id,))
    try:
        _record_change(case_id, CHANGE_RESTORED, operator=operator)
    except Exception as e:
        logger.warning("记录恢复日志失败 [case=%s, err=%s]", case_id, e)
    invalidate_mindmap_cache()
    return True

def list_trash_cases() -> List[Dict[str, Any]]:
    """列出回收站中的用例。"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM case_trash ORDER BY deleted_at DESC"
        ).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            try:
                item["case_data"] = json.loads(item.get("case_data") or "{}")
            except json.JSONDecodeError:
                item["case_data"] = {}
            result.append(item)
        return result
    finally:
        pass  # shared cached conn

def purge_case(case_id: str) -> bool:
    """从回收站彻底删除用例（从主表和回收站都删除）。

    先清理各关联表中的数据（置于同一事务），任一步失败即整体回滚，
    避免留下半删除的脏数据；全部清理成功后才硬删主表记录。
    """
    from app.repositories.case_repo import CaseRepo
    with Database.transaction("testcases.db") as conn:
        # 删除关联数据
        conn.execute("DELETE FROM case_relations WHERE case_id = ? OR related_case_id = ?",
                     (case_id, case_id))
        conn.execute("DELETE FROM case_dependencies WHERE case_id = ? OR depends_on = ?",
                     (case_id, case_id))
        conn.execute("DELETE FROM case_reviews WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM case_versions WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM case_change_logs WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM case_requirements WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM case_trash WHERE case_id = ?", (case_id,))
    invalidate_mindmap_cache()
    return CaseRepo.hard_delete(case_id)
