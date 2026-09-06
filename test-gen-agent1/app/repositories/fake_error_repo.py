"""误报规则（错误注入）数据访问层（Repository 下沉 · 4 层对齐）。

承接原 `app.projects.fake_error_store` 的全部 SQLite 读写：
  - fake_error_rules 表建表（幂等）与补列
  - 列表 / 新增 / 更新 / 启用禁用 / 删除 / 启用计数

数据存储在 projects.db 的 fake_error_rules 表。本层是 fake_error 域数据访问
唯一权威出口，供 app.services.fake_error_service 消费；旧 store 门面委托本层。

前端字段约定（FakeTableListItem）：
  - name:      规则名称
  - type:      标签（多个标签以英文逗号连接；前端发送 string 或 string[]）
  - respType:  匹配类型（RESPONSE_HEADERS / RESPONSE_DATA / RESPONSE_CODE）
  - relation:  操作符（CONTAINS / NOT_CONTAINS / EQUALS / START_WITH / END_WITH）
  - expression: 匹配表达式
  - enable:    是否启用
  - projectId: 所属项目
"""
import sqlite3
import time
import uuid
from typing import Any, Dict, List

from app.core.database import Database
from app.logging_config import get_logger

logger = get_logger(__name__)

_RESP_TYPE_LABEL = {
    "RESPONSE_HEADERS": "Response Headers",
    "RESPONSE_DATA": "Response Data",
    "RESPONSE_CODE": "Response Code",
}

_RELATION_LABEL = {
    "CONTAINS": "包含",
    "NOT_CONTAINS": "不包含",
    "EQUALS": "等于",
    "START_WITH": "开始于",
    "END_WITH": "结束于",
}


def _get_conn() -> sqlite3.Connection:
    return Database.get_conn("projects.db")


def ensure_tables() -> None:
    """幂等建表 + 补列（权威 DDL，供 schema_registry / 迁移兜底引用）。"""
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
                type TEXT DEFAULT '',          -- 错误注入类型
                resp_type TEXT DEFAULT '',     -- 响应类型（RESPONSE_HEADERS/DATA/CODE）
                relation TEXT DEFAULT '',      -- 匹配关系（CONTAINS/EQUALS 等）
                expression TEXT DEFAULT ''     -- 匹配表达式
            )
        """)
        # 补列（幂等）：type/resp_type/relation/expression 与前端契约对齐
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


def _norm_type(tag_type) -> str:
    """归一化标签字段为逗号分隔字符串。"""
    if isinstance(tag_type, list):
        return ",".join(str(t) for t in tag_type if t is not None)
    return str(tag_type or "")


def _build_rule_result(resp_type: str, relation: str, expression: str) -> str:
    """构造前端展示用的 ruleResult。"""
    hdr = _RESP_TYPE_LABEL.get(resp_type, resp_type or "")
    rel = _RELATION_LABEL.get(relation, relation or "")
    parts = [p for p in (hdr, rel, expression) if p]
    return " ".join(parts)


def _row_to_item(row) -> Dict[str, Any]:
    """将 DB 行转换为前端期望的 FakeTableListItem 结构。

    兼容旧数据：旧记录只有 label/rule/rule_result 而无 type/resp_type 等新列时，
    尽量从 rule_result 或 rule 字段恢复基础字段。
    """
    keys = row.keys()

    def _get(name, default=""):
        return row[name] if name in keys else default

    tag_type = _get("type") or _get("label", "") or ""
    resp_type = _get("resp_type") or ""
    relation = _get("relation") or ""
    expression = _get("expression") or ""

    rule_result = _get("rule_result") or ""
    if not rule_result:
        rule_result = _build_rule_result(resp_type, relation, expression)

    return {
        "id": row["id"],
        "projectId": row["project_id"],
        "name": row["name"],
        "enable": bool(row["enable"]),
        "type": tag_type,
        "typeList": tag_type.split(",") if tag_type else [],
        "respType": resp_type,
        "relation": relation,
        "expression": expression,
        "ruleResult": rule_result,
        "createUser": row["create_user"],
        "updateTime": int((row["update_time"] or 0) * 1000),
    }


def list_rules(project_id: str = "") -> List[Dict[str, Any]]:
    conn = _get_conn()
    try:
        if project_id:
            cur = conn.execute(
                "SELECT * FROM fake_error_rules WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            )
        else:
            cur = conn.execute("SELECT * FROM fake_error_rules ORDER BY created_at DESC")
        return [_row_to_item(r) for r in cur.fetchall()]
    except Exception as e:
        logger.warning("list_rules 失败: %s", e)
        return []


def add_rules(items: List[Dict[str, Any]], project_id: str = "") -> List[Dict[str, Any]]:
    """新增误报规则。

    前端入参为 list[dict]，每项含 name/type/enable/respType/relation/expression/projectId。
    """
    conn = _get_conn()
    now = time.time()
    created = []
    try:
        for item in items:
            rid = item.get("id") or str(uuid.uuid4())
            pid = item.get("projectId", project_id) or project_id or ""
            name = item.get("name", "") or ""
            tag_type = _norm_type(item.get("type", ""))
            resp_type = str(item.get("respType", "") or "")
            relation = str(item.get("relation", "") or "")
            expression = str(item.get("expression", "") or "")
            enable = 1 if item.get("enable", True) else 0
            create_user = item.get("createUser", "") or "admin"
            rule_result = item.get("ruleResult", "") or _build_rule_result(resp_type, relation, expression)

            conn.execute(
                """
                INSERT OR REPLACE INTO fake_error_rules
                (id, project_id, name, enable, label, rule, rule_result, create_user,
                 type, resp_type, relation, expression, update_time, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    rid, pid, name, enable,
                    tag_type,            # label 兼容
                    expression,          # rule 兼容：存表达式
                    rule_result,         # rule_result：展示文本
                    create_user,
                    tag_type,            # type：标签（逗号分隔）
                    resp_type,           # resp_type
                    relation,            # relation
                    expression,          # expression
                    now, now,
                ),
            )
            row = _fetch_one(conn, rid)
            if row:
                created.append(_row_to_item(row))
        conn.commit()
    except Exception as e:
        logger.warning("add_rules 失败: %s", e)
    return created


