"""项目应用服务（Application Service / Use Case 门面）。

职责：
  1. 作为路由器与领域层之间的用例编排入口；
  2. 承载"项目"用例的事务边界：加载聚合 → 执行领域命令 → 保存聚合 →
     发布领域事件；
  3. 将领域异常透传给上层（由 Web 层统一翻译为 HTTP 响应）。

保持瘦：只做编排，不写业务规则（业务规则在领域层聚合内）。
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.domain.common.domain_events import event_bus
from app.domain.common.exceptions import AggregateNotFound
from app.domain.project.application.dto import (
    AddMemberCommand,
    BatchRemoveMembersCommand,
    ChangeStatusCommand,
    CreateCustomFuncCommand,
    CreateProjectCommand,
    CustomFieldListQuery,
    CustomFuncListQuery,
    GetMemberCommand,
    ListQuery,
    RemoveMemberCommand,
    UpdateMemberCommand,
    UpdateCustomFuncCommand,
    UpdateCustomFuncStatusCommand,
    UpdateProjectCommand,
    UpsertCustomFieldCommand,
)
from app.domain.project.domain.entities.project import Project
from app.domain.project.domain.repository import ProjectRepository
from app.domain.project.infrastructure.project_repository_impl import ProjectRepoAdapter

logger = logging.getLogger(__name__)


class ProjectAppService:
    """项目用例编排服务。"""

    def __init__(self, repo: ProjectRepository = None):
        self._repo: ProjectRepository = repo or ProjectRepoAdapter()

    # ── 聚合级基础操作 ─────────────────────────────
    def create(self, cmd: CreateProjectCommand) -> dict:
        project = Project(
            project_id=self._repo.next_id(),
            name=cmd.name,
            description=cmd.description,
            repo_url=cmd.repo_url,
            language=cmd.language,
            path=cmd.path,
            organization_id=cmd.organization_id,
        )
        self._repo.save(project)
        self._publish(project)
        return project.to_dict()

    def get(self, project_id: str, include_deleted: bool = False) -> Optional[dict]:
        project = self._repo.find_by_id(project_id, include_deleted=include_deleted)
        return project.to_dict() if project else None

    def get_or_raise(self, project_id: str) -> dict:
        project = self._find_or_raise(project_id)
        return project.to_dict()

    def update(self, cmd: UpdateProjectCommand) -> Optional[dict]:
        project = self._find_or_raise(cmd.project_id)
        if cmd.name is not None:
            project.rename(cmd.name, cmd.operator)
        if cmd.description is not None:
            project.change_description(cmd.description, cmd.operator)
        if cmd.repo_url is not None or cmd.path is not None:
            project.set_repo(repo_url=cmd.repo_url, path=cmd.path, operator=cmd.operator)
        if cmd.language is not None:
            project.change_language(cmd.language, cmd.operator)
        if cmd.organization_id is not None:
            project.set_organization(cmd.organization_id, cmd.operator)
        self._repo.update(project)
        self._publish(project)
        return project.to_dict()

    def change_status(self, cmd: ChangeStatusCommand) -> Optional[dict]:
        project = self._find_or_raise(cmd.project_id)
        project.change_status(cmd.target_status, cmd.operator)
        self._repo.update(project)
        self._publish(project)
        return project.to_dict()

    # ── 生命周期 ───────────────────────────────────
    def archive(self, project_id: str, operator: str = "system") -> Optional[dict]:
        project = self._find_or_raise(project_id)
        project.archive(operator)
        self._repo.update(project)
        self._publish(project)
        return project.to_dict()

    def activate(self, project_id: str, operator: str = "system") -> Optional[dict]:
        project = self._find_or_raise(project_id)
        project.activate(operator)
        self._repo.update(project)
        self._publish(project)
        return project.to_dict()

    # ── 回收站 ─────────────────────────────────────
    def soft_delete(self, project_id: str, operator: str = "system") -> bool:
        project = self._find_or_raise(project_id)
        project.delete(operator)
        self._repo.soft_delete(project_id)
        self._publish(project)
        return True

    def restore(self, project_id: str, operator: str = "system") -> bool:
        project = self._find_deleted_or_raise(project_id)
        project.restore(operator)
        self._repo.restore(project_id)
        self._publish(project)
        return True

    # ── 成员管理 ───────────────────────────────────
    def add_member(self, cmd: AddMemberCommand) -> Optional[dict]:
        project = self._find_or_raise(cmd.project_id)
        project.add_member(
            user_id=cmd.user_id, username=cmd.username, name=cmd.name,
            email=cmd.email, role=cmd.role, user_group=cmd.user_group,
            operator=cmd.operator,
        )
        # 落成员表
        self._repo.add_member(cmd.project_id, project.members[-1].to_dict())
        self._publish(project)
        return self.get(cmd.project_id)

    def remove_member(self, cmd: RemoveMemberCommand) -> bool:
        project = self._find_or_raise(cmd.project_id)
        removed = project.remove_member(user_id=cmd.user_id, operator=cmd.operator)
        if removed:
            self._repo.remove_member(cmd.project_id, cmd.user_id)
            self._publish(project)
        return removed

    def get_member(self, cmd: GetMemberCommand) -> Optional[dict]:
        """按 member_id 查询项目成员。"""
        return self._repo.get_member(cmd.member_id)

    def update_member(self, cmd: UpdateMemberCommand) -> Optional[dict]:
        """更新项目成员（角色/用户组等字段）。"""
        return self._repo.update_member(cmd.member_id, cmd.data)

    def list_members(self, project_id: str, keyword: str = "") -> List[dict]:
        return self._repo.list_members(project_id, keyword=keyword)

    def batch_remove_members(self, cmd: BatchRemoveMembersCommand) -> int:
        """批量移除项目成员。"""
        removed = 0
        for uid in cmd.user_ids:
            if self.remove_member(RemoveMemberCommand(
                project_id=cmd.project_id, user_id=str(uid),
                operator=cmd.operator,
            )):
                removed += 1
        return removed

    # ── 自定义函数（custom_funcs）旁路覆盖 ─────────────
    def list_custom_funcs(self, query: CustomFuncListQuery) -> list:
        return self._repo.list_custom_funcs(
            project_id=query.project_id, keyword=query.keyword,
        )

    def get_custom_func(self, func_id: str) -> Optional[dict]:
        return self._repo.get_custom_func_row(func_id)

    def create_custom_func(self, cmd: CreateCustomFuncCommand) -> bool:
        return self._repo.create_custom_func(
            func_id=cmd.func_id, name=cmd.name, script=cmd.script,
            func_type=cmd.func_type, description=cmd.description,
            status=cmd.status, project_id=cmd.project_id,
            tags=cmd.tags, params=cmd.params, result=cmd.result,
            create_user=cmd.create_user,
        )

    def update_custom_func(self, cmd: UpdateCustomFuncCommand) -> bool:
        return self._repo.update_custom_func(
            cmd.func_id, cmd.updates, update_user=cmd.update_user,
        )

    def update_custom_func_status(self, cmd: UpdateCustomFuncStatusCommand) -> bool:
        return self._repo.update_custom_func_status(cmd.func_id, cmd.status)

    def delete_custom_func(self, func_id: str) -> bool:
        return self._repo.delete_custom_func(func_id)

    def list_custom_func_status(self, project_id: str = "") -> list:
        return self._repo.list_custom_func_status(project_id=project_id)

    # ── 自定义字段（project_custom_fields）旁路覆盖 ────────
    def list_custom_fields(self, query: CustomFieldListQuery) -> list:
        return self._repo.list_custom_fields(query.scope_id, scene=query.scene)

    def get_custom_field(self, field_id: str) -> Optional[dict]:
        return self._repo.get_custom_field(field_id)

    def upsert_custom_field(self, cmd: UpsertCustomFieldCommand) -> Optional[dict]:
        return self._repo.upsert_custom_field(cmd.field_id, cmd.body)

    def delete_custom_field(self, field_id: str) -> bool:
        return self._repo.delete_custom_field(field_id)

    # ── 查询（读模型）──────────────────────────────
    def list(self, query: ListQuery) -> dict:
        items, total = self._repo.list_projects(
            search=query.search, status=query.status, limit=query.limit,
            include_deleted=query.include_deleted,
        )
        return {"list": [p.to_dict() for p in items], "total": total}

    # ── 内部助手 ───────────────────────────────────
    def _find_or_raise(self, project_id: str) -> Project:
        project = self._repo.find_by_id(project_id)
        if project is None:
            raise AggregateNotFound(f"项目不存在或已删除: {project_id}")
        return project

    def _find_deleted_or_raise(self, project_id: str) -> Project:
        project = self._repo.find_by_id(project_id, include_deleted=True)
        if project is None or not project.deleted:
            raise AggregateNotFound(f"回收站中不存在该项目: {project_id}")
        return project

    def _publish(self, project: Project) -> None:
        events = project.pull_domain_events()
        for ev in events:
            event_bus.dispatch(ev)


# 单例门面（进程内复用）
project_app_service = ProjectAppService()
project_service = project_app_service
