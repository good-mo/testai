# app/repositories/test_plan_repo.py
"""测试计划数据访问层（Phase 3 重构 · 4 层对齐）。

本层是 test_plan 域**唯一权威**：同时持有表结构 DDL 与数据访问 SQL。
- 表结构（test_plans / test_plan_cases / test_plan_modules /
  test_plan_schedules / dashboard_layouts）由本模块 _init_db 幂等建表，
  作为 schema_registry 单一权威来源。
- 旧 app.test_plan.store 兼容门面已移除，数据访问统一收敛至此层。

纯数据访问（上述表的 CRUD / 统计 / 定时配置）均在仓库内直连 SQL。
"""
import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.database import Database


def _decode_tags(raw) -> List[str]:
    """解析 tags 字段，兼容 NULL/JSON 字符串/已解析列表。"""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t) for t in raw]
    try:
        parsed = json.loads(raw)
        return [str(t) for t in parsed] if isinstance(parsed, list) else []
    except Exception:
        return [str(raw)] if raw else []


def _plan_from_row(row) -> Dict[str, Any]:
    """裸行 → 归一化输出。"""
    plan = dict(row)
    plan["metadata"] = json.loads(plan.get("metadata", "{}"))
    plan["tags"] = _decode_tags(plan.get("tags"))
    plan["pass_threshold"] = plan.get("pass_threshold", 100) or 100
    plan["test_planning"] = bool(plan.get("test_planning", 0))
    plan["auto_update_status"] = bool(plan.get("auto_update_status", 0))
    plan["repeat_case"] = bool(plan.get("repeat_case", 0))
    return plan


DB_NAME = "test_plans.db"


def _get_conn() -> sqlite3.Connection:
    """获取 test_plans.db 连接（统一使用 Database 连接池）。"""
    return Database.get_conn(DB_NAME)


