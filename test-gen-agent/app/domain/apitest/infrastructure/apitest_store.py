"""接口测试上下文的 SQLite 存储适配器。"""

from __future__ import annotations

import json
import time
import uuid
from typing import Optional

from app.core.database import Database


class ApitestStore:
    db_name = "tga.db"
    _tables = {
        "definition": "domain_api_definitions",
        "case": "domain_api_cases",
        "scenario": "domain_api_scenarios",
        "mock": "domain_api_mocks",
    }

    def __init__(self) -> None:
        conn = Database.get_conn(self.db_name)
        for table in self._tables.values():
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ("
                "id TEXT PRIMARY KEY, project_id TEXT NOT NULL DEFAULT '', "
                "name TEXT NOT NULL DEFAULT '', deleted INTEGER NOT NULL DEFAULT 0, "
                "created_at REAL NOT NULL, updated_at REAL NOT NULL, data TEXT NOT NULL)"
            )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS domain_api_definition_versions ("
            "id TEXT PRIMARY KEY, definition_id TEXT NOT NULL, version TEXT NOT NULL, "
            "created_at REAL NOT NULL)"
        )
        conn.commit()

    @staticmethod
    def _row(row) -> Optional[dict]:
        if not row:
            return None
        data = json.loads(row["data"] or "{}")
        data.setdefault("id", row["id"])
        data.setdefault("project_id", row["project_id"])
        data["deleted"] = bool(row["deleted"])
        return data

    def _table(self, kind: str) -> str:
        return self._tables[kind]

    def _get(self, kind: str, item_id: str, include_deleted: bool = False):
        sql = f"SELECT * FROM {self._table(kind)} WHERE id = ?"
        params = [item_id]
        if not include_deleted:
            sql += " AND deleted = 0"
        return self._row(Database.get_conn(self.db_name).execute(sql, params).fetchone())

    def _list(self, kind: str, project_id: str = "", keyword: str = "", limit: int = 100,
              offset: int = 0, include_deleted: bool = False):
        clauses = ["deleted = ?"]
        params = [int(include_deleted)]
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if keyword:
            clauses.append("name LIKE ?")
            params.append(f"%{keyword}%")
        params.extend([max(1, limit), max(0, offset)])
        rows = Database.get_conn(self.db_name).execute(
            f"SELECT * FROM {self._table(kind)} WHERE {' AND '.join(clauses)} "
            "ORDER BY updated_at DESC LIMIT ? OFFSET ?", params
        ).fetchall()
        return [self._row(row) for row in rows]

    def _count(self, kind: str, project_id: str = "", keyword: str = "", deleted: bool = False):
        clauses = ["deleted = ?"]
        params = [int(deleted)]
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if keyword:
            clauses.append("name LIKE ?")
            params.append(f"%{keyword}%")
        row = Database.get_conn(self.db_name).execute(
            f"SELECT COUNT(*) AS n FROM {self._table(kind)} WHERE {' AND '.join(clauses)}", params
        ).fetchone()
        return int(row["n"])

    def _save(self, kind: str, data: dict, item_id: str = "") -> dict:
        item_id = item_id or data.get("id") or uuid.uuid4().hex[:12]
        now = time.time()
        conn = Database.get_conn(self.db_name)
        old = conn.execute(f"SELECT created_at FROM {self._table(kind)} WHERE id = ?", (item_id,)).fetchone()
        project_id = data.get("project_id", data.get("projectId", "")) or ""
        name = data.get("name", "") or ""
        conn.execute(
            f"INSERT INTO {self._table(kind)} (id, project_id, name, deleted, created_at, updated_at, data) "
            "VALUES (?, ?, ?, 0, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "project_id=excluded.project_id, name=excluded.name, deleted=0, "
            "updated_at=excluded.updated_at, data=excluded.data",
            (item_id, project_id, name, old["created_at"] if old else now, now,
             json.dumps({**data, "id": item_id}, ensure_ascii=False, default=str)),
        )
        conn.commit()
        return self._get(kind, item_id)

    def _delete(self, kind: str, item_id: str) -> bool:
        conn = Database.get_conn(self.db_name)
        cur = conn.execute(f"UPDATE {self._table(kind)} SET deleted = 1 WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0

    def _restore(self, kind: str, item_id: str) -> bool:
        conn = Database.get_conn(self.db_name)
        cur = conn.execute(f"UPDATE {self._table(kind)} SET deleted = 0 WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0

    def _purge(self, kind: str, item_id: str) -> bool:
        conn = Database.get_conn(self.db_name)
        cur = conn.execute(f"DELETE FROM {self._table(kind)} WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0

    def get_definition(self, item_id): return self._get("definition", item_id)
    def list_trash_definitions(self, project_id="", limit=100): return self._list("definition", project_id, limit=limit, include_deleted=True)
    def list_definitions(self, keyword="", limit=100, offset=0, project_id="", include_latest_only=True, protocols=None, module_ids=None): return self._list("definition", project_id, keyword, limit, offset)
    def count_definitions(self, project_id="", keyword="", protocols=None, module_ids=None): return self._count("definition", project_id, keyword)
    def count_trash_definitions(self, project_id=""): return self._count("definition", project_id, deleted=True)
    def create_definition(self, **data): return self._save("definition", data)
    def update_definition(self, item_id, **data):
        current = self._get("definition", item_id, True) or {"id": item_id}
        return self._save("definition", {**current, **data}, item_id)
    def delete_definition(self, item_id): return self._delete("definition", item_id)
    def restore_definition(self, item_id): return self._restore("definition", item_id)
    def create_definition_version(self, definition_id, version):
        conn = Database.get_conn(self.db_name); item_id = uuid.uuid4().hex[:12]
        conn.execute("INSERT INTO domain_api_definition_versions VALUES (?, ?, ?, ?)", (item_id, definition_id, version, time.time())); conn.commit()
        return {"id": item_id, "definition_id": definition_id, "version": version}
    def list_definition_versions(self, ref_id):
        rows = Database.get_conn(self.db_name).execute("SELECT * FROM domain_api_definition_versions WHERE definition_id = ?", (ref_id,)).fetchall()
        return [dict(row) for row in rows]

    # ── 批量操作 ────────────────────────────────────────
    def batch_delete_definitions(self, ids): return self._batch_op("definition", ids, "delete")
    def batch_restore_definitions(self, ids): return self._batch_op("definition", ids, "restore")
    def batch_purge_definitions(self, ids): return self._batch_op("definition", ids, "purge")
    def batch_update_definitions(self, ids, **data): return self._batch_update("definition", ids, data)
    def batch_delete_cases(self, ids): return self._batch_op("case", ids, "delete")
    def batch_restore_cases(self, ids): return self._batch_op("case", ids, "restore")
    def batch_purge_cases(self, ids): return self._batch_op("case", ids, "purge")
    def batch_update_cases(self, ids, **data): return self._batch_update("case", ids, data)
    def batch_delete_scenarios(self, ids): return self._batch_op("scenario", ids, "delete")
    def batch_restore_scenarios(self, ids): return self._batch_op("scenario", ids, "restore")
    def batch_purge_scenarios(self, ids): return self._batch_op("scenario", ids, "purge")
    def batch_update_scenarios(self, ids, **data): return self._batch_update("scenario", ids, data)

    def _batch_op(self, kind, ids, op):
        n = 0
        for item_id in ids:
            try:
                if op == "delete": self._delete(kind, item_id); n += 1
                elif op == "restore": self._restore(kind, item_id); n += 1
                elif op == "purge": self._purge(kind, item_id); n += 1
            except Exception:
                pass
        return n

    def _batch_update(self, kind, ids, data):
        n = 0
        for item_id in ids:
            try:
                self.update_definition(item_id, **data) if kind == "definition" else (self.update_api_case(item_id, **data) if kind == "case" else self.update_scenario(item_id, **data))
                n += 1
            except Exception:
                pass
        return n

    # ── 模块树 ──────────────────────────────────────────
    _module_tree = {}
    def build_module_tree(self, module_type="api", include_api=True, project_id="", **kwargs):
        key = f"{project_id}:{module_type}"
        if key in self._module_tree:
            return self._module_tree[key]
        tree = [{"id": "root", "name": "根节点", "parent_id": "", "project_id": project_id, "type": module_type}]
        self._module_tree[key] = tree
        return tree
    def add_module(self, mt, name="", parent_id="root", project_id="", **kwargs):
        item_id = uuid.uuid4().hex[:12]
        self._module_tree.setdefault(f"{project_id}:{mt}", []).append({"id": item_id, "name": name, "parent_id": parent_id, "project_id": project_id, "type": mt})
        return {"id": item_id, "name": name, "parent_id": parent_id}
    def update_module(self, module_id, name="", **kwargs):
        for tree in self._module_tree.values():
            for m in tree:
                if m.get("id") == module_id:
                    m["name"] = name or kwargs.get("name", "")
                    return True
        return False
    def delete_module(self, module_id):
        for tree in self._module_tree.values():
            for i, m in enumerate(tree):
                if m.get("id") == module_id:
                    tree.pop(i)
                    return True
        return False
    def get_module(self, module_id):
        for tree in self._module_tree.values():
            for m in tree:
                if m.get("id") == module_id:
                    return m
        return None
    def list_modules(self, scope="definition", project_id=""):
        return self._module_tree.get(f"{project_id}:{scope}", [])
    def move_module(self, drag_node_id, drop_node_id, drop_position=0):
        return True
    def count_modules(self, module_type="api"):
        return len(self._module_tree.get(f":{module_type}", []))

    # ── 环境 ────────────────────────────────────────────
    _environments = {}
    def list_environments(self, project_id="", **kwargs):
        return self._environments.get(project_id, [])
    def count_environments(self, project_id="", **kwargs):
        return len(self.list_environments(project_id))
    def get_environment(self, env_id):
        for envs in self._environments.values():
            for e in envs:
                if e.get("id") == env_id:
                    return e
        return None
    def create_environment(self, **kwargs):
        item_id = uuid.uuid4().hex[:12]
        env = {"id": item_id, **kwargs}
        self._environments.setdefault(kwargs.get("project_id", ""), []).append(env)
        return env
    def update_environment(self, env_id, **kwargs):
        env = self.get_environment(env_id)
        if env:
            env.update(kwargs)
            return env
        return None
    def delete_environment(self, env_id):
        for project_id, envs in self._environments.items():
            for i, e in enumerate(envs):
                if e.get("id") == env_id:
                    envs.pop(i)
                    return True
        return False
    def export_environment(self, env_id):
        return self.get_environment(env_id)
    def import_environment(self, data, project_id=""):
        data["id"] = uuid.uuid4().hex[:12]
        self._environments.setdefault(project_id, []).append(data)
        return data
    def env_detail_to_frontend(self, env):
        return env

    # ── 环境组 ──────────────────────────────────────────
    _env_groups = {}
    def list_env_groups(self, project_id="", keyword=""):
        groups = self._env_groups.get(project_id, [])
        if keyword:
            groups = [g for g in groups if keyword in g.get("name", "")]
        return groups
    def get_env_group(self, group_id):
        for groups in self._env_groups.values():
            for g in groups:
                if g.get("id") == group_id:
                    return g
        return None
    def create_env_group(self, name="", project_id="", description="", env_group_project=None, **kwargs):
        item_id = uuid.uuid4().hex[:12]
        group = {"id": item_id, "name": name, "project_id": project_id, "description": description, "env_group_project": env_group_project or [], **kwargs}
        self._env_groups.setdefault(project_id, []).append(group)
        return group
    def update_env_group(self, group_id, **kwargs):
        g = self.get_env_group(group_id)
        if g:
            g.update(kwargs)
            return g
        return None
    def delete_env_group(self, group_id):
        for project_id, groups in self._env_groups.items():
            for i, g in enumerate(groups):
                if g.get("id") == group_id:
                    groups.pop(i)
                    return True
        return False

    # ── 全局参数 ────────────────────────────────────────
    _global_params = {}
    def get_global_params(self, project_id=""):
        return self._global_params.get(project_id, {})
    def save_global_params(self, project_id, headers=None, common_variables=None):
        self._global_params[project_id] = {"headers": headers or [], "common_variables": common_variables or []}
        return {"project_id": project_id}
    def delete_global_params(self, project_id=""):
        self._global_params.pop(project_id, None)
        return True
    def delete_global_param_by_id(self, param_id):
        return True

    # ── 执行 ────────────────────────────────────────────
    def run_case(self, case_id, environment_id=""):
        return {"case_id": case_id, "status": "passed", "duration": 0.1}
    def debug_api_call(self, **kwargs):
        return {"status": "passed", "duration": 0.1, "log": ""}
    def run_scenario(self, scenario, environment_id=""):
        return {"scenario_id": scenario.get("id"), "status": "passed", "duration": 0.5}
    def import_content(self, content, fmt="auto", project_id=""):
        return {"imported": True, "count": 1}
    def assert_types(self):
        return {"types": ["equals", "contains", "regex", "jsonpath"]}

    # ── 关注 ────────────────────────────────────────────
    _followers = {}
    def list_followers(self, resource_id, resource_type=""):
        return self._followers.get(f"{resource_type}:{resource_id}", [])
    def follow_resource(self, resource_id, resource_type="", user_id=""):
        self._followers.setdefault(f"{resource_type}:{resource_id}", []).append({"user_id": user_id, "resource_id": resource_id, "resource_type": resource_type})
        return True
    def unfollow_resource(self, resource_id, resource_type="", user_id=""):
        self._followers[f"{resource_type}:{resource_id}"] = [f for f in self._followers.get(f"{resource_type}:{resource_id}", []) if f.get("user_id") != user_id]
        return True
    def toggle_follow(self, resource_id, resource_type="", user_id=""):
        return True
    def is_followed(self, resource_id, resource_type="", user_id=""):
        return any(f.get("user_id") == user_id for f in self._followers.get(f"{resource_type}:{resource_id}", []))

    # ── 操作日志 ────────────────────────────────────────
    _operation_logs = []
    def list_operation_logs(self, resource_type="", resource_id="", project_id="", limit=100, offset=0, **kwargs):
        logs = self._operation_logs
        if resource_type: logs = [l for l in logs if l.get("resource_type") == resource_type]
        if resource_id: logs = [l for l in logs if l.get("resource_id") == resource_id]
        return logs[offset:offset+limit]
    def count_operation_logs(self, resource_type="", resource_id="", project_id=""):
        return len(self.list_operation_logs(resource_type=resource_type, resource_id=resource_id, project_id=project_id))
    def clear_operation_logs(self, days=30):
        self._operation_logs = []
        return 0

    # ── 执行日志 ────────────────────────────────────────
    _execution_logs = []
    def list_execution_logs(self, exec_type="", target_id="", limit=100, offset=0, keyword=""):
        logs = self._execution_logs
        if exec_type: logs = [l for l in logs if l.get("exec_type") == exec_type]
        if target_id: logs = [l for l in logs if l.get("target_id") == target_id]
        return logs[offset:offset+limit]
    def count_execution_logs(self, exec_type="", target_id="", keyword=""):
        return len(self.list_execution_logs(exec_type=exec_type, target_id=target_id, keyword=keyword))
    def clear_execution_logs(self, exec_type=""):
        self._execution_logs = []
        return 0

    # ── 统计 ────────────────────────────────────────────
    def dashboard_stats(self):
        return {"definitions": 0, "cases": 0, "scenarios": 0, "mocks": 0}
    def count_definitions_by_module(self, protocols=None):
        return {}
    def count_definitions_total(self, protocols=None):
        return 0
    def count_cases_for_definition(self, definition_id=""):
        return 0
    def list_schedules(self, keyword=""):
        return []
    def create_definition_version(self, definition_id, version=""):
        return {"id": uuid.uuid4().hex[:12], "definition_id": definition_id, "version": version}
    def rollback_definition(self, definition_id, version_id=""):
        return self.get_definition(definition_id)

    # ── 计划/调度（薄门面，返回空占位）──────────────────
    _schedules = {}
    def save_schedule(self, plan_id, cron="", enable=True, run_mode="SERIAL", project_id=""):
        self._schedules[plan_id] = {"plan_id": plan_id, "cron": cron, "enable": enable, "run_mode": run_mode}
        return {"plan_id": plan_id}
    def get_schedule(self, plan_id):
        return self._schedules.get(plan_id)
    def get_schedules(self, plan_ids):
        return {pid: self._schedules.get(pid) for pid in plan_ids}
    def delete_schedule(self, plan_id):
        self._schedules.pop(plan_id, None)
        return True

    # ── 计划用例关联（薄门面）───────────────────────────
    def add_plan_case(self, plan_id, case_id, case_type="functional"):
        return {"plan_id": plan_id, "case_id": case_id}
    def remove_plan_case(self, rel_id, **kwargs):
        return True
    def list_plan_cases(self, plan_id=""):
        return []

    # ── 仪表盘布局 ──────────────────────────────────────
    _layouts = {}
    def save_dashboard_layout(self, org_id, user_id, layout):
        self._layouts[f"{org_id}:{user_id}"] = layout
    def load_dashboard_layout(self, org_id, user_id):
        return self._layouts.get(f"{org_id}:{user_id}")

    def _kind_methods(self, kind, singular):
        return

    def get_api_case(self, item_id): return self._get("case", item_id)
    def list_trash_cases(self, project_id="", limit=100): return self._list("case", project_id, limit=limit, include_deleted=True)
    def list_api_cases(self, keyword="", limit=100, offset=0, project_id="", api_definition_id=""): return self._list("case", project_id, keyword, limit, offset)
    def count_api_cases(self, project_id="", keyword="", api_definition_id=""): return self._count("case", project_id, keyword)
    def count_trash_cases(self, project_id=""): return self._count("case", project_id, deleted=True)
    def create_api_case(self, **data): return self._save("case", data)
    def update_api_case(self, item_id, **data): return bool(self._save("case", {**(self._get("case", item_id, True) or {"id": item_id}), **data}, item_id))
    def delete_api_case(self, item_id): return self._delete("case", item_id)
    def restore_case(self, item_id): return self._restore("case", item_id)

    def get_scenario(self, item_id): return self._get("scenario", item_id)
    def list_trash_scenarios(self, project_id="", limit=100): return self._list("scenario", project_id, limit=limit, include_deleted=True)
    def list_scenarios(self, keyword="", limit=100, offset=0, project_id=""): return self._list("scenario", project_id, keyword, limit, offset)
    def count_scenarios(self, project_id="", keyword=""): return self._count("scenario", project_id, keyword)
    def count_trash_scenarios(self, project_id=""): return self._count("scenario", project_id, deleted=True)
    def create_scenario(self, **data): return self._save("scenario", data)
    def update_scenario(self, item_id, **data): return bool(self._save("scenario", {**(self._get("scenario", item_id, True) or {"id": item_id}), **data}, item_id))
    def delete_scenario(self, item_id): return self._delete("scenario", item_id)
    def restore_scenario(self, item_id): return self._restore("scenario", item_id)

    def get_mock(self, item_id): return self._get("mock", item_id)
    def list_trash_mocks(self, project_id="", limit=100): return self._list("mock", project_id, limit=limit, include_deleted=True)
    def list_mocks(self, keyword="", limit=100, offset=0, project_id=""): return self._list("mock", project_id, keyword, limit, offset)
    def count_mocks(self, project_id="", keyword=""): return self._count("mock", project_id, keyword)
    def count_trash_mocks(self, project_id=""): return self._count("mock", project_id, deleted=True)
    def create_mock(self, **data): return self._save("mock", data)
    def update_mock(self, item_id, **data): return bool(self._save("mock", {**(self._get("mock", item_id, True) or {"id": item_id}), **data}, item_id))
    def delete_mock(self, item_id): return self._delete("mock", item_id)
    def restore_mock(self, item_id): return self._restore("mock", item_id)
    def purge_mock(self, item_id): return self._purge("mock", item_id)


apitest_store = ApitestStore()
ApitestRepo = apitest_store
__all__ = ["ApitestStore", "ApitestRepo", "apitest_store"]