def update_rules(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    conn = _get_conn()
    now = time.time()
    updated = []
    try:
        for item in items:
            rid = item.get("id")
            if not rid:
                continue
            name = item.get("name", "") or ""
            tag_type = _norm_type(item.get("type", ""))
            resp_type = str(item.get("respType", "") or "")
            relation = str(item.get("relation", "") or "")
            expression = str(item.get("expression", "") or "")
            enable = 1 if item.get("enable", True) else 0
            rule_result = item.get("ruleResult", "") or _build_rule_result(resp_type, relation, expression)

            conn.execute(
                """
                UPDATE fake_error_rules SET
                    name=?, enable=?, label=?, rule=?, rule_result=?,
                    type=?, resp_type=?, relation=?, expression=?, update_time=?
                WHERE id=?
                """,
                (
                    name, enable,
                    tag_type,          # label
                    expression,        # rule
                    rule_result,       # rule_result
                    tag_type,          # type
                    resp_type,
                    relation,
                    expression,
                    now,
                    rid,
                ),
            )
            row = _fetch_one(conn, rid)
            if row:
                updated.append(_row_to_item(row))
        conn.commit()
    except Exception as e:
        logger.warning("update_rules 失败: %s", e)
    return updated


def update_enable(ids: List[str], enable: bool) -> None:
    conn = _get_conn()
    now = time.time()
    try:
        for rid in ids:
            conn.execute(
                "UPDATE fake_error_rules SET enable=?, update_time=? WHERE id=?",
                (1 if enable else 0, now, rid),
            )
        conn.commit()
    finally:
        pass


def delete_rules(ids: List[str]) -> None:
    conn = _get_conn()
    try:
        for rid in ids:
            conn.execute("DELETE FROM fake_error_rules WHERE id=?", (rid,))
        conn.commit()
    finally:
        pass


def get_enabled_count(project_id: str = "") -> int:
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


def _fetch_one(conn, rid):
    cur = conn.execute("SELECT * FROM fake_error_rules WHERE id=?", (rid,))
    return cur.fetchone()


ensure_tables()