def _init_db() -> None:
    """幂等建表 + 兼容补列（权威 DDL，供 schema_registry / 迁移兜底引用）。"""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_plans (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'prepared',
                priority TEXT DEFAULT 'P2',
                module_id TEXT DEFAULT 'root',
                project_id TEXT DEFAULT '',
                created_by TEXT DEFAULT 'admin',
                created_at REAL,
                updated_at REAL,
                start_time REAL DEFAULT 0,
                end_time REAL DEFAULT 0,
                execution_rate REAL DEFAULT 0,
                pass_rate REAL DEFAULT 0,
                tags TEXT DEFAULT '[]',
                pass_threshold REAL DEFAULT 100,
                test_planning INTEGER DEFAULT 0,
                auto_update_status INTEGER DEFAULT 0,
                repeat_case INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                type TEXT DEFAULT 'TEST_PLAN',
                group_id TEXT DEFAULT 'NONE'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_plan_cases (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                case_type TEXT DEFAULT 'functional',
                status TEXT DEFAULT 'pending',
                execute_time REAL DEFAULT 0,
                created_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_plan_modules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                parent_id TEXT DEFAULT 'root',
                project_id TEXT DEFAULT '',
                pos INTEGER DEFAULT 0,
                created_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_plan_schedules (
                plan_id TEXT PRIMARY KEY,
                cron TEXT NOT NULL DEFAULT '',
                enable INTEGER DEFAULT 1,
                run_mode TEXT DEFAULT 'SERIAL',
                project_id TEXT DEFAULT '',
                updated_at REAL,
                created_at REAL
            )
        """)
        # 兼容旧表：缺列则补充
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(test_plans)").fetchall()]
            alter_specs = [
                ("project_id", "TEXT DEFAULT ''"),
                ("tags", "TEXT DEFAULT '[]'"),
                ("pass_threshold", "REAL DEFAULT 100"),
                ("test_planning", "INTEGER DEFAULT 0"),
                ("auto_update_status", "INTEGER DEFAULT 0"),
                ("repeat_case", "INTEGER DEFAULT 0"),
                ("type", "TEXT DEFAULT 'TEST_PLAN'"),
                ("group_id", "TEXT DEFAULT 'NONE'"),
            ]
            for col, ddl in alter_specs:
                if col not in cols:
                    conn.execute(f"ALTER TABLE test_plans ADD COLUMN {col} {ddl}")
        except Exception:
            pass
        conn.commit()
    finally:
        pass


_init_db()


class TestPlanRepo:
    """测试计划数据访问仓库。

    直接以 test_plans.db（统一路由 tga.db）落库，由 Service 层调用，
    schema_registry 收录其表结构 DDL 为权威来源。
    """

    db_name = DB_NAME

    @classmethod
    def _conn(cls) -> sqlite3.Connection:
        """获取 test_plans.db 连接（表已由模块导入时 _init_db 建好）。"""
        return _get_conn()

    # ── 计划 CRUD ────────────────────────────────────────
    @classmethod
    def create_plan(cls, name: str, description: str = "", priority: str = "P2",
                    module_id: str = "root", project_id: str = "",
                    created_by: str = "admin", **kwargs) -> Dict[str, Any]:
        plan_id = str(uuid.uuid4())
        now = time.time()
        tags_json = json.dumps(kwargs.get("tags") or [], ensure_ascii=False)
        start_time = kwargs.get("start_time", 0)
        end_time = kwargs.get("end_time", 0)
        pass_threshold = kwargs.get("pass_threshold", 100)
        test_planning = 1 if kwargs.get("test_planning", False) else 0
        auto_update_status = 1 if kwargs.get("auto_update_status", False) else 0
        repeat_case = 1 if kwargs.get("repeat_case", False) else 0
        plan_type = kwargs.get("type") or kwargs.get("plan_type") or "TEST_PLAN"
        group_id = kwargs.get("groupId") or kwargs.get("group_id") or "NONE"

        conn = cls._conn()
        conn.execute(
            """INSERT INTO test_plans (id, name, description, priority, module_id,
               project_id, created_by, created_at, updated_at,
               start_time, end_time, tags, pass_threshold,
               test_planning, auto_update_status, repeat_case, type, group_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (plan_id, name, description, priority, module_id, project_id,
             created_by, now, now, start_time or 0, end_time or 0, tags_json,
             pass_threshold, test_planning, auto_update_status, repeat_case,
             plan_type, group_id),
        )
        return cls.get_plan(plan_id) or {}

    @classmethod
    def get_plan(cls, plan_id: str) -> Optional[Dict[str, Any]]:
        conn = cls._conn()
        cursor = conn.execute("SELECT * FROM test_plans WHERE id = ?", (plan_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return _plan_from_row(row)

    @classmethod
    def list_plans(cls, keyword: str = "", status: str = "",
                   project_id: str = "", module_ids: Optional[List[str]] = None,
                   limit: int = 100, offset: int = 0, **kwargs) -> List[Dict[str, Any]]:
        query = "SELECT * FROM test_plans WHERE 1=1"
        params = []
        if keyword:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if status:
            query += " AND status = ?"
            params.append(status)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if module_ids:
            placeholders = ",".join(["?"] * len(module_ids))
            query += f" AND module_id IN ({placeholders})"
            params.extend(module_ids)
        plan_type = kwargs.get("type") or kwargs.get("plan_type") or ""
        if plan_type and plan_type.upper() not in ("ALL", ""):
            query += " AND type = ?"
            params.append(plan_type.upper())
        group_id = kwargs.get("groupId") or kwargs.get("group_id") or ""
        if group_id and group_id != "NONE":
            query += " AND group_id = ?"
            params.append(group_id)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        conn = cls._conn()
        cursor = conn.execute(query, params)
        return [_plan_from_row(row) for row in cursor.fetchall()]

    @classmethod
    def count_plans(cls, keyword: str = "", status: str = "",
                    project_id: str = "", module_ids: Optional[List[str]] = None,
                    **kwargs) -> int:
        query = "SELECT COUNT(*) FROM test_plans WHERE 1=1"
        params = []
        if keyword:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if status:
            query += " AND status = ?"
            params.append(status)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if module_ids:
            placeholders = ",".join(["?"] * len(module_ids))
            query += f" AND module_id IN ({placeholders})"
            params.extend(module_ids)
        plan_type = kwargs.get("type") or kwargs.get("plan_type") or ""
        if plan_type and plan_type.upper() not in ("ALL", ""):
            query += " AND type = ?"
            params.append(plan_type.upper())
        group_id = kwargs.get("groupId") or kwargs.get("group_id") or ""
        if group_id and group_id != "NONE":
            query += " AND group_id = ?"
            params.append(group_id)
        conn = cls._conn()
        cursor = conn.execute(query, params)
        return cursor.fetchone()[0]

    @classmethod
    def update_plan(cls, plan_id: str, **fields) -> Optional[Dict[str, Any]]:
        allowed = {"name", "description", "status", "priority", "module_id",
                   "start_time", "end_time", "execution_rate", "pass_rate",
                   "tags", "pass_threshold", "test_planning",
                   "auto_update_status", "repeat_case", "type"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return cls.get_plan(plan_id)
        if "tags" in updates:
            updates["tags"] = json.dumps(updates["tags"] or [], ensure_ascii=False)
        for bool_key in ("test_planning", "auto_update_status", "repeat_case"):
            if bool_key in updates:
                updates[bool_key] = 1 if updates[bool_key] else 0
        if updates.get("pass_threshold") is None:
            updates["pass_threshold"] = 100
        updates["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [plan_id]
        conn = cls._conn()
        conn.execute(f"UPDATE test_plans SET {set_clause} WHERE id = ?", values)
        return cls.get_plan(plan_id)

    @classmethod
    def delete_plan(cls, plan_id: str) -> bool:
        conn = cls._conn()
        conn.execute("DELETE FROM test_plan_cases WHERE plan_id = ?", (plan_id,))
        cursor = conn.execute("DELETE FROM test_plans WHERE id = ?", (plan_id,))
        return cursor.rowcount > 0

    @classmethod
    def archive_plan(cls, plan_id: str) -> bool:
        plan = cls.update_plan(plan_id, status="archived")
        return plan is not None

    # ── 计划用例关联 ────────────────────────────────────
    @classmethod
    def add_plan_case(cls, plan_id: str, case_id: str,
                      case_type: str = "functional") -> Dict[str, Any]:
        rel_id = str(uuid.uuid4())
        now = time.time()
        conn = cls._conn()
        conn.execute(
            """INSERT INTO test_plan_cases (id, plan_id, case_id, case_type, status, created_at)
               VALUES (?, ?, ?, ?, 'pending', ?)""",
            (rel_id, plan_id, case_id, case_type, now),
        )
        return {"id": rel_id, "plan_id": plan_id, "case_id": case_id,
                "case_type": case_type, "status": "pending"}

    @classmethod
    def list_plan_cases(cls, plan_id: str) -> List[Dict[str, Any]]:
        conn = cls._conn()
        cursor = conn.execute(
            "SELECT * FROM test_plan_cases WHERE plan_id = ?", (plan_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    @classmethod
    def update_plan_case_status(cls, rel_id: str, status: str) -> bool:
        conn = cls._conn()
        cursor = conn.execute(
            "UPDATE test_plan_cases SET status = ? WHERE id = ?",
            (status, rel_id),
        )
        return cursor.rowcount > 0

    @classmethod
    def remove_plan_case(cls, rel_id: str) -> bool:
        conn = cls._conn()
        cursor = conn.execute("DELETE FROM test_plan_cases WHERE id = ?", (rel_id,))
        conn.commit()
        return cursor.rowcount > 0

    @classmethod
    def update_rel_pos(cls, rel_id: str, pos: int) -> bool:
        """更新计划关联用例位置（用 execute_time 列占位存储 sort 顺序）。"""
        conn = cls._conn()
        cursor = conn.execute(
            "UPDATE test_plan_cases SET execute_time = ? WHERE id = ?",
            (float(pos), rel_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    # ── 统计 ────────────────────────────────────────────
    @classmethod
    def get_plan_statistics(cls, plan_id: str) -> Dict[str, Any]:
        conn = cls._conn()
        row = conn.execute(
            "SELECT "
            "COUNT(*) AS total, "
            "SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) AS passed, "
            "SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed, "
            "SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) AS blocked, "
            "SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending "
            "FROM test_plan_cases WHERE plan_id = ?", (plan_id,)
        ).fetchone()
        type_row = conn.execute(
            "SELECT case_type, COUNT(*) AS cnt "
            "FROM test_plan_cases WHERE plan_id = ? "
            "GROUP BY case_type", (plan_id,)
        ).fetchall()
        total = row["total"] if row and row["total"] else 0
        passed = row["passed"] if row and row["passed"] else 0
        failed = row["failed"] if row and row["failed"] else 0
        blocked = row["blocked"] if row and row["blocked"] else 0
        pending = row["pending"] if row and row["pending"] else 0
        executed = total - pending
        type_counts = {r["case_type"]: r["cnt"] for r in type_row}
        functional_cnt = type_counts.get("functional", 0)
        api_cnt = type_counts.get("api", 0) + type_counts.get("api_case", 0) + type_counts.get("API", 0)
        scenario_cnt = type_counts.get("scenario", 0) + type_counts.get("api_scenario", 0) + type_counts.get("SCENARIO", 0)
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "pending": pending,
            "executionRate": round((executed / total * 100) if total else 0, 1),
            "passRate": round((passed / total * 100) if total else 0, 1),
            "executeRate": round((executed / total * 100) if total else 0, 1),
            "successCount": passed,
            "errorCount": failed,
            "fakeErrorCount": 0,
            "blockCount": blocked,
            "pendingCount": pending,
            "caseTotal": total,
            "functionalCaseCount": functional_cnt,
            "apiCaseCount": api_cnt,
            "apiScenarioCount": scenario_cnt,
        }

    @classmethod
    def get_plans_statistics(cls, plan_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        if not plan_ids:
            return {}
        placeholders = ",".join(["?"] * len(plan_ids))
        conn = cls._conn()
        rows = conn.execute(
            f"SELECT plan_id, "
            f"COUNT(*) AS total, "
            f"SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) AS passed, "
            f"SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed, "
            f"SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) AS blocked, "
            f"SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending "
            f"FROM test_plan_cases WHERE plan_id IN ({placeholders}) "
            f"GROUP BY plan_id", plan_ids,
        ).fetchall()
        type_rows = conn.execute(
            f"SELECT plan_id, case_type, COUNT(*) AS cnt "
            f"FROM test_plan_cases WHERE plan_id IN ({placeholders}) "
            f"GROUP BY plan_id, case_type", plan_ids,
        ).fetchall()
        result = {}
        for r in rows:
            total = r["total"] or 0
            passed = r["passed"] or 0
            failed = r["failed"] or 0
            blocked = r["blocked"] or 0
            pending = r["pending"] or 0
            executed = total - pending
            result[r["plan_id"]] = {
                "total": total,
                "passed": passed,
                "failed": failed,
                "blocked": blocked,
                "pending": pending,
                "executionRate": round((executed / total * 100) if total else 0, 1),
                "passRate": round((passed / total * 100) if total else 0, 1),
                "executeRate": round((executed / total * 100) if total else 0, 1),
                "successCount": passed,
                "errorCount": failed,
                "fakeErrorCount": 0,
                "blockCount": blocked,
                "pendingCount": pending,
                "caseTotal": total,
            }
        for tr in type_rows:
            pid = tr["plan_id"]
            if pid not in result:
                continue
            ct = tr["case_type"]
            if ct in ("functional", "FUNCTIONAL"):
                result[pid]["functionalCaseCount"] = result[pid].get("functionalCaseCount", 0) + tr["cnt"]
            elif ct in ("api", "api_case", "API"):
                result[pid]["apiCaseCount"] = result[pid].get("apiCaseCount", 0) + tr["cnt"]
            elif ct in ("scenario", "api_scenario", "SCENARIO"):
                result[pid]["apiScenarioCount"] = result[pid].get("apiScenarioCount", 0) + tr["cnt"]
            else:
                result[pid]["functionalCaseCount"] = result[pid].get("functionalCaseCount", 0) + tr["cnt"]
        for pid in plan_ids:
            if pid in result:
                result[pid].setdefault("functionalCaseCount", 0)
                result[pid].setdefault("apiCaseCount", 0)
                result[pid].setdefault("apiScenarioCount", 0)
        return result

    # ── 模块 ────────────────────────────────────────────
    @classmethod
    def create_module(cls, name: str, parent_id: str = "root",
                      project_id: str = "") -> Dict[str, Any]:
        module_id = str(uuid.uuid4())
        conn = cls._conn()
        conn.execute(
            """INSERT INTO test_plan_modules (id, name, parent_id, created_at)
               VALUES (?, ?, ?, ?)""",
            (module_id, name, parent_id, time.time()),
        )
        return {"id": module_id, "name": name, "parent_id": parent_id}

    @classmethod
    def list_modules(cls) -> List[Dict[str, Any]]:
        conn = cls._conn()
        cursor = conn.execute("SELECT * FROM test_plan_modules ORDER BY pos")
        return [dict(row) for row in cursor.fetchall()]

    @classmethod
    def update_module(cls, module_id: str, name: str = "") -> bool:
        conn = cls._conn()
        cursor = conn.execute(
            "UPDATE test_plan_modules SET name = ? WHERE id = ?",
            (name, module_id),
        )
        return cursor.rowcount > 0

    @classmethod
    def delete_module(cls, module_id: str) -> bool:
        conn = cls._conn()
        cursor = conn.execute("DELETE FROM test_plan_modules WHERE id = ?", (module_id,))
        return cursor.rowcount > 0

    @classmethod
    def move_module(cls, drag_node_id: str, drop_node_id: str,
                    drop_position: int = 0) -> bool:
        """移动测试计划模块到目标位置（改 parent_id）。

        drop_position 语义与前端 MoveModules / 其它域 move_module 对齐：
          -1  放到 drop 节点之前（同级）
           0  放到 drop 节点内部（成为其子节点）
           1  放到 drop 节点之后（同级）

        该域模块树仅按 parent_id 层级构建（不依赖 pos 排序），故移动只需
        重挂 parent_id；同级场景统一挂在 drop 的父模块之下即可。
        兼容 drop 节点为 root / 不存在：整树无目标则挂回 root。
        """
        conn = cls._conn()
        drag = conn.execute(
            "SELECT * FROM test_plan_modules WHERE id = ?", (drag_node_id,)
        ).fetchone()
        if not drag:
            return False

        def _target_parent() -> str:
            # drop_position==0：成为 drop 的子节点
            if drop_position == 0 and drop_node_id and drop_node_id != "root":
                drop = conn.execute(
                    "SELECT * FROM test_plan_modules WHERE id = ?", (drop_node_id,)
                ).fetchone()
                if not drop:
                    return "root"
                if drop["id"] == drag_node_id:  # 自身不入子级
                    return drag["parent_id"] or "root"
                return drop["id"]
            # 同级：挂在 drop 的父模块之下；drop 为 root/不存在则挂 root
            if not drop_node_id or drop_node_id == "root":
                return "root"
            drop = conn.execute(
                "SELECT * FROM test_plan_modules WHERE id = ?", (drop_node_id,)
            ).fetchone()
            if not drop:
                return "root"
            return drop["parent_id"] or "root"

        new_parent = _target_parent()
        conn.execute(
            "UPDATE test_plan_modules SET parent_id = ? WHERE id = ?",
            (new_parent, drag_node_id),
        )
        return True

    @classmethod
    def count_plans_by_module(cls, project_id: str = "") -> Dict[str, int]:
        conn = cls._conn()
        if project_id:
            total = conn.execute(
                "SELECT COUNT(*) FROM test_plans WHERE project_id = ?", [project_id]
            ).fetchone()[0]
        else:
            total = conn.execute("SELECT COUNT(*) FROM test_plans").fetchone()[0]
        if project_id:
            rows = conn.execute(
                "SELECT module_id, COUNT(*) as cnt FROM test_plans WHERE project_id = ? GROUP BY module_id",
                [project_id],
            ).fetchall()
            module_ids = [r["id"] for r in conn.execute(
                "SELECT id FROM test_plan_modules WHERE project_id = ?", [project_id]
            ).fetchall()]
        else:
            rows = conn.execute(
                "SELECT module_id, COUNT(*) as cnt FROM test_plans GROUP BY module_id"
            ).fetchall()
            module_ids = [r["id"] for r in conn.execute(
                "SELECT id FROM test_plan_modules"
            ).fetchall()]
        result = {"all": total, "root": 0}
        for r in rows:
            result[r["module_id"]] = r["cnt"]
        for mid in module_ids:
            result.setdefault(mid, 0)
        return result

    # ── 定时任务配置 ─────────────────────────────────
    @classmethod
    def save_schedule(cls, plan_id: str, cron: str = "", enable: bool = True,
                      run_mode: str = "SERIAL", project_id: str = "") -> Dict[str, Any]:
        plan_id = plan_id or ""
        if not plan_id:
            return {}
        now = time.time()
        conn = cls._conn()
        conn.execute("""
            INSERT INTO test_plan_schedules (plan_id, cron, enable, run_mode, project_id, updated_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(plan_id) DO UPDATE SET
                cron=excluded.cron,
                enable=excluded.enable,
                run_mode=excluded.run_mode,
                project_id=excluded.project_id,
                updated_at=excluded.updated_at
        """, (plan_id, cron or "", 1 if enable else 0, run_mode or "SERIAL",
              project_id or "", now, now))
        return cls.get_schedule(plan_id) or {}

    @classmethod
    def get_schedule(cls, plan_id: str) -> Optional[Dict[str, Any]]:
        if not plan_id:
            return None
        conn = cls._conn()
        row = conn.execute(
            "SELECT plan_id, cron, enable, run_mode, project_id, updated_at, created_at "
            "FROM test_plan_schedules WHERE plan_id = ?", (plan_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        return {
            "plan_id": d["plan_id"],
            "cron": d["cron"] or "",
            "enable": bool(d["enable"]),
            "run_mode": d["run_mode"] or "SERIAL",
            "project_id": d["project_id"] or "",
            "updated_at": d["updated_at"] or 0,
        }

    @classmethod
    def get_schedules(cls, plan_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        plan_ids = [pid for pid in (plan_ids or []) if pid]
        if not plan_ids:
            return {}
        placeholders = ",".join(["?"] * len(plan_ids))
        conn = cls._conn()
        rows = conn.execute(
            f"SELECT plan_id, cron, enable, run_mode, project_id, updated_at "
            f"FROM test_plan_schedules WHERE plan_id IN ({placeholders})",
            plan_ids,
        ).fetchall()
        result = {}
        for r in rows:
            d = dict(r)
            result[d["plan_id"]] = {
                "plan_id": d["plan_id"],
                "cron": d["cron"] or "",
                "enable": bool(d["enable"]),
                "run_mode": d["run_mode"] or "SERIAL",
                "project_id": d["project_id"] or "",
                "updated_at": d["updated_at"] or 0,
            }
        return result

    @classmethod
    def delete_schedule(cls, plan_id: str) -> bool:
        if not plan_id:
            return False
        conn = cls._conn()
        cur = conn.execute("DELETE FROM test_plan_schedules WHERE plan_id = ?", (plan_id,))
        return cur.rowcount > 0

    # ── Dashboard 布局 ─────────────────────────────────
    @classmethod
    def _ensure_dashboard_layout_table(cls) -> None:
        conn = cls._conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_layouts (
                    org_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    layout TEXT NOT NULL DEFAULT '[]',
                    updated_at REAL,
                    PRIMARY KEY (org_id, user_id)
                )
            """)
        except Exception:
            pass

    @classmethod
    def save_dashboard_layout(cls, org_id: str, user_id: str, layout: list) -> None:
        cls._ensure_dashboard_layout_table()
        try:
            conn = cls._conn()
            conn.execute("""
                INSERT INTO dashboard_layouts (org_id, user_id, layout, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(org_id, user_id) DO UPDATE SET
                    layout=excluded.layout, updated_at=excluded.updated_at
            """, (org_id or "", user_id or "", json.dumps(layout, ensure_ascii=False), time.time()))
        except Exception:
            pass

    @classmethod
    def load_dashboard_layout(cls, org_id: str, user_id: str):
        cls._ensure_dashboard_layout_table()
        try:
            conn = cls._conn()
            row = conn.execute(
                "SELECT layout FROM dashboard_layouts WHERE org_id=? AND user_id=?",
                (org_id or "", user_id or ""),
            ).fetchone()
            if row and row["layout"]:
                return json.loads(row["layout"])
        except Exception:
            pass
        return None


# 兼容类方法调用（部分上层代码按类使用）
test_plan_repo = TestPlanRepo
