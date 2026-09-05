# app/services/project_service.py
"""项目管理业务逻辑门面（Phase 4 · DDD A→B→C 渐进迁移 — 阶段 C 收敛）。

本层是 routers 的项目管理业务入口，同时也是 13+ 旁路 / compat router 复用的
**兼容门面**。按 §五「渐进式、可回滚」方案推进，本 Service 的**核心生命周期**
（create / get / list / update / delete）已收敛为对 DDD 应用门面
`project_app_service` 的薄委托：

    Router → project_service(薄门面) → ProjectAppService → ProjectRepoAdapter → ProjectRepo

参数经 DTO（`application/dto.py`）翻译，返回经 DTO 契约桥（`application/web_contract.py`）
归一为既有仓库行口径，保证旁路 / compat router 的对外 schema 与迁移前零变化。

> 仍保留直连 ProjectRepo 的**兼容方法**（双轨过渡，逐域收敛后再移除）：
>   - `update` / `set_status` 中的**遗留状态位**（`disabled` / `deleted`，由组织 / 系统管理
>     等 admin 流写入）不在 DDD 聚合的 active⇄archived 状态机语义内，故这些特殊状态仍走
>     Repo 原样落库，避免被聚合状态机改写；active/archived 的合法迁移仍经领域状态机守护。
>   - 自定义函数 / 自定义字段已收敛为经 `ProjectAppService` 委托 DDD（阶段 C 续），
>     Service 侧保留前端格式契约桥；
>   - 成员批量/跨项目统计、项目扫描等超聚合能力仍保留在 Repo，逐项补 DDD 能力后再收敛。
"""
from __future__ import annotations

from typing import Optional

from app.domain.project.application.dto import (
    ChangeStatusCommand,
    CreateCustomFuncCommand,
    CreateProjectCommand,
    CustomFieldListQuery,
    CustomFuncListQuery,
    GetMemberCommand,
    ListQuery,
    RemoveMemberCommand,
    UpdateCustomFuncCommand,
    UpdateCustomFuncStatusCommand,
    UpdateMemberCommand,
    UpdateProjectCommand,
    UpsertCustomFieldCommand,
)
from app.domain.project.application.project_app_service import (
    project_app_service as _ddd_app,
)
from app.domain.project.application.web_contract import to_row, to_row_list
from app.repositories.project_repo import ProjectRepo

# 领域状态机可合法迁移的项目状态（active ⇄ archived）
_MANAGEABLE_STATUSES = ("active", "archived")


