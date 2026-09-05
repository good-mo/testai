# app/repositories/apitest_repo.py
"""接口测试数据访问层（Phase 3 重构 · 4 层对齐）。

本层是接口测试域（定义/用例/场景/Mock/环境/回收站）的数据访问与执行统一入口。
所有数据访问与执行逻辑直接在本层实现，供 service 层消费。
"""
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Optional

from app.core.database import Database


class ApitestRepo:
    """接口测试数据访问层（门面）。"""

    # ═══════════════════════════════════════════════════
    # 接口定义
    # ═══════════════════════════════════════════════════
    @classmethod
    def list_definitions(cls, keyword: str = "", limit: int = 100,
                         offset: int = 0, project_id: str = "",
                         include_latest_only: bool = True,
                         protocols: Optional[list] = None,
                         module_ids: Optional[list] = None) -> list:
        """分页列出接口定义（仓库内直连 SQL，默认仅最新版本）。"""
        conn = cls._apitest_conn()
        sql = "SELECT * FROM api_definitions WHERE (deleted IS NULL OR deleted = 0)"
        params: list = []
        if include_latest_only:
            sql += " AND (latest IS NULL OR latest = 1)"
        if keyword:
            sql += " AND (name LIKE ? OR path LIKE ? OR description LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        if protocols:
            sql += " AND protocol IN (" + ",".join("?" for _ in protocols) + ")"
            params.extend(list(protocols))
        if module_ids and module_ids != ["all"] and "all" not in module_ids:
            placeholders = ",".join("?" for _ in module_ids)
            if "root" in module_ids:
                sql += (
                    f" AND (module_id IN ({placeholders}) "
                    f"OR module_id IS NULL OR module_id = '')"
                )
            else:
                sql += f" AND module_id IN ({placeholders})"
            params.extend(list(module_ids))
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(sql, params).fetchall()
        return [cls._apitest_row(r) for r in rows]

    @classmethod
    def count_definitions(cls, project_id: str = "", **kwargs) -> int:
        """统计符合条件的接口定义数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT COUNT(*) AS c FROM api_definitions WHERE (deleted IS NULL OR deleted = 0)"
        params: list = []
        sql += " AND (latest IS NULL OR latest = 1)"
        keyword = kwargs.get("keyword", "")
        protocols = kwargs.get("protocols")
        module_ids = kwargs.get("module_ids")
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        if keyword:
            sql += " AND (name LIKE ? OR path LIKE ? OR description LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if protocols:
            sql += " AND protocol IN (" + ",".join("?" for _ in protocols) + ")"
            params.extend(list(protocols))
        if module_ids and module_ids != ["all"] and "all" not in module_ids:
            placeholders = ",".join("?" for _ in module_ids)
            if "root" in module_ids:
                sql += (
                    f" AND (module_id IN ({placeholders}) "
                    f"OR module_id IS NULL OR module_id = '')"
                )
            else:
                sql += f" AND module_id IN ({placeholders})"
            params.extend(list(module_ids))
        row = conn.execute(sql, params).fetchone()
        return row["c"] if row else 0

    @classmethod
    def count_definitions_by_module(cls, protocols=None) -> dict:
        """统计每个模块下的接口定义数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = (
            "SELECT module_id, COUNT(*) AS c FROM api_definitions "
            "WHERE (deleted IS NULL OR deleted = 0) "
        )
        params: list = []
        if protocols:
            ph = ",".join("?" for _ in protocols)
            sql += f" AND protocol IN ({ph})"
            params = list(protocols)
        sql += " GROUP BY module_id"
        counts: dict = {}
        for r in conn.execute(sql, params).fetchall():
            counts[r["module_id"] or "root"] = r["c"]
        return counts

    @classmethod
    def count_definitions_total(cls, protocols=None) -> int:
        """统计接口定义总数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT COUNT(*) AS c FROM api_definitions WHERE (deleted IS NULL OR deleted = 0)"
        params: list = []
        if protocols:
            ph = ",".join("?" for _ in protocols)
            sql += f" AND protocol IN ({ph})"
            params = list(protocols)
        row = conn.execute(sql, params).fetchone()
        return row["c"] if row else 0

    @classmethod
    def count_cases_for_definition(cls, definition_id: str) -> int:
        """统计某接口定义下的接口用例数（仓库内直连 SQL）。"""
        if not definition_id:
            return 0
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM api_cases "
            "WHERE api_definition_id = ? AND (deleted IS NULL OR deleted = 0)",
            (definition_id,),
        ).fetchone()
        return row["c"] if row else 0

    @classmethod
    def list_schedules(cls, keyword: str = "") -> list:
        """查询真实调度任务列表（api_schedules 表，仓库内直连 SQL）。"""
        items: list = []
        try:
            conn = cls._apitest_conn()
            rows = conn.execute(
                "SELECT id, name, cron, status, enabled, created_at "
                "FROM api_schedules "
                "WHERE (? = '' OR name LIKE ?) "
                "ORDER BY created_at DESC LIMIT 500",
                (keyword, f"%{keyword}%"),
            ).fetchall()
            for r in rows:
                items.append({
                    "id": r["id"],
                    "name": r["name"],
                    "cron": r["cron"],
                    "status": "OPEN" if r["enabled"] else "CLOSE",
                    "createTime": int((r["created_at"] or 0) * 1000),
                    "nextExecutionTime": 0,
                    "executor": "admin",
                })
        except Exception:
            return []
        return items

    @classmethod
    def get_definition(cls, definition_id: str) -> Optional[dict]:
        """获取单个接口定义（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_definitions WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (definition_id,)
        ).fetchone()
        return cls._apitest_row(row) if row else None

    @classmethod
    def create_definition(cls, name: str, protocol: str = "HTTP", method: str = "GET",
                          path: str = "", headers: dict = None, body: str = "",
                          query: dict = None, params: dict = None,
                          description: str = "", tags: list = None,
                          project_id: str = "", version: str = "v1",
                          module_id: str = "", **kwargs) -> dict:
        """创建接口定义（仓库内直连 SQL）。"""
        def_id = cls._new_id()
        ref_id = cls._new_id()
        version_id = cls._new_id()
        now = cls._now()
        conn = cls._apitest_conn()
        data = {
            "id": def_id, "name": name, "protocol": protocol, "method": method,
            "path": path,
            "headers": json.dumps(headers or {}, ensure_ascii=False),
            "body": body, "query": json.dumps(query or {}, ensure_ascii=False),
            "params": json.dumps(params or {}, ensure_ascii=False),
            "description": description,
            "tags": json.dumps(tags or [], ensure_ascii=False),
            "project_id": project_id,
            "module_id": module_id or "",
            "version_id": version_id, "ref_id": ref_id, "latest": 1,
            "created_at": now, "updated_at": now, "metadata": "{}",
            "deleted": 0,
        }
        cols = ", ".join(data.keys())
        marks = ", ".join(["?"] * len(data))
        conn.execute(
            f"INSERT INTO api_definitions ({cols}) VALUES ({marks})",
            list(data.values()))
        # 记录版本快照
        conn.execute(
            """INSERT INTO api_definition_versions
               (id, ref_id, definition_id, version, version_id, snapshot, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (cls._new_id(), ref_id, def_id, version, version_id,
             json.dumps(data, ensure_ascii=False), now))
        conn.commit()
        cls._apitest_log("definition", def_id, name, "create",
                         detail={"version": version}, project_id=project_id)
        return cls.get_definition(def_id) or {"id": def_id}

    @classmethod
    def update_definition(cls, definition_id: str, **kwargs) -> Optional[dict]:
        """更新接口定义（仓库内直连 SQL）。"""
        for k in ("headers", "query", "params", "tags"):
            if k in kwargs and isinstance(kwargs[k], (dict, list)):
                kwargs[k] = json.dumps(kwargs[k], ensure_ascii=False)
        kwargs["updated_at"] = cls._now()
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_definitions WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (definition_id,)
        ).fetchone()
        if not row:
            return None
        sets = ", ".join([f"{k} = ?" for k in kwargs])
        conn.execute(
            f"UPDATE api_definitions SET {sets} WHERE id = ?",
            list(kwargs.values()) + [definition_id])
        conn.commit()
        item = cls.get_definition(definition_id) or {}
        cls._apitest_log("definition", definition_id, item.get("name", ""),
                         "update",
                         detail={k: v for k, v in kwargs.items() if k != "updated_at"},
                         project_id=item.get("project_id", ""))
        return item or None

    @classmethod
    def delete_definition(cls, definition_id: str) -> bool:
        """软删除接口定义，进入回收站（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_definitions WHERE id = ?", (definition_id,)
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE api_definitions SET deleted = 1, deleted_at = ? WHERE id = ?",
            (cls._now(), definition_id))
        conn.commit()
        cls._apitest_log("definition", definition_id, row["name"], "delete",
                         project_id=row["project_id"])
        return True

    # ── 版本 ─────────────────────────────────────────────
    @classmethod
    def list_definition_versions(cls, ref_id: str) -> list:
        """列出指定 ref_id 下的所有版本（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        rows = conn.execute(
            "SELECT * FROM api_definition_versions WHERE ref_id = ? "
            "ORDER BY created_at DESC", (ref_id,)
        ).fetchall()
        return [cls._apitest_row(r) for r in rows]

    @classmethod
    def create_definition_version(cls, definition_id: str,
                                  version: str = "") -> Optional[dict]:
        """为接口定义创建新版本（仓库内直连 SQL）。"""
        item = cls.get_definition(definition_id)
        if not item:
            return None
        ref_id = item.get("ref_id") or definition_id
        conn = cls._apitest_conn()
        conn.execute(
            "UPDATE api_definitions SET latest = 0 WHERE ref_id = ? AND latest = 1",
            (ref_id,))
        new_def_id = cls._new_id()
        new_version_id = cls._new_id()
        now = cls._now()
        if not version:
            existing = conn.execute(
                "SELECT COUNT(*) FROM api_definition_versions WHERE ref_id = ?",
                (ref_id,)).fetchone()[0]
            version = f"v{existing + 1}"
        data = {
            "id": new_def_id,
            "name": item.get("name", ""),
            "protocol": item.get("protocol", "HTTP"),
            "method": item.get("method", "GET"),
            "path": item.get("path", ""),
            "headers": json.dumps(item.get("headers", {}), ensure_ascii=False),
            "body": item.get("body", ""),
            "query": json.dumps(item.get("query", {}), ensure_ascii=False),
            "params": json.dumps(item.get("params", {}), ensure_ascii=False),
            "description": item.get("description", ""),
            "tags": json.dumps(item.get("tags", []), ensure_ascii=False),
            "project_id": item.get("project_id", ""),
            "module_id": item.get("module_id", ""),
            "version_id": new_version_id,
            "ref_id": ref_id,
            "latest": 1,
            "created_at": now,
            "updated_at": now,
            "metadata": "{}",
            "deleted": 0,
        }
        cols = ", ".join(data.keys())
        marks = ", ".join(["?"] * len(data))
        conn.execute(
            f"INSERT INTO api_definitions ({cols}) VALUES ({marks})",
            list(data.values()))
        conn.execute(
            """INSERT INTO api_definition_versions
               (id, ref_id, definition_id, version, version_id, snapshot, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (cls._new_id(), ref_id, new_def_id, version, new_version_id,
             json.dumps(data, ensure_ascii=False), now))
        conn.commit()
        cls._apitest_log("definition", new_def_id, data["name"], "version_create",
                         detail={"version": version, "from": definition_id},
                         project_id=data["project_id"])
        return cls.get_definition(new_def_id)

    @classmethod
    def rollback_definition(cls, definition_id: str,
                            version_id: str) -> Optional[dict]:
        """回滚接口定义到指定版本（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_definition_versions WHERE version_id = ? OR definition_id = ?",
            (version_id, version_id)).fetchone()
        if not row:
            return None
        ver = cls._apitest_row(row)
        snapshot = ver.get("snapshot", {})
        current = cls.get_definition(definition_id)
        if not current:
            return None
        ref_id = current.get("ref_id") or current["id"]
        new_def_id = cls._new_id()
        new_version_id = cls._new_id()
        now = cls._now()
        data = {
            "id": new_def_id,
            "name": snapshot.get("name", current.get("name", "")),
            "protocol": snapshot.get("protocol", "HTTP"),
            "method": snapshot.get("method", "GET"),
            "path": snapshot.get("path", ""),
            "headers": snapshot.get("headers", "{}"),
            "body": snapshot.get("body", ""),
            "query": snapshot.get("query", "{}"),
            "params": snapshot.get("params", "{}"),
            "description": snapshot.get("description", ""),
            "tags": snapshot.get("tags", "[]"),
            "project_id": current.get("project_id", ""),
            "version_id": new_version_id,
            "ref_id": ref_id,
            "latest": 1,
            "created_at": now,
            "updated_at": now,
            "metadata": "{}",
            "deleted": 0,
        }
        conn.execute(
            "UPDATE api_definitions SET latest = 0 WHERE ref_id = ? AND latest = 1",
            (ref_id,))
        cols = ", ".join(data.keys())
        marks = ", ".join(["?"] * len(data))
        conn.execute(
            f"INSERT INTO api_definitions ({cols}) VALUES ({marks})",
            list(data.values()))
        version = f"v{ver.get('version', '1')}-rollback"
        conn.execute(
            """INSERT INTO api_definition_versions
               (id, ref_id, definition_id, version, version_id, snapshot, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (cls._new_id(), ref_id, new_def_id, version, new_version_id,
             json.dumps(data, ensure_ascii=False), now))
        conn.commit()
        cls._apitest_log("definition", new_def_id, data["name"], "version_rollback",
                         detail={"from_version": ver.get("version", "")},
                         project_id=data["project_id"])
        return cls.get_definition(new_def_id)

    # ═══════════════════════════════════════════════════
    # 接口用例
    # ═══════════════════════════════════════════════════
    @classmethod
    def list_api_cases(cls, keyword: str = "", limit: int = 100,
                       offset: int = 0, project_id: str = "",
                       api_definition_id: str = "", **kwargs) -> list:
        """分页列出接口用例（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT * FROM api_cases WHERE (deleted IS NULL OR deleted = 0)"
        params: list = []
        if keyword:
            sql += " AND name LIKE ?"
            params.append(f"%{keyword}%")
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        if api_definition_id:
            sql += " AND api_definition_id = ?"
            params.append(api_definition_id)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [cls._apitest_row(r) for r in rows]

    @classmethod
    def count_api_cases(cls, project_id: str = "",
                        api_definition_id: str = "", **kwargs) -> int:
        """统计接口用例数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT COUNT(*) AS c FROM api_cases WHERE (deleted IS NULL OR deleted = 0)"
        params: list = []
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        if api_definition_id:
            sql += " AND api_definition_id = ?"
            params.append(api_definition_id)
        row = conn.execute(sql, tuple(params)).fetchone()
        return row["c"] if row else 0

    @classmethod
    def get_api_case(cls, case_id: str) -> Optional[dict]:
        """获取单个接口用例（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_cases WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (case_id,)).fetchone()
        return cls._apitest_row(row) if row else None

    @classmethod
    def create_api_case(cls, name: str, api_definition_id: str = "",
                        request: dict = None, asserts: list = None,
                        pre_scripts: list = None, post_scripts: list = None,
                        pre_sql: list = None, post_sql: list = None,
                        variables: list = None, logic_controllers: list = None,
                        environment_id: str = "", status: str = "draft",
                        priority: str = "P2", description: str = "",
                        project_id: str = "", method: str = "",
                        path: str = "", **kwargs) -> dict:
        """创建接口用例（仓库内直连 SQL）。"""
        now = cls._now()
        cid = cls._new_id()
        conn = cls._apitest_conn()
        conn.execute(
            """INSERT INTO api_cases
               (id, name, api_definition_id, request, asserts, pre_scripts,
                post_scripts, pre_sql, post_sql, variables, logic_controllers,
                environment_id, status, priority, description, project_id,
                created_at, updated_at, metadata, deleted)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, name, api_definition_id,
             json.dumps(request or {}, ensure_ascii=False),
             json.dumps(asserts or [], ensure_ascii=False),
             json.dumps(pre_scripts or [], ensure_ascii=False),
             json.dumps(post_scripts or [], ensure_ascii=False),
             json.dumps(pre_sql or [], ensure_ascii=False),
             json.dumps(post_sql or [], ensure_ascii=False),
             json.dumps(variables or [], ensure_ascii=False),
             json.dumps(logic_controllers or [], ensure_ascii=False),
             environment_id, status, priority, description, project_id,
             now, now, "{}", 0),
        )
        conn.commit()
        cls._apitest_log("case", cid, name, "create", project_id=project_id)
        return cls.get_api_case(cid) or {"id": cid}

    @classmethod
    def update_api_case(cls, case_id: str, **fields) -> Optional[dict]:
        """更新接口用例（仓库内直连 SQL）。"""
        for k in ("request", "asserts", "pre_scripts", "post_scripts", "pre_sql",
                  "post_sql", "variables", "logic_controllers"):
            if k in fields and isinstance(fields[k], (dict, list)):
                fields[k] = json.dumps(fields[k], ensure_ascii=False)
        fields["updated_at"] = cls._now()
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_cases WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (case_id,)).fetchone()
        if not row:
            return None
        sets = ", ".join([f"{k} = ?" for k in fields])
        conn.execute(f"UPDATE api_cases SET {sets} WHERE id = ?",
                     list(fields.values()) + [case_id])
        conn.commit()
        item = cls.get_api_case(case_id) or {}
        cls._apitest_log("case", case_id, item.get("name", ""), "update",
                         detail={k: v for k, v in fields.items()
                                 if k != "updated_at"},
                         project_id=item.get("project_id", ""))
        return item or None

    @classmethod
    def delete_api_case(cls, case_id: str) -> bool:
        """软删除接口用例，进入回收站（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_cases WHERE id = ?", (case_id,)).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE api_cases SET deleted = 1, deleted_at = ? WHERE id = ?",
            (cls._now(), case_id))
        conn.commit()
        cls._apitest_log("case", case_id, row["name"], "delete",
                         project_id=row["project_id"])
        return True

    # ═══════════════════════════════════════════════════
    # 场景
    # ═══════════════════════════════════════════════════
    @classmethod
    def list_scenarios(cls, keyword: str = "", limit: int = 100,
                       offset: int = 0, project_id: str = "", **kwargs) -> list:
        """分页列出接口场景（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT * FROM api_scenarios WHERE (deleted IS NULL OR deleted = 0)"
        params: list = []
        if keyword:
            sql += " AND name LIKE ?"
            params.append(f"%{keyword}%")
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [cls._apitest_row(r) for r in rows]

    @classmethod
    def count_scenarios(cls, project_id: str = "", **kwargs) -> int:
        """统计接口场景数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT COUNT(*) AS c FROM api_scenarios WHERE (deleted IS NULL OR deleted = 0)"
        params: list = []
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        row = conn.execute(sql, tuple(params)).fetchone()
        return row["c"] if row else 0

    @classmethod
    def get_scenario(cls, scenario_id: str) -> Optional[dict]:
        """获取单个接口场景（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_scenarios WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (scenario_id,)).fetchone()
        return cls._apitest_row(row) if row else None

    @classmethod
    def create_scenario(cls, name: str, steps: list = None,
                        description: str = "", status: str = "draft",
                        environment_id: str = "", project_id: str = "",
                        **kwargs) -> dict:
        """创建接口场景（仓库内直连 SQL）。"""
        now = cls._now()
        sid = cls._new_id()
        conn = cls._apitest_conn()
        conn.execute(
            """INSERT INTO api_scenarios
               (id, name, steps, description, status, environment_id,
                project_id, created_at, updated_at, metadata, deleted)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (sid, name, json.dumps(steps or [], ensure_ascii=False),
             description, status, environment_id, project_id,
             now, now, "{}", 0),
        )
        conn.commit()
        cls._apitest_log("scenario", sid, name, "create", project_id=project_id)
        return cls.get_scenario(sid) or {"id": sid}

    @classmethod
    def update_scenario(cls, scenario_id: str, **fields) -> Optional[dict]:
        """更新接口场景（仓库内直连 SQL）。"""
        if "steps" in fields and isinstance(fields["steps"], list):
            fields["steps"] = json.dumps(fields["steps"], ensure_ascii=False)
        fields["updated_at"] = cls._now()
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_scenarios WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (scenario_id,)).fetchone()
        if not row:
            return None
        sets = ", ".join([f"{k} = ?" for k in fields])
        conn.execute(f"UPDATE api_scenarios SET {sets} WHERE id = ?",
                     list(fields.values()) + [scenario_id])
        conn.commit()
        item = cls.get_scenario(scenario_id) or {}
        cls._apitest_log("scenario", scenario_id, item.get("name", ""), "update",
                         detail={k: v for k, v in fields.items()
                                 if k != "updated_at"},
                         project_id=item.get("project_id", ""))
        return item or None

    @classmethod
    def delete_scenario(cls, scenario_id: str) -> bool:
        """软删除接口场景，进入回收站（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_scenarios WHERE id = ?", (scenario_id,)).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE api_scenarios SET deleted = 1, deleted_at = ? WHERE id = ?",
            (cls._now(), scenario_id))
        conn.commit()
        cls._apitest_log("scenario", scenario_id, row["name"], "delete",
                         project_id=row["project_id"])
        return True

    # ═══════════════════════════════════════════════════
    # Mock
    # ═══════════════════════════════════════════════════
    @classmethod
    def list_mocks(cls, keyword: str = "", limit: int = 100,
                   offset: int = 0, project_id: str = "", **kwargs) -> list:
        """分页列出 Mock 服务（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT * FROM api_mocks WHERE (deleted IS NULL OR deleted = 0)"
        params: list = []
        if keyword:
            sql += " AND name LIKE ?"
            params.append(f"%{keyword}%")
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [cls._apitest_row(r) for r in rows]

    @classmethod
    def count_mocks(cls, project_id: str = "", **kwargs) -> int:
        """统计 Mock 服务数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT COUNT(*) AS c FROM api_mocks WHERE (deleted IS NULL OR deleted = 0)"
        params: list = []
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        row = conn.execute(sql, tuple(params)).fetchone()
        return row["c"] if row else 0

    @classmethod
    def get_mock(cls, mock_id: str) -> Optional[dict]:
        """获取单个 Mock 服务（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_mocks WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (mock_id,)).fetchone()
        return cls._apitest_row(row) if row else None

    @classmethod
    def create_mock(cls, name: str, api_definition_id: str = "",
                    method: str = "GET", path: str = "", status_code: int = 200,
                    response_body: str = "", response_headers: dict = None,
                    delay_ms: int = 0, active: int = 1, description: str = "",
                    project_id: str = "", match_type: str = "exact",
                    match_script: str = "", **kwargs) -> dict:
        """创建 Mock 服务（仓库内直连 SQL）。"""
        now = cls._now()
        mid = cls._new_id()
        conn = cls._apitest_conn()
        conn.execute(
            """INSERT INTO api_mocks
               (id, name, api_definition_id, method, path, status_code,
                response_body, response_headers, delay_ms, active, description,
                project_id, match_type, match_script, created_at, updated_at, deleted)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (mid, name, api_definition_id, method, path, status_code,
             response_body,
             json.dumps(response_headers or {}, ensure_ascii=False),
             delay_ms, active, description, project_id, match_type, match_script,
             now, now, 0),
        )
        conn.commit()
        cls._apitest_log("mock", mid, name, "create", project_id=project_id)
        return cls.get_mock(mid) or {"id": mid}

    @classmethod
    def update_mock(cls, mock_id: str, **fields) -> Optional[dict]:
        """更新 Mock 服务（仓库内直连 SQL）。"""
        if "response_headers" in fields and isinstance(fields["response_headers"], dict):
            fields["response_headers"] = json.dumps(fields["response_headers"], ensure_ascii=False)
        fields["updated_at"] = cls._now()
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_mocks WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (mock_id,)).fetchone()
        if not row:
            return None
        sets = ", ".join([f"{k} = ?" for k in fields])
        conn.execute(f"UPDATE api_mocks SET {sets} WHERE id = ?",
                     list(fields.values()) + [mock_id])
        conn.commit()
        item = cls.get_mock(mock_id) or {}
        cls._apitest_log("mock", mock_id, item.get("name", ""), "update",
                         detail={k: v for k, v in fields.items() if k != "updated_at"},
                         project_id=item.get("project_id", ""))
        return item or None

    @classmethod
    def delete_mock(cls, mock_id: str) -> bool:
        """软删除 Mock 服务，进入回收站（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_mocks WHERE id = ?", (mock_id,)).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE api_mocks SET deleted = 1, deleted_at = ? WHERE id = ?",
            (cls._now(), mock_id))
        conn.commit()
        cls._apitest_log("mock", mock_id, row["name"], "delete",
                         project_id=row["project_id"])
        return True

    # ── Mock 运行时匹配工具（由 service.run_mock_request 下沉）────────
    @staticmethod
    def _mock_path_match(mock_path: str, req_path: str) -> bool:
        """通配路径匹配（支持 ** / * / {param}）。"""
        mp = (mock_path or "").rstrip("/")
        rp = (req_path or "").rstrip("/")
        if mp == rp:
            return True
        pattern = ""
        i = 0
        while i < len(mp):
            ch = mp[i]
            if ch == '{':
                end = mp.find('}', i)
                if end != -1:
                    pattern += r"[^/]+"
                    i = end + 1
                    continue
                else:
                    pattern += r"\{"
                    i += 1
            elif ch == '*':
                if i + 1 < len(mp) and mp[i+1] == '*':
                    pattern += r".*"
                    i += 2
                else:
                    pattern += r"[^/]*"
                    i += 1
            else:
                pattern += re.escape(ch)
                i += 1
        pattern = "^" + pattern + "$"
        try:
            return bool(re.match(pattern, rp))
        except re.error:
            return False

    @classmethod
    def run_mock_request(cls, method: str, path: str, base_path: str = "",
                         query_params: dict = None,
                         request_body: str = "") -> Optional[dict]:
        """根据请求方法+路径匹配启用的 Mock，返回响应。"""
        from app.apitest import engine as _engine
        mocks = cls.list_mocks(keyword="", limit=10000, offset=0)
        # 规范化请求路径：去掉 base_path 前缀
        req_path = path
        if base_path and req_path.startswith(base_path.rstrip("/")):
            req_path = req_path[len(base_path.rstrip("/")):] or "/"

        best_match = None
        best_score = -1

        for m in mocks:
            if not m.get("active"):
                continue
            m_path = m.get("path", "")
            m_method = m.get("method", "").upper()
            if m_method and m_method != method.upper():
                continue

            # 兼容：mock path 可能带 base_path 前缀，也可能不带
            m_norm = m_path
            if base_path and m_norm.startswith(base_path.rstrip("/")):
                m_norm = m_norm[len(base_path.rstrip("/")):] or "/"

            match_type = m.get("match_type", "exact")
            matched = False
            score = 0

            if match_type == "script":
                script = m.get("match_script", "")
                if script:
                    try:
                        ctx = {
                            "method": method.upper(),
                            "path": req_path,
                            "query": query_params or {},
                            "body": request_body or "",
                        }
                        matched = bool(eval(script, {"__builtins__": {}}, ctx))
                        score = 100
                    except Exception:
                        matched = False
            elif match_type == "wildcard":
                matched = cls._mock_path_match(m_norm, req_path)
                if matched:
                    non_wild = len([c for c in m_norm if c not in "*{}"])
                    score = non_wild
            else:
                if m_norm.lstrip("/") == req_path.lstrip("/"):
                    matched = True
                    score = 1000

            if matched and score > best_score:
                best_score = score
                best_match = m

        if best_match:
            return _engine.generate_mock_response(
                best_match, {"method": method, "path": path})
        return None

    # ═══════════════════════════════════════════════════
    # 环境
    # ═══════════════════════════════════════════════════
    @classmethod
    def list_environments(cls, keyword: str = "", limit: int = 100,
                          project_id: str = "", **kwargs) -> list:
        """列出环境（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        if project_id:
            rows = conn.execute(
                "SELECT * FROM api_environments WHERE (project_id = ? OR project_id = '') "
                "AND (deleted IS NULL OR deleted = 0) ORDER BY created_at ASC",
                (project_id,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM api_environments WHERE (deleted IS NULL OR deleted = 0) "
                "ORDER BY created_at ASC").fetchall()
        return [cls._apitest_row(r) for r in rows]

    @classmethod
    def count_environments(cls, project_id: str = "", **kwargs) -> int:
        """统计环境数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        if project_id:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM api_environments "
                "WHERE (project_id = ? OR project_id = '') "
                "AND (deleted IS NULL OR deleted = 0)", (project_id,)).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM api_environments "
                "WHERE (deleted IS NULL OR deleted = 0)").fetchone()
        return row["c"] if row else 0

    @classmethod
    def get_environment(cls, env_id: str) -> Optional[dict]:
        """获取环境（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_environments WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (env_id,)).fetchone()
        return cls._apitest_row(row) if row else None

    @classmethod
    def create_environment(cls, name: str = "", base_url: str = "",
                           headers: dict = None, variables: dict = None,
                           description: str = "", project_id: str = "",
                           script: str = "", database_config: dict = None,
                           config: dict = None, **kwargs) -> dict:
        """创建环境（仓库内直连 SQL）。"""
        env_id = cls._new_id()
        now = cls._now()
        conn = cls._apitest_conn()
        conn.execute(
            """INSERT INTO api_environments
               (id, name, base_url, headers, variables, description,
                project_id, script, database_config, config,
                created_at, updated_at, deleted)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (env_id, name, base_url,
             json.dumps(headers or {}, ensure_ascii=False),
             json.dumps(variables or {}, ensure_ascii=False),
             description, project_id, script,
             json.dumps(database_config or {}, ensure_ascii=False),
             json.dumps(config or {}, ensure_ascii=False),
             now, now, 0))
        conn.commit()
        cls._apitest_log("environment", env_id, name, "create", project_id=project_id)
        return cls.get_environment(env_id) or {"id": env_id, "name": name}

    @classmethod
    def update_environment(cls, env_id: str, **kwargs) -> Optional[dict]:
        """更新环境（仓库内直连 SQL）。"""
        for k in ("headers", "variables", "database_config", "config"):
            if k in kwargs and isinstance(kwargs[k], (dict, list)):
                kwargs[k] = json.dumps(kwargs[k], ensure_ascii=False)
        kwargs["updated_at"] = cls._now()
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_environments WHERE (deleted IS NULL OR deleted = 0) AND id = ?", (env_id,)).fetchone()
        if not row:
            return None
        sets = ", ".join([f"{k} = ?" for k in kwargs])
        conn.execute(
            f"UPDATE api_environments SET {sets} WHERE id = ?",
            list(kwargs.values()) + [env_id])
        conn.commit()
        item = cls.get_environment(env_id) or {}
        cls._apitest_log("environment", env_id, item.get("name", ""), "update",
                         detail={k: v for k, v in kwargs.items() if k != "updated_at"},
                         project_id=item.get("project_id", ""))
        return item or None

    @classmethod
    def delete_environment(cls, env_id: str) -> bool:
        """删除环境（软删除，仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_environments WHERE id = ?", (env_id,)).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE api_environments SET deleted = 1, deleted_at = ? WHERE id = ?",
            (cls._now(), env_id))
        conn.commit()
        cls._apitest_log("environment", env_id, row["name"], "delete",
                         project_id=row["project_id"])
        return True

    @classmethod
    def export_environment(cls, env_id: str) -> Optional[dict]:
        """导出环境配置为 JSON（仓库内直连 SQL）。"""
        return cls.get_environment(env_id)

    @classmethod
    def import_environment(cls, data: dict, project_id: str = "") -> dict:
        """导入环境配置（仓库内直连 SQL）。

        project_id 可选：未显式传入时从 data 中回退读取，
        兼容「项目维度放在请求体里」的调用方式。
        """
        if not data or not data.get("name"):
            return None
        if not project_id:
            project_id = data.get("project_id") or data.get("projectId") or ""
        config = data.get("config") or {}
        return cls.create_environment(
            name=data["name"],
            base_url=data.get("base_url", ""),
            headers=data.get("headers", {}),
            variables=data.get("variables", {}),
            description=data.get("description", ""),
            project_id=project_id,
            script=data.get("script", ""),
            database_config=data.get("database_config", {}),
            config=config,
        )

    # ═══════════════════════════════════════════════════
    # 回收站
    # ═══════════════════════════════════════════════════
    @classmethod
    def list_trash_definitions(cls, project_id: str = "",
                               limit: int = 100) -> list:
        """列出回收站中的接口定义（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT * FROM api_definitions WHERE deleted = 1"
        params = []
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        sql += " ORDER BY deleted_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [cls._apitest_row(r) for r in rows]

    @classmethod
    def restore_definition(cls, definition_id: str) -> bool:
        """从回收站恢复接口定义（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_definitions WHERE id = ?", (definition_id,)
        ).fetchone()
        if not row:
            return False
        cur = conn.execute(
            "UPDATE api_definitions SET deleted = 0, deleted_at = NULL "
            "WHERE id = ? AND deleted = 1", (definition_id,))
        conn.commit()
        cls._apitest_log("definition", definition_id, row["name"], "restore",
                         project_id=row["project_id"])
        return cur.rowcount > 0

    @classmethod
    def purge_definition(cls, definition_id: str) -> bool:
        """从回收站彻底删除接口定义（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        conn.execute("DELETE FROM api_definitions WHERE id = ?", (definition_id,))
        conn.execute("DELETE FROM api_definition_versions WHERE definition_id = ?",
                     (definition_id,))
        conn.commit()
        return True

    @classmethod
    def list_trash_cases(cls, project_id: str = "", limit: int = 100) -> list:
        """列出回收站中的接口用例（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT * FROM api_cases WHERE deleted = 1"
        params = []
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        sql += " ORDER BY deleted_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [cls._apitest_row(r) for r in rows]

    @classmethod
    def restore_case(cls, case_id: str) -> bool:
        """从回收站恢复接口用例（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_cases WHERE id = ?", (case_id,)).fetchone()
        if not row:
            return False
        cur = conn.execute(
            "UPDATE api_cases SET deleted = 0, deleted_at = NULL WHERE id = ? AND deleted = 1",
            (case_id,))
        conn.commit()
        cls._apitest_log("case", case_id, row["name"], "restore",
                         project_id=row["project_id"])
        return cur.rowcount > 0

    @classmethod
    def purge_case(cls, case_id: str) -> bool:
        """从回收站彻底删除接口用例（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        conn.execute("DELETE FROM api_cases WHERE id = ?", (case_id,))
        conn.commit()
        return True

    @classmethod
    def list_trash_scenarios(cls, project_id: str = "",
                             limit: int = 100) -> list:
        """列出回收站中的接口场景（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT * FROM api_scenarios WHERE deleted = 1"
        params = []
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        sql += " ORDER BY deleted_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [cls._apitest_row(r) for r in rows]

    @classmethod
    def restore_scenario(cls, scenario_id: str) -> bool:
        """从回收站恢复接口场景（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_scenarios WHERE id = ?", (scenario_id,)).fetchone()
        if not row:
            return False
        cur = conn.execute(
            "UPDATE api_scenarios SET deleted = 0, deleted_at = NULL WHERE id = ? AND deleted = 1",
            (scenario_id,))
        conn.commit()
        cls._apitest_log("scenario", scenario_id, row["name"], "restore",
                         project_id=row["project_id"])
        return cur.rowcount > 0

    @classmethod
    def purge_scenario(cls, scenario_id: str) -> bool:
        """从回收站彻底删除接口场景（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        conn.execute("DELETE FROM api_scenarios WHERE id = ?", (scenario_id,))
        conn.commit()
        return True

    @classmethod
    def list_trash_mocks(cls, project_id: str = "", limit: int = 100) -> list:
        """列出回收站中的 Mock 服务（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT * FROM api_mocks WHERE deleted = 1"
        params = []
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        sql += " ORDER BY deleted_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [cls._apitest_row(r) for r in rows]

    @classmethod
    def count_trash_definitions(cls, project_id: str = "") -> int:
        """统计回收站中的接口定义数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT COUNT(*) AS c FROM api_definitions WHERE deleted = 1"
        params = []
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        row = conn.execute(sql, params).fetchone()
        return row["c"] if row else 0

    @classmethod
    def count_trash_cases(cls, project_id: str = "") -> int:
        """统计回收站中的接口用例数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT COUNT(*) AS c FROM api_cases WHERE deleted = 1"
        params = []
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        row = conn.execute(sql, tuple(params)).fetchone()
        return row["c"] if row else 0

    @classmethod
    def count_trash_scenarios(cls, project_id: str = "") -> int:
        """统计回收站中的接口场景数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT COUNT(*) AS c FROM api_scenarios WHERE deleted = 1"
        params = []
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        row = conn.execute(sql, tuple(params)).fetchone()
        return row["c"] if row else 0

    @classmethod
    def count_trash_mocks(cls, project_id: str = "") -> int:
        """统计回收站中的 Mock 服务数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT COUNT(*) AS c FROM api_mocks WHERE deleted = 1"
        params = []
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        row = conn.execute(sql, tuple(params)).fetchone()
        return row["c"] if row else 0

    @classmethod
    def restore_mock(cls, mock_id: str) -> bool:
        """从回收站恢复 Mock 服务（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_mocks WHERE id = ?", (mock_id,)).fetchone()
        if not row:
            return False
        cur = conn.execute(
            "UPDATE api_mocks SET deleted = 0, deleted_at = NULL WHERE id = ? AND deleted = 1",
            (mock_id,))
        conn.commit()
        cls._apitest_log("mock", mock_id, row["name"], "restore",
                         project_id=row["project_id"])
        return cur.rowcount > 0

    @classmethod
    def purge_mock(cls, mock_id: str) -> bool:
        """从回收站彻底删除 Mock 服务（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        conn.execute("DELETE FROM api_mocks WHERE id = ?", (mock_id,))
        conn.commit()
        return True

    # ═══════════════════════════════════════════════════
    # 批量操作
    # ═══════════════════════════════════════════════════
    @classmethod
    def batch_delete_definitions(cls, ids: list) -> int:
        """批量软删除接口定义（仓库内直连 SQL）。"""
        n = 0
        for did in ids:
            if cls.delete_definition(did):
                n += 1
        return n

    @classmethod
    def batch_restore_definitions(cls, ids: list) -> int:
        """批量恢复回收站中的接口定义（仓库内直连 SQL）。"""
        n = 0
        for did in ids:
            if cls.restore_definition(did):
                n += 1
        return n

    @classmethod
    def batch_purge_definitions(cls, ids: list) -> int:
        """批量彻底删除接口定义（仓库内直连 SQL）。"""
        n = 0
        for did in ids:
            if cls.purge_definition(did):
                n += 1
        return n

    @classmethod
    def batch_update_definitions(cls, ids: list, **fields) -> int:
        """批量更新接口定义（仓库内直连 SQL）。"""
        n = 0
        for did in ids:
            if cls.update_definition(did, **fields):
                n += 1
        return n

    @classmethod
    def batch_delete_cases(cls, ids: list) -> int:
        """批量软删除接口用例（仓库内直连 SQL）。"""
        n = 0
        for cid in ids:
            if cls.delete_api_case(cid):
                n += 1
        return n

    @classmethod
    def batch_restore_cases(cls, ids: list) -> int:
        """批量恢复回收站中的接口用例（仓库内直连 SQL）。"""
        n = 0
        for cid in ids:
            if cls.restore_case(cid):
                n += 1
        return n

    @classmethod
    def batch_purge_cases(cls, ids: list) -> int:
        """批量彻底删除接口用例（仓库内直连 SQL）。"""
        n = 0
        for cid in ids:
            if cls.purge_case(cid):
                n += 1
        return n

    @classmethod
    def batch_update_cases(cls, ids: list, **fields) -> int:
        """批量更新接口用例（仓库内直连 SQL）。"""
        n = 0
        for cid in ids:
            if cls.update_api_case(cid, **fields):
                n += 1
        return n

    @classmethod
    def batch_delete_scenarios(cls, ids: list) -> int:
        """批量软删除接口场景（仓库内直连 SQL）。"""
        n = 0
        for sid in ids:
            if cls.delete_scenario(sid):
                n += 1
        return n

    @classmethod
    def batch_restore_scenarios(cls, ids: list) -> int:
        """批量恢复回收站中的接口场景（仓库内直连 SQL）。"""
        n = 0
        for sid in ids:
            if cls.restore_scenario(sid):
                n += 1
        return n

    @classmethod
    def batch_purge_scenarios(cls, ids: list) -> int:
        """批量彻底删除接口场景（仓库内直连 SQL）。"""
        n = 0
        for sid in ids:
            if cls.purge_scenario(sid):
                n += 1
        return n

    @classmethod
    def batch_update_scenarios(cls, ids: list, **fields) -> int:
        """批量更新接口场景（仓库内直连 SQL）。"""
        n = 0
        for sid in ids:
            if cls.update_scenario(sid, **fields):
                n += 1
        return n

    @classmethod
    def batch_delete_mocks(cls, ids: list) -> int:
        """批量软删除 Mock 服务（仓库内直连 SQL）。"""
        n = 0
        for mid in ids:
            if cls.delete_mock(mid):
                n += 1
        return n

    @classmethod
    def batch_restore_mocks(cls, ids: list) -> int:
        """批量恢复回收站中的 Mock 服务（仓库内直连 SQL）。"""
        n = 0
        for mid in ids:
            if cls.restore_mock(mid):
                n += 1
        return n

    @classmethod
    def batch_purge_mocks(cls, ids: list) -> int:
        """批量彻底删除 Mock 服务（仓库内直连 SQL）。"""
        n = 0
        for mid in ids:
            if cls.purge_mock(mid):
                n += 1
        return n

    # ═══════════════════════════════════════════════════
    # 模块树（Repository 内直接 SQLite 实现，消除对旧 module_store 委托）
    # ═══════════════════════════════════════════════════
    @staticmethod
    def _module_conn():
        """模块树统一连接（apitest.db）。"""
        return Database.get_conn("apitest.db")

    @classmethod
    def get_module(cls, module_id: str) -> Optional[dict]:
        """获取单个模块。"""
        conn = cls._module_conn()
        row = conn.execute(
            "SELECT * FROM modules WHERE id = ?", (module_id,)
        ).fetchone()
        return dict(row) if row else None

    @classmethod
    def list_modules(cls, scope: str, project_id: str = "") -> list:
        """列出指定作用域下全部模块（可带 project_id 过滤）。"""
        conn = cls._module_conn()
        if project_id:
            rows = conn.execute(
                "SELECT * FROM modules WHERE scope = ? AND (project_id = ? OR project_id = '') ORDER BY pos ASC",
                (scope, project_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM modules WHERE scope = ? ORDER BY pos ASC", (scope,)
            ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def add_module(cls, scope: str = "definition", name: str = "",
                   parent_id: str = "root", project_id: str = "",
                   module_type: str = "", **kwargs) -> dict:
        """新增模块。"""
        mt = scope if scope else module_type
        mod_id = uuid.uuid4().hex[:12]
        now = time.time()
        conn = cls._module_conn()
        conn.execute(
            """INSERT INTO modules
               (id, scope, name, parent_id, pos, project_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (mod_id, mt, name, parent_id, 1, project_id, now, now),
        )
        conn.commit()
        return cls.get_module(mod_id) or {"id": mod_id}

    @classmethod
    def update_module(cls, module_id: str, name: str = None, **kwargs) -> bool:
        """更新模块名称，返回是否更新成功（bool）。"""
        conn = cls._module_conn()
        cur = conn.execute(
            "UPDATE modules SET name = ?, updated_at = ? WHERE id = ?",
            (name, time.time(), module_id),
        )
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def delete_module(cls, module_id: str) -> bool:
        """删除模块（级联删除全部子孙）。"""
        conn = cls._module_conn()

        def _collect_descendants(parent: str) -> list:
            rows = conn.execute(
                "SELECT id FROM modules WHERE parent_id = ?", (parent,)
            ).fetchall()
            ids = [r[0] for r in rows]
            for rid in ids:
                ids.extend(_collect_descendants(rid))
            return ids

        to_delete = [module_id] + _collect_descendants(module_id)
        if not to_delete:
            return False
        placeholders = ",".join(["?"] * len(to_delete))
        cur = conn.execute(
            f"DELETE FROM modules WHERE id IN ({placeholders})", to_delete
        )
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def move_module(cls, drag_node_id: str, drop_node_id: str,
                    drop_position: int = 0) -> bool:
        """移动模块到目标位置（整体置于事务内保证原子性）。

        drop_position:
          -1: 放到 dropNode 之前
           0: 放到 dropNode 内部
           1: 放到 dropNode 之后
        """
        with Database.transaction("apitest.db") as conn:
            drag = conn.execute(
                "SELECT * FROM modules WHERE id = ?", (drag_node_id,)
            ).fetchone()
            if not drag:
                return False

            now = time.time()
            if drop_position == 0:
                # 放到 dropNode 内部，即成为其子节点
                conn.execute(
                    "UPDATE modules SET parent_id = ?, pos = 1, updated_at = ? WHERE id = ?",
                    (drop_node_id, now, drag_node_id),
                )
            else:
                # 放到同级（sibling），需要根据 dropNode 的父节点和 pos 来调整
                drop = conn.execute(
                    "SELECT * FROM modules WHERE id = ?", (drop_node_id,)
                ).fetchone()
                if not drop:
                    # drop 节点不存在，放到 root
                    conn.execute(
                        "UPDATE modules SET parent_id = 'root', pos = 1, updated_at = ? WHERE id = ?",
                        (now, drag_node_id),
                    )
                    return True

                new_parent = drop["parent_id"]
                drop_pos = drop["pos"]

                if drop_position == -1:
                    # 放到 drop 之前：之后的所有同级节点 pos + 1
                    new_pos = drop_pos
                    conn.execute(
                        "UPDATE modules SET pos = pos + 1 WHERE scope = ? AND parent_id = ? AND pos >= ?",
                        (drag["scope"], new_parent, new_pos),
                    )
                else:  # drop_position == 1
                    # 放到 drop 之后
                    new_pos = drop_pos + 1
                    conn.execute(
                        "UPDATE modules SET pos = pos + 1 WHERE scope = ? AND parent_id = ? AND pos > ?",
                        (drag["scope"], new_parent, drop_pos),
                    )

                conn.execute(
                    "UPDATE modules SET parent_id = ?, pos = ?, updated_at = ? WHERE id = ?",
                    (new_parent, new_pos, now, drag_node_id),
                )
            return True

    @classmethod
    def count_modules(cls, module_type: str = "api") -> int:
        conn = cls._module_conn()
        row = conn.execute(
            "SELECT COUNT(*) FROM modules WHERE scope = ?", (module_type,)
        ).fetchone()
        return row[0] if row else 0

    @classmethod
    def _module_count_by_id(cls, include_api: bool = True) -> tuple:
        """统计每个模块下的 API 定义数量（下沉 module_store 直连 SQL）。"""
        api_count_by_module: dict = {}
        api_nodes_by_module: dict = {}
        total_api_count = 0
        if include_api:
            try:
                conn = cls._apitest_conn()
                try:
                    rows = conn.execute(
                        "SELECT id, name, method, path, protocol, module_id "
                        "FROM api_definitions "
                        "WHERE (deleted IS NULL OR deleted = 0)"
                    ).fetchall()
                    for row in rows:
                        total_api_count += 1
                        mod_id = row["module_id"] if row["module_id"] else "root"
                        api_count_by_module[mod_id] = api_count_by_module.get(mod_id, 0) + 1
                        api_nodes_by_module.setdefault(mod_id, []).append({
                            "id": row["id"],
                            "name": row["name"],
                            "type": "API",
                            "parentId": mod_id,
                            "children": [],
                            "count": 0,
                            "pos": 0,
                            "attachInfo": {
                                "method": row["method"] if row["method"] else "GET",
                                "protocol": row["protocol"] if row["protocol"] else "HTTP",
                            },
                            "path": row["path"] if row["path"] else "/",
                        })
                except Exception:
                    pass
            except Exception:
                pass
        return api_count_by_module, api_nodes_by_module, total_api_count

    @classmethod
    def build_module_tree(cls, module_type: str = "api",
                          include_api: bool = True,
                          project_id: str = "", **kwargs) -> list:
        """构建模块树（含根节点与 API 定义节点、计数）。"""
        modules = cls.list_modules(module_type, project_id=project_id)

        module_map = {}
        for m in modules:
            mid = m.get("id", "")
            module_map[mid] = {
                "id": mid,
                "name": m.get("name", ""),
                "type": "MODULE",
                "parentId": m.get("parent_id", "root"),
                "children": [],
                "pos": m.get("pos", 1),
                "count": 0,
                "attachInfo": None,
                "path": f"/{m.get('name', '')}",
            }

        api_count_by_module, api_nodes_by_module, total_api_count = \
            cls._module_count_by_id(include_api)

        root = {
            "id": "root",
            "name": "全部模块",
            "type": "MODULE",
            "parentId": "",
            "children": [],
            "count": total_api_count,
            "attachInfo": None,
            "path": "/全部模块",
        }

        for m in modules:
            mid = m.get("id", "")
            parent_id = m.get("parent_id", "root")
            node = module_map.get(mid, {
                "id": mid,
                "name": m.get("name", ""),
                "type": "MODULE",
                "parentId": parent_id,
                "children": [],
                "pos": m.get("pos", 1),
                "count": 0,
                "attachInfo": None,
                "path": f"/{m.get('name', '')}",
            })
            for api_node in api_nodes_by_module.get(mid, []):
                node["children"].append(api_node)
            node["count"] = api_count_by_module.get(mid, 0) + len(api_nodes_by_module.get(mid, []))
            if parent_id == "root":
                root["children"].append(node)
            elif parent_id in module_map:
                module_map[parent_id]["children"].append(node)
            else:
                root["children"].append(node)

        for api_node in api_nodes_by_module.get("root", []):
            root["children"].append(api_node)

        root["count"] = total_api_count
        return [root]

    # ═══════════════════════════════════════════════════
    # 执行与统计
    # ═══════════════════════════════════════════════════
    @classmethod
    def _log_execution(cls, exec_type: str, target_id: str = "",
                       target_name: str = "", method: str = "GET",
                       url: str = "", request_data: dict = None,
                       response_data: dict = None, asserts: list = None,
                       extracted_variables: dict = None,
                       passed: bool = False, response_code: int = 0,
                       duration_ms: float = 0, error: str = "",
                       detail: dict = None) -> None:
        """写入 api_execution_logs 表（下沉 execution_log.log_execution）。"""
        try:
            conn = cls._apitest_conn()
            conn.execute(
                """INSERT INTO api_execution_logs (
                    id, exec_type, target_id, target_name, method, url,
                    request_data, response_data, asserts, extracted_variables,
                    passed, response_code, duration_ms, error, detail, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()),
                 exec_type, target_id, target_name, method, url,
                 json.dumps(request_data or {}, ensure_ascii=False),
                 json.dumps(response_data or {}, ensure_ascii=False),
                 json.dumps(asserts or [], ensure_ascii=False),
                 json.dumps(extracted_variables or {}, ensure_ascii=False),
                 1 if passed else 0,
                 int(response_code or 0),
                 round(float(duration_ms or 0), 2),
                 error or '',
                 json.dumps(detail or {}, ensure_ascii=False),
                 time.time()))
            conn.commit()
        except Exception:
            pass

    _dashboard_cache = None
    _dashboard_cache_time = 0.0
    _dashboard_lock = threading.Lock()
    _DASHBOARD_CACHE_TTL = 5.0

    @classmethod
    def dashboard_stats(cls) -> dict:
        """接口测试模块仪表盘统计（带 5s 缓存，下沉 service.dashboard_stats）。"""
        now = time.time()
        with cls._dashboard_lock:
            if cls._dashboard_cache is not None and \
                    (now - cls._dashboard_cache_time) < cls._DASHBOARD_CACHE_TTL:
                return cls._dashboard_cache
        stats = {
            "definitions": cls.count_definitions(),
            "cases": cls.count_api_cases(),
            "scenarios": cls.count_scenarios(),
            "mocks": cls.count_mocks(),
            "environments": cls.count_environments(),
        }
        with cls._dashboard_lock:
            cls._dashboard_cache = stats
            cls._dashboard_cache_time = now
        return stats

    @classmethod
    def _render_request_vars(cls, req: dict, variables: dict) -> dict:
        """渲染请求中的 {{ var }} 引用（下沉 engine.render_request_vars）。"""
        from app.apitest import engine as _eng
        return _eng.render_request_vars(req, variables)

    @classmethod
    def _merge_environment(cls, req: dict, env: Optional[dict]) -> dict:
        """环境变量注入与 {{ var }} 渲染（下沉 engine.merge_environment）。"""
        from app.apitest import engine as _eng
        return _eng.merge_environment(req, env)

    @classmethod
    def run_case(cls, case_id: str, environment_id: str = "") -> dict:
        """单独执行一个接口用例（下沉 service.run_case）。"""
        from app.apitest import engine as _eng

        case = cls.get_api_case(case_id)
        if not case:
            return {"success": False, "error": "用例不存在"}

        definition = None
        if case.get("api_definition_id"):
            definition = cls.get_definition(case["api_definition_id"])

        variables = {}
        # 前置脚本
        for sp in (case.get("pre_scripts") or []):
            _eng.execute_script(sp, {"vars": variables})

        # 解析请求
        env = cls.get_environment(
            environment_id or case.get("environment_id")) if (environment_id or case.get("environment_id")) else None
        req = {}
        if case.get("request"):
            req = json.loads(case["request"])
        elif definition:
            req = {
                "protocol": definition.get("protocol", "HTTP"),
                "method": definition.get("method", "GET"),
                "path": definition.get("path", ""),
                "headers": definition.get("headers", {}),
                "body": definition.get("body", ""),
                "query": definition.get("query", {}),
            }
        req.setdefault("protocol", "HTTP")
        req = _eng.render_request_vars(req, variables)
        req = _eng.merge_environment(req, env)

        resp = _eng.execute_request(req)

        # 断言
        assert_result = _eng.evaluate_asserts(case.get("asserts") or [], resp)

        # 变量提取
        extracted = _eng.extract_variables_from_response(resp, case.get("variables") or [])

        # 后置脚本
        for sp in (case.get("post_scripts") or []):
            _eng.execute_script(sp, {"vars": variables, "response": resp})

        passed = bool(assert_result.get("passed") if isinstance(assert_result, dict) else True)

        # 测试数据落库
        cls._log_execution(
            exec_type="case",
            target_id=case_id,
            target_name=case.get("name", ""),
            method=req.get("method", "GET"),
            url=req.get("path", req.get("url", "")),
            request_data=req,
            response_data=resp,
            asserts=assert_result if isinstance(assert_result, list) else [assert_result],
            extracted_variables=extracted,
            passed=passed,
            response_code=resp.get("status_code", 0),
            duration_ms=resp.get("elapsed_ms", 0),
            error=resp.get("error", ""),
        )

        return {
            "success": True,
            "case_id": case_id,
            "name": case.get("name"),
            "request": req,
            "response": resp,
            "asserts": assert_result,
            "extracted_variables": extracted,
        }

    @classmethod
    def debug_api_call(cls, **kwargs) -> dict:
        """执行接口调试请求（下沉 mgmt.debug.debug_api_call）。"""
        method = (kwargs.get("method") or "GET").upper()
        url = kwargs.get("url") or kwargs.get("path") or ""
        headers = kwargs.get("headers") or {}
        params = kwargs.get("params") or kwargs.get("query_params") or {}
        body = kwargs.get("body") or kwargs.get("request_body") or ""
        body_type = kwargs.get("body_type", "json")
        timeout = kwargs.get("timeout", 30)

        start = time.time()
        result = {
            'method': method,
            'url': url,
            'success': False,
            'response_code': 0,
            'response_data': '',
            'duration_ms': 0,
            'error': '',
        }
        try:
            # 构建 URL
            if params:
                qs = urllib.parse.urlencode(params)
                sep = '&' if '?' in url else '?'
                url = f"{url}{sep}{qs}"

            req_headers = dict(headers or {})
            data_bytes = None
            if body and method in ('POST', 'PUT', 'PATCH'):
                data_bytes = body.encode('utf-8')
                if body_type == 'json' and 'Content-Type' not in req_headers:
                    req_headers['Content-Type'] = 'application/json'

            req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    resp_data = resp.read().decode('utf-8', errors='replace')
                    result.update({
                        'success': True,
                        'response_code': resp.status,
                        'response_data': resp_data[:5000],
                    })
            except urllib.error.HTTPError as e:
                body_data = e.read().decode('utf-8', errors='replace') if hasattr(e, 'read') else ''
                result.update({
                    'response_code': e.code,
                    'response_data': body_data[:5000],
                    'error': f'HTTP {e.code}: {e.reason}',
                })
            except Exception as e:
                result['error'] = str(e)

            result['duration_ms'] = round((time.time() - start) * 1000, 2)

            # 记录调试日志到统一执行流水
            cls._log_execution(
                exec_type="debug",
                target_id=kwargs.get("case_id") or "",
                target_name="",
                method=method,
                url=url,
                request_data=json.dumps({'headers': headers, 'params': params, 'body': body}),
                response_data=result['response_data'],
                asserts=[],
                extracted_variables={},
                passed=bool(result['success']),
                response_code=result['response_code'],
                duration_ms=result['duration_ms'],
                error=result.get('error', ''),
            )
            return result
        except Exception as e:
            result['error'] = str(e)
            result['duration_ms'] = round((time.time() - start) * 1000, 2)
            cls._log_execution(
                exec_type="debug",
                target_id=kwargs.get("case_id") or "",
                target_name="",
                method=method,
                url=url,
                request_data='',
                response_code=0,
                response_data='',
                asserts=[],
                extracted_variables={},
                passed=False,
                duration_ms=result['duration_ms'],
                error=str(e),
            )
            return result

    @classmethod
    def _resolve_step_request(cls, step: dict, definition: dict,
                              case: dict, variables: dict) -> dict:
        """解析步骤的请求对象，合并定义、用例与环境（下沉 scenario_runner）。"""
        from app.apitest import engine as _eng
        if case and case.get("request"):
            req = json.loads(case["request"])
        elif definition:
            req = {
                "protocol": definition.get("protocol", "HTTP"),
                "method": definition.get("method", "GET"),
                "path": definition.get("path", ""),
                "headers": definition.get("headers", {}),
                "body": definition.get("body", ""),
                "query": definition.get("query", {}),
                "params": definition.get("params", {}),
            }
        else:
            req = dict(step.get("request") or {})

        req.setdefault("protocol", definition.get("protocol", "HTTP") if definition else "HTTP")
        req.setdefault("method", step.get("method", "GET"))
        req = _eng.render_request_vars(req, variables)
        return req

    @classmethod
    def run_scenario(cls, scenario: dict, environment_id: str = "") -> dict:
        """执行接口场景（下沉 scenario_runner.run_scenario）。"""
        from app.apitest import engine as _eng

        steps = scenario.get("steps") or []
        env = None
        env_id = environment_id or scenario.get("environment_id") or ""
        if env_id:
            env = cls.get_environment(env_id)

        variables = {}
        step_results = []
        all_passed = True

        # 执行环境前置脚本
        if env and env.get("script"):
            _eng.execute_script({"type": "python", "code": env["script"], "name": "环境脚本"},
                                {"vars": variables})

        for idx, step in enumerate(steps):
            stype = step.get("type", "case")
            result = {"index": idx, "type": stype,
                      "name": step.get("name", f"步骤{idx+1}"), "passed": False}

            if stype == "controller":
                ctrl = dict(step.get("controller") or {})
                ctrl.setdefault("type", "loop")
                cr = _eng.evaluate_logic_controller(ctrl, {"vars": variables})
                result.update({"passed": cr["passed"], "message": cr["message"],
                              "iterations": cr.get("iterations"),
                              "controller_type": ctrl.get("type")})
                if ctrl.get("type") == "random":
                    variables[f"random_{idx}"] = cr.get("random_value", 0)
                all_passed = all_passed and cr["passed"]
            elif stype in ("case", "definition"):
                definition = None
                case = None
                if step.get("case_id"):
                    case = cls.get_api_case(step["case_id"])
                    if case and case.get("api_definition_id"):
                        definition = cls.get_definition(case["api_definition_id"])
                elif step.get("definition_id"):
                    definition = cls.get_definition(step["definition_id"])

                if not definition and not case:
                    result["message"] = "未找到对应的接口定义或用例"
                    step_results.append(result)
                    all_passed = False
                    continue

                # 前置脚本
                pre_scripts = step.get("pre_scripts") or (case.get("pre_scripts") if case else []) or []
                for sp in pre_scripts:
                    _eng.execute_script(sp, {"vars": variables})

                # 解析请求
                req = cls._resolve_step_request(step, definition, case, variables)
                # 合并环境
                step_env = env
                if not step_env and case and case.get("environment_id"):
                    step_env = cls.get_environment(case["environment_id"])
                req = _eng.merge_environment(req, step_env)

                # 执行请求
                resp = _eng.execute_request(req)

                # 断言
                asserts = step.get("asserts") or (case.get("asserts") if case else []) or []
                if asserts:
                    ar = _eng.evaluate_asserts(asserts, resp)
                    result["asserts"] = ar
                    result["passed"] = ar["passed"]
                    all_passed = all_passed and ar["passed"]
                else:
                    result["passed"] = resp.get("ok", False)
                    all_passed = all_passed and result["passed"]

                # 变量提取
                var_rules = step.get("variables") or (case.get("variables") if case else []) or []
                if var_rules:
                    extracted = _eng.extract_variables_from_response(resp, var_rules)
                    variables.update(extracted)
                    result["extracted"] = extracted

                result["status_code"] = resp.get("status_code")
                result["elapsed_ms"] = resp.get("elapsed_ms", 0)
                result["message"] = f"{definition.get('method','GET') if definition else 'HTTP'} {req.get('path','')}"
                if resp.get("error"):
                    result["error"] = resp["error"]

                # 后置脚本
                post_scripts = step.get("post_scripts") or (case.get("post_scripts") if case else []) or []
                for sp in post_scripts:
                    _eng.execute_script(sp, {"vars": variables, "response": resp})

            step_results.append(result)

        # 测试数据落库
        cls._log_execution(
            exec_type="scenario",
            target_id=scenario.get("id", ""),
            target_name=scenario.get("name", ""),
            method="SCENARIO",
            url=scenario.get("name", ""),
            request_data={"steps": scenario.get("steps", [])},
            response_data={"steps": step_results, "final_variables": variables},
            asserts=[],
            extracted_variables=variables,
            passed=all_passed,
            response_code=0,
            duration_ms=0,
            error="",
            detail={
                "total_steps": len(step_results),
                "passed_steps": sum(1 for s in step_results if s.get("passed")),
            },
        )

        return {
            "scenario_id": scenario.get("id"),
            "name": scenario.get("name"),
            "passed": all_passed,
            "total_steps": len(step_results),
            "passed_steps": sum(1 for s in step_results if s.get("passed")),
            "steps": step_results,
            "final_variables": variables,
        }

    @classmethod
    def import_postman(cls, content: str, project_id: str = "") -> dict:
        """从 Postman Collection JSON 导入接口定义（下沉 importer.import_postman）。"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON 解析失败: {e}", "imported": 0}

        base_url = ""
        if data.get("variable"):
            for v in data["variable"]:
                if v.get("key", "").lower() in ("baseurl", "base_url", "host"):
                    base_url = v.get("value", "")
                    break

        items = data.get("item", [])
        imported = 0
        errors = []

        def _walk(items_list, folder=""):
            nonlocal imported
            for it in items_list:
                if it.get("item"):
                    _walk(it["item"], folder + it.get("name", "") + "/")
                elif it.get("request"):
                    try:
                        req_obj = it.get("request", {})
                        method = req_obj.get("method", "GET")
                        url_obj = req_obj.get("url", {})
                        if isinstance(url_obj, str):
                            raw_url = url_obj
                            query = {}
                        else:
                            raw_url = url_obj.get("raw", "")
                            query = {}
                            if url_obj.get("query"):
                                for q in url_obj["query"]:
                                    if q.get("key"):
                                        query[q["key"]] = q.get("value", "")
                        headers = {}
                        for h in req_obj.get("header", []) or []:
                            if h.get("key"):
                                headers[h["key"]] = h.get("value", "")
                        body = ""
                        body_obj = req_obj.get("body", {})
                        if isinstance(body_obj, dict):
                            if body_obj.get("raw"):
                                body = body_obj["raw"]
                            elif body_obj.get("urlencoded"):
                                pairs = []
                                for kv in body_obj["urlencoded"]:
                                    if kv.get("key"):
                                        pairs.append(f"{kv['key']}={kv.get('value','')}")
                                body = "&".join(pairs)
                            elif body_obj.get("formdata"):
                                body = json.dumps(body_obj.get("formdata"), ensure_ascii=False)
                        path = raw_url
                        if base_url and raw_url.startswith(base_url):
                            path = raw_url[len(base_url):]
                        name = folder + it.get("name", "未命名接口")
                        cls.create_definition(
                            name=name, protocol="HTTP", method=method, path=path,
                            headers=headers, body=body, query=query,
                            description="来自 Postman 导入", tags=["postman"],
                            project_id=project_id,
                        )
                        imported += 1
                    except Exception as ex:
                        errors.append(str(ex))

        _walk(items)
        return {"success": True, "imported": imported, "errors": errors, "base_url": base_url}

    @classmethod
    def import_swagger(cls, content: str, project_id: str = "") -> dict:
        """从 Swagger 2.0 / OpenAPI 3.x JSON 导入接口定义（下沉 importer.import_swagger）。"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON 解析失败: {e}", "imported": 0}

        paths = data.get("paths", {})
        servers = data.get("servers", [])
        base_url = servers[0].get("url", "") if servers else ""
        if not base_url and data.get("host"):
            base_url = f"{'https' if data.get('schemes') and 'https' in data['schemes'] else 'http'}://{data['host']}"
            base_path = data.get("basePath", "")
            base_url += base_path

        imported = 0
        errors = []
        for path, methods in (paths or {}).items():
            for method, op in (methods or {}).items():
                if method.lower() not in ("get", "post", "put", "delete", "patch", "head", "options"):
                    continue
                try:
                    summary = op.get("summary", "") or op.get("operationId", "") or path
                    tags = list(op.get("tags", [])) or ["swagger"]
                    query = {}
                    if op.get("parameters"):
                        for p in op["parameters"]:
                            if p.get("in") == "query":
                                query[p.get("name", "")] = p.get("example", "")
                    cls.create_definition(
                        name=summary, protocol="HTTP", method=method.upper(), path=path,
                        headers={"Content-Type": "application/json"}, query=query,
                        description="来自 Swagger/OpenAPI 导入", tags=tags,
                        project_id=project_id,
                    )
                    imported += 1
                except Exception as ex:
                    errors.append(str(ex))
        return {"success": True, "imported": imported, "errors": errors, "base_url": base_url}

    @classmethod
    def import_har(cls, content: str, project_id: str = "") -> dict:
        """从 HAR (HTTP Archive) 文件导入接口定义（下沉 importer.import_har）。"""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON 解析失败: {e}", "imported": 0}

        entries = data.get("log", {}).get("entries", [])
        imported = 0
        errors = []

        for entry in entries:
            try:
                req = entry.get("request", {})
                method = req.get("method", "GET")
                url = req.get("url", "")
                headers = {}
                for h in req.get("headers", []):
                    if h.get("name"):
                        headers[h["name"]] = h.get("value", "")
                from urllib.parse import parse_qs, urlparse
                parsed = urlparse(url)
                path = parsed.path or "/"
                query = {k: v[0] if v else "" for k, v in parse_qs(parsed.query).items()}
                body = ""
                post_data = req.get("postData", {})
                if isinstance(post_data, dict):
                    body = post_data.get("text", "")
                name = f"{method} {path}"
                cls.create_definition(
                    name=name, protocol="HTTP", method=method, path=path,
                    headers=headers, body=body, query=query,
                    description="来自 HAR 导入", tags=["har"],
                    project_id=project_id,
                )
                imported += 1
            except Exception as ex:
                errors.append(str(ex))
        return {"success": True, "imported": imported, "errors": errors}

    @classmethod
    def import_content(cls, content: str, fmt: str = "auto",
                       project_id: str = "") -> dict:
        """自动识别格式导入（下沉 importer.import_content）。"""
        f = fmt.lower()
        if f == "auto":
            try:
                data = json.loads(content)
                if "paths" in data and ("swagger" in data or "openapi" in data):
                    return cls.import_swagger(content, project_id)
                if "item" in data and ("info" in data or "variable" in data):
                    return cls.import_postman(content, project_id)
                if "log" in data and "entries" in data.get("log", {}):
                    return cls.import_har(content, project_id)
                return {"success": False, "error": "无法识别的接口文档格式", "imported": 0}
            except json.JSONDecodeError:
                return {"success": False, "error": "请输入有效的 JSON 内容", "imported": 0}
        if f in ("swagger", "openapi", "openapi3"):
            return cls.import_swagger(content, project_id)
        if f == "postman":
            return cls.import_postman(content, project_id)
        if f in ("har", "httparchive"):
            return cls.import_har(content, project_id)
        return {"success": False, "error": f"不支持的导入格式: {f}", "imported": 0}

    @classmethod
    def assert_types(cls) -> dict:
        """运行时断言类型字典（引用 app.apitest.engine 常量）。"""
        from app.apitest import engine
        return engine.ASSERT_TYPES

    @classmethod
    def list_execution_logs(cls, exec_type: str = "", target_id: str = "",
                            limit: int = 100, offset: int = 0,
                            keyword: str = "") -> list:
        """查询测试执行记录（仓库内直连 SQL）。"""
        try:
            conn = cls._apitest_conn()
            sql = "SELECT * FROM api_execution_logs"
            conds, params = [], []
            if exec_type:
                conds.append("exec_type = ?")
                params.append(exec_type)
            if target_id:
                conds.append("target_id = ?")
                params.append(target_id)
            if keyword:
                conds.append("(target_name LIKE ? OR url LIKE ?)")
                params.append(f"%{keyword}%")
                params.append(f"%{keyword}%")
            if conds:
                sql += " WHERE " + " AND ".join(conds)
            sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.append(int(limit))
            params.append(int(offset or 0))
            rows = conn.execute(sql, params).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                for k in ("request_data", "response_data", "asserts",
                          "extracted_variables", "detail"):
                    try:
                        d[k] = json.loads(
                            d.get(k) or ("[]" if k == "asserts" else "{}"))
                    except Exception:
                        pass
                result.append(d)
            return result
        except Exception:
            return []

    @classmethod
    def count_execution_logs(cls, exec_type: str = "",
                             target_id: str = "", keyword: str = "") -> int:
        """统计测试执行记录总数（仓库内直连 SQL）。"""
        try:
            conn = cls._apitest_conn()
            sql = "SELECT COUNT(*) FROM api_execution_logs"
            conds, params = [], []
            if exec_type:
                conds.append("exec_type = ?")
                params.append(exec_type)
            if target_id:
                conds.append("target_id = ?")
                params.append(target_id)
            if keyword:
                conds.append("(target_name LIKE ? OR url LIKE ?)")
                params.append(f"%{keyword}%")
                params.append(f"%{keyword}%")
            if conds:
                sql += " WHERE " + " AND ".join(conds)
            row = conn.execute(sql, params).fetchone()
            return int(row[0]) if row else 0
        except Exception:
            return 0

    @classmethod
    def clear_execution_logs(cls, exec_type: str = "") -> int:
        """清空测试执行记录（仓库内直连 SQL）。"""
        try:
            conn = cls._apitest_conn()
            if exec_type:
                cur = conn.execute(
                    "DELETE FROM api_execution_logs WHERE exec_type = ?",
                    (exec_type,))
            else:
                cur = conn.execute("DELETE FROM api_execution_logs")
            conn.commit()
            return cur.rowcount
        except Exception:
            return 0

    # ═══════════════════════════════════════════════════
    # 关注 / 日志
    # ═══════════════════════════════════════════════════
    @classmethod
    def list_followers(cls, resource_id: str,
                       resource_type: str = "") -> list:
        """列出资源的关注者（仓库内直连 SQL）。"""
        try:
            conn = cls._apitest_conn()
            rows = conn.execute(
                "SELECT user_id FROM api_follows "
                "WHERE resource_type = ? AND resource_id = ?",
                (resource_type, resource_id)).fetchall()
            return [r["user_id"] for r in rows]
        except Exception:
            return []

    @classmethod
    def follow_resource(cls, resource_id: str, resource_type: str = "",
                        user_id: str = "") -> bool:
        """关注资源（仓库内直连 SQL）。"""
        try:
            conn = cls._apitest_conn()
            conn.execute(
                """INSERT OR IGNORE INTO api_follows
                   (id, resource_type, resource_id, user_id, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (cls._new_id(), resource_type, resource_id,
                 user_id or "admin", cls._now()))
            conn.commit()
            return True
        except Exception:
            return False

    @classmethod
    def toggle_follow(cls, resource_id: str, resource_type: str = "",
                      user_id: str = "") -> bool:
        """单端点关注/取消关注，返回翻转后状态（仓库内直连 SQL）。"""
        try:
            conn = cls._apitest_conn()
            uid = user_id or "admin"
            followed = cls.is_followed(resource_id, resource_type, uid)
            if followed:
                conn.execute(
                    "DELETE FROM api_follows WHERE resource_type = ? "
                    "AND resource_id = ? AND user_id = ?",
                    (resource_type, resource_id, uid))
            else:
                conn.execute(
                    """INSERT OR IGNORE INTO api_follows
                       (id, resource_type, resource_id, user_id, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (cls._new_id(), resource_type, resource_id, uid, cls._now()))
            conn.commit()
            return not followed
        except Exception:
            return False

    @classmethod
    def is_followed(cls, resource_id: str, resource_type: str = "",
                    user_id: str = "") -> bool:
        """判断是否已关注（仓库内直连 SQL）。"""
        try:
            conn = cls._apitest_conn()
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM api_follows "
                "WHERE resource_type = ? AND resource_id = ? AND user_id = ?",
                (resource_type, resource_id, user_id or "admin")).fetchone()
            return (row["c"] > 0) if row else False
        except Exception:
            return False

    @classmethod
    def unfollow_resource(cls, resource_id: str, resource_type: str = "",
                          user_id: str = "") -> bool:
        """取消关注资源（仓库内直连 SQL）。"""
        try:
            conn = cls._apitest_conn()
            cur = conn.execute(
                "DELETE FROM api_follows WHERE resource_type = ? "
                "AND resource_id = ? AND user_id = ?",
                (resource_type, resource_id, user_id or "admin"))
            conn.commit()
            return cur.rowcount > 0
        except Exception:
            return False


    @classmethod
    def list_operation_logs(cls, resource_type: str = "",
                            resource_id: str = "", project_id: str = "",
                            limit: int = 100, offset: int = 0,
                            **kwargs) -> list:
        """列出操作日志（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT * FROM api_operation_logs WHERE 1=1"
        params = []
        if resource_type:
            sql += " AND resource_type = ?"
            params.append(resource_type)
        if resource_id:
            sql += " AND resource_id = ?"
            params.append(resource_id)
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(int(offset or 0))
        rows = conn.execute(sql, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["detail"] = cls._json_loads(d.get("detail"), {})
            result.append(d)
        return result

    @classmethod
    def count_operation_logs(cls, resource_type: str = "",
                             resource_id: str = "", project_id: str = "") -> int:
        """统计操作日志条数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT COUNT(*) FROM api_operation_logs WHERE 1=1"
        params = []
        if resource_type:
            sql += " AND resource_type = ?"
            params.append(resource_type)
        if resource_id:
            sql += " AND resource_id = ?"
            params.append(resource_id)
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        row = conn.execute(sql, params).fetchone()
        return int(row[0]) if row else 0

    @classmethod
    def clear_operation_logs(cls, days: int = 30) -> int:
        """清理 days 天之前的操作日志（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        cutoff = cls._now() - days * 86400
        cur = conn.execute(
            "DELETE FROM api_operation_logs WHERE created_at < ?", (cutoff,))
        conn.commit()
        return cur.rowcount

    # ═══════════════════════════════════════════════════
    # 前端兼容（V1 前端兼容层，已下沉自 app.api_testing.management）
    # ═══════════════════════════════════════════════════
    @classmethod
    def mgmt_import_from_postman(cls, data: dict) -> dict:
        """从 Postman Collection JSON 导入 V1 接口定义（下沉 mgmt.imports）。"""
        imported = 0
        errors = []
        items = data.get('item', []) if isinstance(data, dict) else []

        def walk_items(items_list):
            result = []
            for item in items_list:
                if 'item' in item:
                    result.extend(walk_items(item['item']))
                elif 'request' in item:
                    result.append(item)
            return result

        try:
            all_requests = walk_items(items)
            for req_item in all_requests:
                request = req_item.get('request', {})
                name = req_item.get('name', request.get('name', 'unnamed'))
                method = request.get('method', 'GET')
                url_obj = request.get('url', {})
                if isinstance(url_obj, dict):
                    path = '/'.join(url_obj.get('path', []))
                    query_params = {}
                    for qp in url_obj.get('query', []):
                        if isinstance(qp, dict):
                            query_params[qp.get('key', '')] = qp.get('value', '')
                else:
                    path = str(url_obj)
                    query_params = {}

                body = request.get('body', {})
                body_content = ''
                if isinstance(body, dict):
                    raw = body.get('raw', '')
                    body_content = str(raw) if raw else ''

                headers = {}
                for h in request.get('header', []):
                    if isinstance(h, dict):
                        headers[h.get('key', '')] = h.get('value', '')

                cls.mgmt_create_api_definition(
                    name=name,
                    method=method,
                    path=path,
                    request_headers=headers,
                    request_params=query_params,
                    request_body=body_content,
                    tags=['postman-import'],
                )
                imported += 1
        except Exception as e:
            errors.append(str(e))

        return {'imported': imported, 'errors': errors}

    @classmethod
    def mgmt_import_from_swagger(cls, data: dict) -> dict:
        """从 Swagger/OpenAPI JSON 导入 V1 接口定义（下沉 mgmt.imports）。"""
        imported = 0
        errors = []
        try:
            paths = data.get('paths', {})
            for path, methods in paths.items():
                for method, op in methods.items():
                    if method.lower() not in ('get', 'post', 'put', 'delete', 'patch', 'head', 'options'):
                        continue
                    name = op.get('summary', op.get('operationId', f"{method.upper()} {path}"))
                    parameters = {}
                    for p in op.get('parameters', []):
                        if isinstance(p, dict):
                            parameters[p.get('name', '')] = p.get('schema', {}).get('default', '') if isinstance(p.get('schema'), dict) else ''

                    request_body = ''
                    rb = op.get('requestBody', {})
                    if isinstance(rb, dict):
                        content_map = rb.get('content', {})
                        if 'application/json' in content_map:
                            schema = content_map['application/json'].get('schema', {})
                            request_body = json.dumps(schema, ensure_ascii=False, indent=2) if schema else ''

                    tags = op.get('tags', [])
                    cls.mgmt_create_api_definition(
                        name=name,
                        method=method.upper(),
                        path=path,
                        description=op.get('description', ''),
                        request_params=parameters,
                        request_body=request_body,
                        tags=tags,
                    )
                    imported += 1
        except Exception as e:
            errors.append(str(e))

        return {'imported': imported, 'errors': errors}

    @classmethod
    def mgmt_list_api_definitions(cls, search: str = "", method: str = "",
                                  protocol: str = "", limit: int = 100,
                                  project_id: str = "") -> list:
        """列出 V1 接口定义（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT * FROM api_definitions WHERE (deleted IS NULL OR deleted = 0)"
        params = []
        if search:
            sql += " AND (name LIKE ? OR path LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        if method:
            sql += " AND method = ?"
            params.append(method.upper())
        if protocol:
            sql += " AND protocol = ?"
            params.append(protocol)
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            for key in ('request_headers', 'request_params',
                        'response_headers', 'tags'):
                try:
                    d[key] = json.loads(d.get(key) or '{}')
                except Exception:
                    d[key] = {}
            result.append(d)
        return result

    @classmethod
    def mgmt_create_api_definition(cls, name: str, method: str = "GET",
                                   path: str = "", protocol: str = "HTTP",
                                   description: str = "",
                                   request_headers: dict = None,
                                   request_params: dict = None,
                                   request_body: str = "",
                                   request_body_type: str = "json",
                                   response_code: str = "200",
                                   response_headers: dict = None,
                                   response_body: str = "",
                                   response_body_type: str = "json",
                                   tags: list = None,
                                   project_id: str = "", **kwargs) -> dict:
        """创建 V1 接口定义（仓库内直连 SQL）。"""
        def_id = cls._new_id()
        now = cls._now()
        conn = cls._apitest_conn()
        conn.execute(
            """INSERT INTO api_definitions (
                id, name, method, path, protocol, description,
                request_headers, request_params, request_body, request_body_type,
                response_code, response_headers, response_body, response_body_type,
                tags, created_at, updated_at, project_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (def_id, name, method.upper(), path, protocol, description,
             json.dumps(request_headers or {}),
             json.dumps(request_params or {}),
             request_body or '', request_body_type,
             response_code,
             json.dumps(response_headers or {}),
             response_body or '', response_body_type,
             json.dumps(tags or []), now, now, project_id))
        conn.commit()
        return cls.mgmt_get_api_definition(def_id)

    @classmethod
    def mgmt_get_api_definition(cls, def_id: str) -> Optional[dict]:
        """获取 V1 接口定义（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_definitions WHERE id = ?", (def_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ('request_headers', 'request_params',
                    'response_headers', 'tags'):
            try:
                d[key] = json.loads(d.get(key) or '{}')
            except Exception:
                d[key] = {}
        return d

    @classmethod
    def mgmt_update_api_definition(cls, def_id: str, **kwargs) -> Optional[dict]:
        """更新 V1 接口定义（仓库内直连 SQL）。"""
        allowed = {
            'name', 'method', 'path', 'protocol', 'description',
            'request_headers', 'request_params', 'request_body', 'request_body_type',
            'response_code', 'response_headers', 'response_body', 'response_body_type',
            'tags',
        }
        updates = []
        params = []
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                if isinstance(v, (dict, list)):
                    v = json.dumps(v)
                updates.append(f"{k} = ?")
                params.append(v)
        if not updates:
            return cls.mgmt_get_api_definition(def_id)
        updates.append("updated_at = ?")
        params.append(cls._now())
        params.append(def_id)
        conn = cls._apitest_conn()
        conn.execute(
            f"UPDATE api_definitions SET {', '.join(updates)} WHERE id = ?",
            params)
        conn.commit()
        return cls.mgmt_get_api_definition(def_id)

    @classmethod
    def mgmt_delete_api_definition(cls, def_id: str,
                                   permanent: bool = False) -> bool:
        """删除 V1 接口定义（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        if permanent:
            conn.execute("DELETE FROM api_definitions WHERE id = ?", (def_id,))
        else:
            conn.execute(
                "UPDATE api_definitions SET deleted = 1, deleted_at = ? "
                "WHERE id = ? AND (deleted IS NULL OR deleted = 0)",
                (cls._now(), def_id))
        conn.commit()
        return True

    @classmethod
    def mgmt_list_trash_definitions(cls, limit: int = 100) -> list:
        """列出回收站中的 V1 接口定义（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        rows = conn.execute(
            "SELECT * FROM api_definitions WHERE deleted = 1 "
            "ORDER BY deleted_at DESC LIMIT ?", (limit,)).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            for key in ('request_headers', 'request_params',
                        'response_headers', 'tags'):
                try:
                    d[key] = json.loads(d.get(key) or '{}')
                except Exception:
                    d[key] = {}
            result.append(d)
        return result

    @classmethod
    def mgmt_restore_definition(cls, def_id: str) -> bool:
        """从回收站恢复 V1 接口定义（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        cur = conn.execute(
            "UPDATE api_definitions SET deleted = 0, deleted_at = NULL "
            "WHERE id = ? AND deleted = 1", (def_id,))
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def mgmt_list_api_test_cases(cls, search: str = "",
                                 definition_id: str = "",
                                 environment_id: str = "", enabled=None,
                                 limit: int = 100, project_id: str = "") -> list:
        """列出 V1 api_test_cases（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        sql = "SELECT * FROM api_test_cases WHERE (deleted IS NULL OR deleted = 0)"
        params = []
        if search:
            sql += " AND (name LIKE ? OR path LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if definition_id:
            sql += " AND definition_id = ?"
            params.append(definition_id)
        if environment_id:
            sql += " AND environment_id = ?"
            params.append(environment_id)
        if enabled is not None:
            sql += " AND enabled = ?"
            params.append(1 if enabled else 0)
        if project_id:
            sql += " AND (project_id = ? OR project_id = '')"
            params.append(project_id)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [cls._decode_v1_test_case(dict(r)) for r in rows]

    @classmethod
    def mgmt_create_api_test_case(cls, name: str, definition_id: str = None,
                                  method: str = "GET", path: str = "",
                                  request_headers: dict = None,
                                  request_params: dict = None,
                                  request_body: str = "",
                                  request_body_type: str = "json",
                                  assertions: list = None,
                                  pre_scripts: list = None,
                                  post_scripts: list = None,
                                  pre_sql: str = "", post_sql: str = "",
                                  variables: dict = None,
                                  environment_id: str = None,
                                  timeout: int = 30, retry_count: int = 0,
                                  project_id: str = "", **kwargs) -> dict:
        """创建 V1 api_test_case（仓库内直连 SQL）。"""
        case_id = cls._new_id()
        now = cls._now()
        conn = cls._apitest_conn()
        conn.execute(
            """INSERT INTO api_test_cases
               (id, name, definition_id, method, path,
                request_headers, request_params, request_body, request_body_type,
                assertions, pre_scripts, post_scripts, pre_sql, post_sql,
                variables, environment_id, timeout, retry_count,
                created_at, updated_at, project_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (case_id, name, definition_id, method.upper(), path,
             json.dumps(request_headers or {}, ensure_ascii=False),
             json.dumps(request_params or {}, ensure_ascii=False),
             request_body or '', request_body_type,
             json.dumps(assertions or [], ensure_ascii=False),
             json.dumps(pre_scripts or [], ensure_ascii=False),
             json.dumps(post_scripts or [], ensure_ascii=False),
             pre_sql or '', post_sql or '',
             json.dumps(variables or {}, ensure_ascii=False),
             environment_id, timeout, retry_count,
             now, now, project_id))
        conn.commit()
        return cls.mgmt_get_api_test_case(case_id)

    @classmethod
    def mgmt_get_api_test_case(cls, case_id: str) -> Optional[dict]:
        """获取 V1 api_test_case（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_test_cases WHERE id = ?", (case_id,)).fetchone()
        return cls._decode_v1_test_case(dict(row)) if row else None

    @classmethod
    def mgmt_update_api_test_case(cls, case_id: str, **kwargs) -> Optional[dict]:
        """更新 V1 api_test_case（仓库内直连 SQL）。"""
        allowed = {
            'name', 'definition_id', 'method', 'path',
            'request_headers', 'request_params', 'request_body', 'request_body_type',
            'assertions', 'pre_scripts', 'post_scripts', 'pre_sql', 'post_sql',
            'variables', 'environment_id', 'timeout', 'retry_count',
            'enabled', 'status',
        }
        updates = []
        params = []
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                if isinstance(v, (dict, list)):
                    v = json.dumps(v)
                updates.append(f"{k} = ?")
                params.append(v)
        if not updates:
            return cls.mgmt_get_api_test_case(case_id)
        updates.append("updated_at = ?")
        params.append(cls._now())
        params.append(case_id)
        conn = cls._apitest_conn()
        conn.execute(
            f"UPDATE api_test_cases SET {', '.join(updates)} WHERE id = ?",
            params)
        conn.commit()
        return cls.mgmt_get_api_test_case(case_id)

    @classmethod
    def mgmt_delete_api_test_case(cls, case_id: str,
                                  permanent: bool = False) -> bool:
        """删除 V1 api_test_case（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        if permanent:
            conn.execute("DELETE FROM api_test_cases WHERE id = ?", (case_id,))
        else:
            conn.execute(
                "UPDATE api_test_cases SET deleted = 1, deleted_at = ? "
                "WHERE id = ? AND (deleted IS NULL OR deleted = 0)",
                (cls._now(), case_id))
        conn.commit()
        return True

    @classmethod
    def mgmt_restore_case(cls, case_id: str) -> bool:
        """从回收站恢复 V1 api_test_case（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        cur = conn.execute(
            "UPDATE api_test_cases SET deleted = 0, deleted_at = NULL "
            "WHERE id = ? AND deleted = 1", (case_id,))
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def mgmt_list_trash_cases(cls, limit: int = 100) -> list:
        """列出回收站中的 V1 api_test_case（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        rows = conn.execute(
            "SELECT * FROM api_test_cases WHERE deleted = 1 "
            "ORDER BY deleted_at DESC LIMIT ?", (limit,)).fetchall()
        return [cls._decode_v1_test_case(dict(r)) for r in rows]

    @classmethod
    def mgmt_list_scenarios(cls, limit: int = 100) -> list:
        """列出 V1 场景（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        rows = conn.execute(
            "SELECT * FROM api_scenarios WHERE (deleted IS NULL OR deleted = 0) "
            "ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [cls._decode_v1_scenario(dict(r)) for r in rows]

    @classmethod
    def mgmt_create_scenario(cls, name: str, description: str = "",
                             steps: list = None, environment_id: str = None,
                             project_id: str = "", **kwargs) -> dict:
        """创建 V1 场景（仓库内直连 SQL）。"""
        sc_id = cls._new_id()
        now = cls._now()
        conn = cls._apitest_conn()
        conn.execute(
            """INSERT INTO api_scenarios
               (id, name, description, steps, environment_id,
                created_at, updated_at, project_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (sc_id, name, description,
             json.dumps(steps or [], ensure_ascii=False),
             environment_id, now, now, project_id))
        conn.commit()
        return cls.mgmt_get_scenario(sc_id)

    @classmethod
    def mgmt_execute_scenario(cls, scenario_id: str,
                              environment_id: Optional[str] = None) -> dict:
        """执行 V1 接口场景（下沉 mgmt.execution.execute_scenario）。"""
        scenario = cls.mgmt_get_scenario(scenario_id)
        if not scenario:
            return {'success': False, 'error': '场景不存在'}

        env = None
        if environment_id:
            env = cls.get_environment(environment_id)
        elif scenario.get('environment_id'):
            env = cls.get_environment(scenario['environment_id'])

        steps = scenario.get('steps', [])
        results = []
        all_success = True

        for step in sorted(steps, key=lambda x: x.get('order', 0)):
            if not step.get('enabled', True):
                continue
            case_id = step.get('case_id')
            case = cls.mgmt_get_api_test_case(case_id) if case_id else None
            if not case:
                results.append({
                    'step': step.get('order', 0),
                    'case_id': case_id,
                    'success': False,
                    'error': '用例不存在',
                })
                all_success = False
                continue

            # 构建完整 URL
            base_url = env.get('base_url', '') if env else ''
            path = case.get('path', '')
            url = f"{base_url.rstrip('/')}/{path.lstrip('/')}" if base_url else path

            result = cls.debug_api_call(
                method=case.get('method', 'GET'),
                url=url,
                headers=case.get('request_headers', {}),
                params=case.get('request_params', {}),
                body=case.get('request_body', ''),
                timeout=case.get('timeout', 30),
            )
            results.append({
                'step': step.get('order', 0),
                'case_id': case_id,
                'case_name': case.get('name', ''),
                'method': case.get('method', ''),
                'url': url,
                'success': result['success'],
                'response_code': result['response_code'],
                'duration_ms': result['duration_ms'],
                'error': result.get('error', ''),
            })
            if not result['success']:
                all_success = False

        # 测试数据落库
        cls._log_execution(
            exec_type="scenario",
            target_id=scenario_id,
            target_name=scenario.get('name', ''),
            method="SCENARIO",
            url=scenario.get('name', ''),
            request_data={'steps': steps},
            response_data={'results': results},
            asserts=[],
            extracted_variables={},
            passed=all_success,
            response_code=0,
            duration_ms=0,
            error="",
            detail={
                'total_steps': len(results),
                'passed_steps': sum(1 for r in results if r['success']),
                'failed_steps': sum(1 for r in results if not r['success']),
            },
        )

        return {
            'scenario_id': scenario_id,
            'scenario_name': scenario.get('name', ''),
            'success': all_success,
            'total_steps': len(results),
            'passed': sum(1 for r in results if r['success']),
            'failed': sum(1 for r in results if not r['success']),
            'results': results,
        }

    @classmethod
    def mgmt_get_scenario(cls, scenario_id: str) -> Optional[dict]:
        """获取 V1 场景（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM api_scenarios WHERE id = ?",
            (scenario_id,)).fetchone()
        return cls._decode_v1_scenario(dict(row)) if row else None

    @classmethod
    def mgmt_update_scenario(cls, scenario_id: str, **kwargs) -> Optional[dict]:
        """更新 V1 场景（仓库内直连 SQL）。"""
        allowed = {'name', 'description', 'steps', 'status', 'environment_id'}
        updates = []
        params = []
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                if isinstance(v, (dict, list)):
                    v = json.dumps(v)
                updates.append(f"{k} = ?")
                params.append(v)
        if not updates:
            return cls.mgmt_get_scenario(scenario_id)
        updates.append("updated_at = ?")
        params.append(cls._now())
        params.append(scenario_id)
        conn = cls._apitest_conn()
        conn.execute(
            f"UPDATE api_scenarios SET {', '.join(updates)} WHERE id = ?",
            params)
        conn.commit()
        return cls.mgmt_get_scenario(scenario_id)

    @classmethod
    def mgmt_delete_scenario(cls, scenario_id: str,
                             permanent: bool = False) -> bool:
        """删除 V1 场景（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        if permanent:
            conn.execute("DELETE FROM api_scenarios WHERE id = ?",
                         (scenario_id,))
        else:
            conn.execute(
                "UPDATE api_scenarios SET deleted = 1, deleted_at = ? "
                "WHERE id = ? AND (deleted IS NULL OR deleted = 0)",
                (cls._now(), scenario_id))
        conn.commit()
        return True

    @classmethod
    def mgmt_list_trash_scenarios(cls, limit: int = 100) -> list:
        """列出回收站中的 V1 场景（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        rows = conn.execute(
            "SELECT * FROM api_scenarios WHERE deleted = 1 "
            "ORDER BY deleted_at DESC LIMIT ?", (limit,)).fetchall()
        return [cls._decode_v1_scenario(dict(r)) for r in rows]

    @classmethod
    def mgmt_restore_scenario(cls, scenario_id: str) -> bool:
        """从回收站恢复 V1 场景（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        cur = conn.execute(
            "UPDATE api_scenarios SET deleted = 0, deleted_at = NULL "
            "WHERE id = ? AND deleted = 1", (scenario_id,))
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def mgmt_list_mock_services(cls, limit: int = 100) -> list:
        """列出 V1 mock_services（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        rows = conn.execute(
            "SELECT * FROM mock_services WHERE (deleted IS NULL OR deleted = 0) "
            "ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [cls._decode_v1_mock(dict(r)) for r in rows]

    @classmethod
    def mgmt_create_mock_service(cls, name: str, method: str = "GET",
                                 path: str = "", response_code: int = 200,
                                 response_headers: dict = None,
                                 response_body: str = "{}", delay_ms: int = 0,
                                 project_id: str = "", **kwargs) -> dict:
        """创建 V1 mock_service（仓库内直连 SQL）。"""
        mock_id = cls._new_id()
        now = cls._now()
        conn = cls._apitest_conn()
        conn.execute(
            """INSERT INTO mock_services
               (id, name, method, path, response_code,
                response_headers, response_body, delay_ms,
                created_at, updated_at, project_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (mock_id, name, method.upper(), path, response_code,
             json.dumps(response_headers or {}, ensure_ascii=False),
             response_body, delay_ms, now, now, project_id))
        conn.commit()
        return cls.mgmt_get_mock_service(mock_id)

    @classmethod
    def mgmt_get_mock_service(cls, mock_id: str) -> Optional[dict]:
        """获取 V1 mock_service（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM mock_services WHERE id = ?", (mock_id,)).fetchone()
        return cls._decode_v1_mock(dict(row)) if row else None

    @classmethod
    def mgmt_update_mock_service(cls, mock_id: str, **kwargs) -> Optional[dict]:
        """更新 V1 mock_service（仓库内直连 SQL）。"""
        allowed = {'name', 'method', 'path', 'response_code',
                   'response_headers', 'response_body', 'delay_ms', 'enabled'}
        updates = []
        params = []
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                if isinstance(v, dict):
                    v = json.dumps(v)
                updates.append(f"{k} = ?")
                params.append(v)
        if not updates:
            return cls.mgmt_get_mock_service(mock_id)
        updates.append("updated_at = ?")
        params.append(cls._now())
        params.append(mock_id)
        conn = cls._apitest_conn()
        conn.execute(
            f"UPDATE mock_services SET {', '.join(updates)} WHERE id = ?",
            params)
        conn.commit()
        return cls.mgmt_get_mock_service(mock_id)

    @classmethod
    def mgmt_delete_mock_service(cls, mock_id: str,
                                 permanent: bool = False) -> bool:
        """删除 V1 mock_service（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        if permanent:
            conn.execute("DELETE FROM mock_services WHERE id = ?", (mock_id,))
        else:
            conn.execute(
                "UPDATE mock_services SET deleted = 1, deleted_at = ? "
                "WHERE id = ? AND (deleted IS NULL OR deleted = 0)",
                (cls._now(), mock_id))
        conn.commit()
        return True

    @classmethod
    def mgmt_list_trash_mocks(cls, limit: int = 100) -> list:
        """列出回收站中的 V1 mock_service（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        rows = conn.execute(
            "SELECT * FROM mock_services WHERE deleted = 1 "
            "ORDER BY deleted_at DESC LIMIT ?", (limit,)).fetchall()
        return [cls._decode_v1_mock(dict(r)) for r in rows]

    @classmethod
    def mgmt_restore_mock(cls, mock_id: str) -> bool:
        """从回收站恢复 V1 mock_service（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        cur = conn.execute(
            "UPDATE mock_services SET deleted = 0, deleted_at = NULL "
            "WHERE id = ? AND deleted = 1", (mock_id,))
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def mgmt_delete_mock(cls, mock_id: str,
                         permanent: bool = False) -> bool:
        """删除 V1 mock_service（仓库内直连 SQL 别名）。"""
        return cls.mgmt_delete_mock_service(mock_id, permanent=permanent)

    # ═══════════════════════════════════════════════════
    # 环境组 / 全局参数（Repository 去空壳 · SQL 下沉直连）
    # 环境格式转换（env_detail_to_frontend / env_frontend_to_db）属纯数据
    # 形态转换，非数据访问，按四层约束保留委托 store。
    # ═══════════════════════════════════════════════════
    @classmethod
    def list_env_groups(cls, project_id: str = "", keyword: str = "") -> list:
        """列出环境组（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        query = "SELECT * FROM env_groups WHERE 1=1"
        params: list = []
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if keyword:
            query += " AND name LIKE ?"
            params.append(f"%{keyword}%")
        query += " ORDER BY pos ASC, created_at ASC"
        rows = conn.execute(query, params).fetchall()
        return [cls._decode_env_group(dict(r)) for r in rows]

    @classmethod
    def get_env_group(cls, group_id: str) -> Optional[dict]:
        """获取环境组详情（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM env_groups WHERE id = ?", (group_id,)).fetchone()
        return cls._decode_env_group(dict(row)) if row else None

    @classmethod
    def create_env_group(cls, name: str = "", description: str = "",
                         project_id: str = "", env_group_project: list = None,
                         pos: int = 0, **kwargs) -> dict:
        """创建环境组（仓库内直连 SQL）。"""
        import time
        import uuid
        conn = cls._apitest_conn()
        now = time.time()
        gid = uuid.uuid4().hex[:12]
        conn.execute(
            """INSERT INTO env_groups
               (id, name, description, project_id, env_group_project,
                pos, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (gid, name, description, project_id,
             json.dumps(env_group_project or [], ensure_ascii=False),
             pos, now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM env_groups WHERE id = ?", (gid,)).fetchone()
        return cls._decode_env_group(dict(row)) if row else {
            "id": gid, "name": name, "env_group_project": env_group_project or []}

    @classmethod
    def update_env_group(cls, group_id: str, **fields) -> Optional[dict]:
        """更新环境组（仓库内直连 SQL）。"""
        import time
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM env_groups WHERE id = ?", (group_id,)).fetchone()
        if not row:
            return None
        allowed = {"name", "description", "project_id", "env_group_project", "pos"}
        updates = {}
        for k, v in fields.items():
            if k in allowed and v is not None:
                if k == "env_group_project" and isinstance(v, (list, dict)):
                    v = json.dumps(v, ensure_ascii=False)
                updates[k] = v
        if not updates:
            return cls._decode_env_group(dict(row))
        updates["updated_at"] = time.time()
        sets = ", ".join([f"{k} = ?" for k in updates])
        conn.execute(
            f"UPDATE env_groups SET {sets} WHERE id = ?",
            list(updates.values()) + [group_id])
        conn.commit()
        row2 = conn.execute(
            "SELECT * FROM env_groups WHERE id = ?", (group_id,)).fetchone()
        return cls._decode_env_group(dict(row2)) if row2 else None

    @classmethod
    def delete_env_group(cls, group_id: str) -> bool:
        """删除环境组（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        cur = conn.execute("DELETE FROM env_groups WHERE id = ?", (group_id,))
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def get_env_groups_by_project(cls, project_id: str) -> list:
        """获取项目下的环境组列表（仓库内直连 SQL）。"""
        return cls.list_env_groups(project_id=project_id)

    # ── global_params 全局参数（仓库内直连 SQL）────────────
    @classmethod
    def get_global_params(cls, project_id: str) -> Optional[dict]:
        """获取项目全局参数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            """SELECT * FROM global_params WHERE project_id = ?
               ORDER BY updated_at DESC LIMIT 1""",
            (project_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["headers"] = cls._json_loads(d.get("headers"), [])
        d["common_variables"] = cls._json_loads(d.get("common_variables"), [])
        return d

    @classmethod
    def save_global_params(cls, project_id: str, headers: list = None,
                           common_variables: list = None) -> dict:
        """保存全局参数：存在则更新、否则新建（仓库内直连 SQL）。"""
        import time
        import uuid
        conn = cls._apitest_conn()
        existing = cls.get_global_params(project_id)
        now = time.time()
        if existing:
            updates = {"updated_at": now}
            if headers is not None:
                updates["headers"] = json.dumps(headers or [], ensure_ascii=False)
            if common_variables is not None:
                updates["common_variables"] = json.dumps(
                    common_variables or [], ensure_ascii=False)
            sets = ", ".join([f"{k} = ?" for k in updates])
            conn.execute(
                f"UPDATE global_params SET {sets} WHERE id = ?",
                list(updates.values()) + [existing["id"]])
            conn.commit()
            result = cls.get_global_params(project_id)
            return result or existing
        gpid = uuid.uuid4().hex[:12]
        conn.execute(
            """INSERT INTO global_params
               (id, project_id, headers, common_variables, created_at, updated_at)
               VALUES (?,?,?,?,?,?)""",
            (gpid, project_id,
             json.dumps(headers or [], ensure_ascii=False),
             json.dumps(common_variables or [], ensure_ascii=False),
             now, now),
        )
        conn.commit()
        return cls.get_global_params(project_id) or {
            "id": gpid, "project_id": project_id,
            "headers": headers or [], "common_variables": common_variables or []}

    @classmethod
    def delete_global_params(cls, project_id: str) -> bool:
        """删除项目全局参数（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        cur = conn.execute(
            "DELETE FROM global_params WHERE project_id = ?", (project_id,))
        conn.commit()
        return cur.rowcount > 0

    @classmethod
    def delete_global_param_by_id(cls, param_id: str) -> bool:
        """按记录 id 删除全局参数记录（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        cur = conn.execute("DELETE FROM global_params WHERE id = ?", (param_id,))
        conn.commit()
        return cur.rowcount > 0

    # ── 数据解码与连接工具（供本仓库层下沉方法使用）────────
    @staticmethod
    def _apitest_conn():
        """获取接口测试库连接（apitest.db）。"""
        from app.core.database import Database
        return Database.get_conn("apitest.db")

    @staticmethod
    def _json_loads(value, fallback):
        if value is None:
            return fallback
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return fallback

    @classmethod
    def _decode_env_group(cls, d: dict) -> dict:
        d["env_group_project"] = cls._json_loads(d.get("env_group_project"), [])
        return d

    @classmethod
    def _env_to_frontend(cls, e: dict) -> dict:
        """将后端 api_environments 记录转换为前端 EnvDetailItem 格式（下沉 store）。"""
        config_str = e.get("config") or "{}"
        try:
            config = json.loads(config_str) if isinstance(config_str, str) else (config_str or {})
        except Exception:
            config = {}
        default_config = {
            "commonParams": {},
            "commonVariables": [],
            "httpConfig": [],
            "dataSources": [],
            "hostConfig": {"enable": False, "hosts": []},
            "preProcessorConfig": {
                "apiProcessorConfig": {
                    "scenarioProcessorConfig": {"processors": []},
                    "requestProcessorConfig": {"processors": []},
                }
            },
            "postProcessorConfig": {
                "apiProcessorConfig": {
                    "scenarioProcessorConfig": {"processors": []},
                    "requestProcessorConfig": {"processors": []},
                }
            },
            "assertionConfig": {"assertions": []},
            "pluginConfigMap": {},
        }
        merged_config = {**default_config, **config}
        return {
            "id": e.get("id", ""),
            "projectId": e.get("project_id", ""),
            "name": e.get("name", ""),
            "description": e.get("description", ""),
            "mock": e.get("mock", False) if "mock" in e else False,
            "config": merged_config,
        }

    @classmethod
    def env_detail_to_frontend(cls, env: dict) -> Optional[dict]:
        """环境详情 → 前端形态（数据形态转换，下沉 store）。"""
        if not env:
            return None
        return cls._env_to_frontend(env)

    @classmethod
    def env_frontend_to_db(cls, data: dict) -> dict:
        """前端形态 → 库内形态（数据形态转换，下沉 store）。"""
        config = data.get("config") or {}
        http_config = config.get("httpConfig") or []
        base_url = ""
        if http_config:
            first = http_config[0]
            base_url = first.get("url", "") or first.get("hostname", "") or ""
        return {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "project_id": data.get("projectId", ""),
            "config": json.dumps(config, ensure_ascii=False),
            "base_url": base_url,
            "mock": data.get("mock", False),
        }


    # ── 接口用例/场景通用数据工具（下沉真实 SQL 用）────────
    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _now() -> float:
        return time.time()

    @classmethod
    def _apitest_row(cls, row) -> dict:
        """行 → 归一化 dict（与旧 store._row_to_dict 完全一致的 JSON 反序列化）。"""
        data = dict(row)
        str_cols = {"headers", "query", "params", "metadata",
                    "response_headers", "variables", "database_config", "snapshot"}
        list_cols = {"tags", "asserts", "pre_scripts", "post_scripts", "pre_sql",
                     "post_sql", "logic_controllers", "steps", "detail",
                     "common_variables", "env_group_project"}
        for k in str_cols:
            if k in data and isinstance(data[k], str):
                try:
                    data[k] = json.loads(data[k])
                except (json.JSONDecodeError, TypeError):
                    data[k] = {}
        for k in list_cols:
            if k in data and isinstance(data[k], str):
                try:
                    data[k] = json.loads(data[k])
                except (json.JSONDecodeError, TypeError):
                    data[k] = []
        return data

    @classmethod
    def _decode_v1_test_case(cls, d: dict) -> dict:
        """V1 api_test_case JSON 列反序列化。"""
        for key in ('request_headers', 'request_params', 'assertions',
                    'pre_scripts', 'post_scripts', 'variables'):
            if key in d and isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    d[key] = {}
        return d

    @classmethod
    def _decode_v1_mock(cls, d: dict) -> dict:
        """V1 mock_service response_headers JSON 反序列化。"""
        try:
            d['response_headers'] = json.loads(d.get('response_headers') or '{}')
        except Exception:
            d['response_headers'] = {}
        return d

    @classmethod
    def _decode_v1_scenario(cls, d: dict) -> dict:
        """V1 api_scenario steps JSON 反序列化。"""
        try:
            d['steps'] = json.loads(d.get('steps') or '[]')
        except Exception:
            d['steps'] = []
        return d

    # ── assertion_rules 断言规则（仓库内直连 SQL）────────
    @classmethod
    def list_assertion_rules(cls, limit: int = 100) -> list:
        """列出断言规则（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        rows = conn.execute(
            "SELECT * FROM assertion_rules ORDER BY created_at DESC LIMIT ?",
            (limit,)).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def get_assertion_rule(cls, rule_id: str) -> Optional[dict]:
        """获取断言规则详情（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        row = conn.execute(
            "SELECT * FROM assertion_rules WHERE id = ?", (rule_id,)).fetchone()
        return dict(row) if row else None

    @classmethod
    def create_assertion_rule(cls, name: str, rule_type: str = "text",
                              target: str = "", expression: str = "",
                              expected: str = "",
                              description: str = "", **kwargs) -> dict:
        """创建断言规则（仓库内直连 SQL）。"""
        rule_id = cls._new_id()
        now = cls._now()
        conn = cls._apitest_conn()
        conn.execute(
            """INSERT INTO assertion_rules
               (id, name, rule_type, target, expression, expected,
                description, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (rule_id, name, rule_type, target, expression, expected,
             description, now))
        conn.commit()
        return cls.get_assertion_rule(rule_id) or {"id": rule_id}

    @classmethod
    def delete_assertion_rule(cls, rule_id: str) -> bool:
        """删除断言规则（仓库内直连 SQL）。"""
        conn = cls._apitest_conn()
        conn.execute("DELETE FROM assertion_rules WHERE id = ?", (rule_id,))
        conn.commit()
        return True

    @classmethod
    def _apitest_log(cls, resource_type: str, resource_id: str,
                     resource_name: str, action: str, operator: str = "",
                     detail: dict = None, project_id: str = "") -> None:
        """写入 api_operation_logs 操作日志。"""
        try:
            conn = cls._apitest_conn()
            conn.execute(
                """INSERT INTO api_operation_logs
                   (id, resource_type, resource_id, resource_name, action,
                    operator, detail, project_id, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (cls._new_id(), resource_type, resource_id, resource_name,
                 action, operator,
                 json.dumps(detail or {}, ensure_ascii=False),
                 project_id, cls._now()),
            )
            conn.commit()
        except Exception:
            pass


apitest_repo = ApitestRepo


# ── 注册到域 Repository 接口 ─────────────────────────────
# 确保 apitest 域通过统一接口出口访问（合并 apitest / api_testing）
from app.repositories.interface import register_domain_repository

register_domain_repository("apitest", apitest_repo)