class ProjectService:
    """项目管理服务（核心生命周期委托 DDD 应用门面的薄门面）。"""

    def create(self, data: dict) -> dict:
        """创建项目（委托 DDD，输出归一为既有仓库行口径）。"""
        try:
            item = _ddd_app.create(CreateProjectCommand(
                name=data.get("name", ""),
                description=data.get("description", ""),
                repo_url=data.get("repo_url", ""),
                language=data.get("language", "python"),
                path=data.get("path", ""),
            ))
        except Exception as exc:  # 名称非空等不变量 → 兼容既有 create 抛异常语义
            raise ValueError(str(exc)) from exc
        return to_row(item)

    def get(self, pid: str) -> Optional[dict]:
        """获取项目详情（委托 DDD；不存在/已删除返回 None，兼容既有语义）。"""
        item = _ddd_app.get(pid)
        return to_row(item) if item else None

    def list(self, search: str = "", status: str = "", limit: int = 100) -> list:
        """列出项目（委托 DDD，返回既有仓库行口径的列表）。"""
        result = _ddd_app.list(ListQuery(
            search=search or "", status=status or "", limit=int(limit or 100),
        ))
        return to_row_list(result.get("list", []))

    def update(self, pid: str, data: dict) -> Optional[dict]:
        """更新项目。

        普通字段（name/description/repo_url/language/path）委托 DDD `update`；
        active/archived 状态迁移经领域状态机 `change_status`（已做幂等守卫：
        目标态与当前态一致时跳过，兼容 admin 重复启用/禁用）；遗留 disabled/deleted
        等状态位仍走 Repo 原样落库，保证 admin 旁路流对外语义不变。
        """
        if ProjectRepo.get(pid) is None:
            return None
        updates = dict(data or {})
        status = updates.pop("status", None)

        if updates:
            try:
                _ddd_app.update(UpdateProjectCommand(
                    project_id=pid,
                    name=updates.get("name"),
                    description=updates.get("description"),
                    repo_url=updates.get("repo_url"),
                    language=updates.get("language"),
                    path=updates.get("path"),
                ))
            except Exception as exc:
                raise ValueError(str(exc)) from exc

        if status is not None:
            status = str(status)
            if status in _MANAGEABLE_STATUSES:
                current = _ddd_app.get(pid)
                if current and current.get("status") != status:
                    _ddd_app.change_status(ChangeStatusCommand(
                        project_id=pid, target_status=status,
                    ))
            else:
                # 遗留状态位（deleted/disabled 等）不经聚合状态机，原样落库
                ProjectRepo.update(pid, {"status": status})

        item = _ddd_app.get(pid)
        return to_row(item) if item else None

    def delete(self, pid: str) -> bool:
        """删除项目（软删除进回收站，委托 DDD；不存在/已删除返回 False）。"""
        try:
            _ddd_app.soft_delete(pid)
            return True
        except Exception:
            return False

    def get_stats(self, pid: str) -> dict:
        return ProjectRepo.get_stats(pid)

    # ── 管理辅助（供系统管理/成员管理路由复用）──────────────
    def set_status(self, pid: str, status: str) -> Optional[dict]:
        """启用/禁用项目（status: active/disabled/archived）。"""
        return ProjectRepo.update(pid, {"status": status})

    def find_or_create(self, project_id: str) -> dict:
        """按 id 查找项目，不存在则按名称自动创建（兼容前端松散传参）。"""
        found = ProjectRepo.get(project_id)
        if found:
            return found
        return ProjectRepo.create(name=project_id, description="auto-created")

    def list_members(self, project_id: str, keyword: str = "") -> list:
        """列出项目成员（委托 DDD `ProjectAppService.list_members`）。"""
        return _ddd_app.list_members(project_id, keyword=keyword or "")

    def get_member(self, member_id: str) -> Optional[dict]:
        """按 member_id 查询项目成员（经 DDD 门面）。"""
        return _ddd_app.get_member(GetMemberCommand(member_id=member_id))

    def add_member(self, project_id: str, user_id: str = "",
                   username: str = "", name: str = "", email: str = "",
                   role: str = "member", user_group: str = "") -> Optional[dict]:
        """添加项目成员。返回成员记录（含 id/project_id 等行字段）。

        注：`_ddd_app.add_member` 返回项目视图（不含行级 member_id），
        与上游（org router）期望的成员行 schema 不一致；此处沿用既有
        `ProjectRepo.add_member` 直写（超聚合能力双轨保留），DDD 成员
        管理能力已具备（project_app_service.add_member），后续收敛时
        以门面契约桥过渡。
        """
        return ProjectRepo.add_member(
            project_id, user_id=user_id, username=username, name=name,
            email=email, role=role, user_group=user_group,
        )

    def update_member(self, member_id: str, data: dict) -> Optional[dict]:
        """更新项目成员（经 DDD 门面）。"""
        return _ddd_app.update_member(UpdateMemberCommand(
            member_id=member_id, data=data or {}))

    def remove_member(self, project_id: str, user_id: str) -> bool:
        """移除项目成员。经 DDD 门面（项目不存在时回退直连返回 False）。"""
        try:
            return _ddd_app.remove_member(RemoveMemberCommand(
                project_id=project_id, user_id=user_id))
        except Exception:
            return ProjectRepo.remove_member(project_id, user_id)

    def batch_remove_members(self, project_id: str, user_ids: list) -> int:
        """批量移除项目成员。注：直接走 Repo（DDD 聚合级 remove 需项目存在
        会抛异常，与既有"项目不存在仍返回 0"语义不符）。"""
        return ProjectRepo.batch_remove_members(project_id, user_ids)

    def count_members_by_project(self) -> dict:
        """统计各项目成员数。返回 {project_id: count}（组织前端 memberCount）。"""
        return ProjectRepo.count_members_by_project()

    def remove_user_all_projects(self, user_id: str) -> int:
        """移除某用户在全部项目下的成员关系（跨项目批量删除）。"""
        return ProjectRepo.remove_user_all_projects(str(user_id))

    def list_projects_by_user_ids(self, user_ids) -> dict:
        """批量反查多个用户所属的项目（含 id/name），返回 {user_id: [project,...]}。"""
        return ProjectRepo.list_projects_by_user_ids(user_ids)

    def set_member_group(self, member_id: str, project_id: str,
                         user_id: str, group_str: str) -> Optional[dict]:
        """按 member_id（或 project_id+user_id 解析）更新成员用户组。"""
        if not member_id and project_id and user_id:
            members = ProjectRepo.list_members(project_id)
            for m in members:
                if str(m.get("user_id", "")) == str(user_id):
                    member_id = m.get("id")
                    break
        if not member_id:
            return None
        return ProjectRepo.update_member(member_id, {"user_group": group_str})

    def remove_role_from_all_members(self, role_id: str) -> int:
        """从所有项目成员的 user_group 中移除指定角色。"""
        return ProjectRepo.remove_role_from_all_members(role_id)
    # ── 项目自定义函数（custom_funcs）────────────────────
    def _custom_func_to_frontend(self, row: dict) -> Optional[dict]:
        """将 custom_funcs 行转换为前端字段对象（含用户名查询）。"""
        import json
        if row is None:
            return None
        tags_raw = row.get("tags", "") or "[]"
        try:
            tags = json.loads(tags_raw) if isinstance(tags_raw, str) else (list(tags_raw) if tags_raw else [])
        except Exception:
            tags = []
        create_user = row.get("create_user", "") or "admin"
        update_user = row.get("update_user", "") or "admin"
        create_user_name = create_user
        update_user_name = update_user
        try:
            from app.core.database import Database
            uconn = Database.get_conn("auth.db")
            urow = uconn.execute(
                "SELECT name FROM users WHERE username = ?", (create_user,)
            ).fetchone()
            if urow and urow["name"]:
                create_user_name = urow["name"]
            urow2 = uconn.execute(
                "SELECT name FROM users WHERE username = ?", (update_user,)
            ).fetchone()
            if urow2 and urow2["name"]:
                update_user_name = urow2["name"]
        except Exception:
            pass
        return {
            "id": row.get("id", ""),
            "name": row.get("name", ""),
            "script": row.get("script", ""),
            "type": row.get("type", "HTTP"),
            "description": row.get("description", ""),
            "status": row.get("status", "DRAFT"),
            "projectId": row.get("project_id", ""),
            "tags": tags,
            "params": row.get("params", "") or "[]",
            "result": row.get("result", "") or "",
            "internal": bool(row.get("internal", 0)),
            "createTime": int((row.get("create_time", 0) or 0) * 1000),
            "updateTime": int((row.get("update_time", 0) or 0) * 1000),
            "createUser": create_user,
            "updateUser": update_user,
            "createUserName": create_user_name,
            "updateUserName": update_user_name,
        }

    def list_custom_funcs(self, project_id: str = "", keyword: str = "") -> list:
        """列出自定义函数（经 DDD 门面，含前端格式转换）。"""
        rows = _ddd_app.list_custom_funcs(
            CustomFuncListQuery(project_id=project_id, keyword=keyword)
        )
        return [self._custom_func_to_frontend(r) for r in rows]

    def get_custom_func(self, func_id: str) -> Optional[dict]:
        """按 id 获取自定义函数（经 DDD 门面，前端格式）。"""
        row = _ddd_app.get_custom_func(func_id)
        return self._custom_func_to_frontend(row)

    def create_custom_func(self, func_id: str, name: str = "", script: str = "",
                           func_type: str = "HTTP", description: str = "",
                           status: str = "DRAFT", project_id: str = "",
                           tags: list = None, params: str = "[]", result: str = "",
                           create_user: str = "admin") -> bool:
        """创建自定义函数（经 DDD 门面）。"""
        return _ddd_app.create_custom_func(CreateCustomFuncCommand(
            func_id=func_id, name=name, script=script, func_type=func_type,
            description=description, status=status, project_id=project_id,
            tags=tags or [], params=params, result=result,
            create_user=create_user,
        ))

    def update_custom_func(self, func_id: str, updates: dict,
                           update_user: str = "admin") -> bool:
        """更新自定义函数（tags 自动 JSON 序列化）。"""
        import json
        repo_updates = dict(updates)
        if "tags" in repo_updates:
            tags = repo_updates["tags"]
            if not isinstance(tags, list):
                tags = []
            repo_updates["tags"] = json.dumps(tags, ensure_ascii=False)
        return _ddd_app.update_custom_func(UpdateCustomFuncCommand(
            func_id=func_id, updates=repo_updates, update_user=update_user,
        ))

    def update_custom_func_status(self, func_id: str, status: str) -> bool:
        """更新自定义函数状态（经 DDD 门面）。"""
        return _ddd_app.update_custom_func_status(
            UpdateCustomFuncStatusCommand(func_id=func_id, status=status)
        )

    def delete_custom_func(self, func_id: str) -> bool:
        """删除自定义函数（经 DDD 门面）。"""
        return _ddd_app.delete_custom_func(func_id)

    def list_custom_func_status(self, project_id: str = "") -> list:
        """列出自定义函数 id/name/status（经 DDD 门面）。"""
        rows = _ddd_app.list_custom_func_status(project_id=project_id)
        return [dict(r) for r in rows]

    # ── 项目自定义字段（project_custom_fields）────────────
    def _custom_field_to_frontend(self, row: dict) -> Optional[dict]:
        """将 project_custom_fields 行转换为前端字段对象。"""
        import json
        if row is None:
            return None
        options_raw = row.get("options", "") or "[]"
        try:
            options = json.loads(options_raw) if isinstance(options_raw, str) else list(options_raw or [])
        except Exception:
            options = []
        return {
            "id": row.get("id", ""),
            "name": row.get("name", ""),
            "remark": row.get("remark", ""),
            "type": row.get("type", "INPUT"),
            "scene": row.get("scene", ""),
            "scopeId": row.get("scope_id", ""),
            "scopeType": "PROJECT",
            "internal": bool(row.get("internal", 0)),
            "enableOptionKey": bool(row.get("enable_option_key", 0)),
            "options": options,
            "used": bool(row.get("used", 0)),
            "createTime": int((row.get("create_time", 0) or 0) * 1000),
            "updateTime": int((row.get("update_time", 0) or 0) * 1000),
            "createUser": row.get("create_user", "admin"),
            "updateUser": row.get("update_user", "admin"),
            "refId": None,
            "fieldType": row.get("type", "INPUT"),
        }

    def list_custom_fields(self, scope_id: str, scene: str = "") -> list:
        """列出项目自定义字段（经 DDD 门面，前端格式）。"""
        rows = _ddd_app.list_custom_fields(
            CustomFieldListQuery(scope_id=scope_id, scene=scene)
        )
        return [self._custom_field_to_frontend(r) for r in rows]

    def get_custom_field(self, field_id: str) -> Optional[dict]:
        """获取单个项目自定义字段（经 DDD 门面，前端格式）。"""
        row = _ddd_app.get_custom_field(field_id)
        return self._custom_field_to_frontend(row)

    def upsert_custom_field(self, field_id: str, body: dict) -> Optional[dict]:
        """新增或更新项目自定义字段，返回前端格式（经 DDD 门面）。"""
        row = _ddd_app.upsert_custom_field(UpsertCustomFieldCommand(
            field_id=field_id, body=body,
        ))
        return self._custom_field_to_frontend(row)

    def delete_custom_field(self, field_id: str) -> bool:
        """删除项目自定义字段（经 DDD 门面）。"""
        return _ddd_app.delete_custom_field(field_id)

    # ── 项目扫描 / 源文件收集（委托 app.projects.manager 兼容层）────────
    def scan_project(self, project_path: str, **kwargs) -> dict:
        """递归扫描项目目录，返回所有源文件与函数签名。"""
        from app.services.project_scan import scan_project as _scan
        return _scan(project_path, **kwargs)

    def collect_sources_from_paths(self, paths: list) -> list:
        """从指定文件路径列表读取源代码。"""
        from app.services.project_scan import collect_sources_from_paths as _collect
        return _collect(paths)


project_service = ProjectService()
