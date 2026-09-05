"""项目聚合根 Project（项目管理限界上下文）。

聚合内聚内容：
  - Project（聚合根）
  - 成员列表 ProjectMember[]（子实体/值对象快照）
  - 关联环境、版本等由各自仓储管理，仅在此保留 id 级关联语义

聚合职责：守护项目标识/名称/生命周期与成员不变量。所有变更必须经由
聚合根方法，禁止外部直接改字段；业务命令（改名 / 归档 / 启停 / 软删除 /
恢复 / 成员管理）在校验通过后返回领域事件，供应用层落库+发布，从而与
审计、通知等副作用解耦。
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.project.domain.events import (
    ProjectActivated,
    ProjectArchived,
    ProjectCreated,
    ProjectInfoChanged,
    ProjectMemberAdded,
    ProjectMemberRemoved,
    ProjectRenamed,
    ProjectRestored,
    ProjectSoftDeleted,
    ProjectStatusChanged,
)
from app.domain.project.domain.services.project_policy import ProjectLifecyclePolicy
from app.domain.project.domain.value_objects.language import ProjectLanguage
from app.domain.project.domain.value_objects.member import ProjectMember
from app.domain.project.domain.value_objects.member_role import MemberRole
from app.domain.project.domain.value_objects.project_status import (
    ProjectStatus,
    ProjectStatusEnum,
)


class Project(AggregateRoot):
    """项目聚合根。"""

    def __init__(
        self,
        *,
        project_id: str,
        name: str,
        description: str = "",
        repo_url: str = "",
        language: str = "python",
        path: str = "",
        status: str = "active",
        organization_id: str = "",
        deleted: bool = False,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        members: Optional[List[dict]] = None,
    ):
        self.id = Identifier.of(project_id)
        self._name = (name or "").strip()
        self._description = description or ""
        self._repo_url = repo_url or ""
        self._language = ProjectLanguage(language)
        self._path = path or ""
        self._organization_id = organization_id or ""
        self._status = ProjectStatus(status)
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._deleted: bool = bool(deleted or self._status.is_deleted)
        self._members: List[ProjectMember] = []
        for m in (members or []):
            self._members.append(ProjectMember.from_dict(m) if isinstance(m, dict) else m)
        self._domain_events = []
        if not self._name:
            raise DomainValidationError("项目名称不能为空")

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def repo_url(self) -> str:
        return self._repo_url

    @property
    def language(self) -> str:
        return str(self._language)

    @property
    def path(self) -> str:
        return self._path

    @property
    def organization_id(self) -> str:
        return self._organization_id

    @property
    def status(self) -> ProjectStatus:
        return self._status

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def members(self) -> List[ProjectMember]:
        return list(self._members)

    @property
    def deleted(self) -> bool:
        return self._deleted or self._status.is_deleted

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 业务命令（守护不变量）────────────────────────
    def rename(self, new_name: str, operator: str = "system") -> None:
        """修改项目名称。"""
        self._ensure_active_aggregate()
        nt = (new_name or "").strip()
        if not nt:
            raise DomainValidationError("项目名称不能为空")
        if nt == self._name:
            return
        old = self._name
        self._name = nt
        self._touch()
        self.record_event(ProjectRenamed(self.id.value, old, nt, operator))

    def change_description(self, text: str, operator: str = "system") -> None:
        self._ensure_active_aggregate()
        self._description = text or ""
        self._touch()
        self.record_event(ProjectInfoChanged(self.id.value, "description", operator))

    def change_language(self, language: str, operator: str = "system") -> None:
        self._ensure_active_aggregate()
        self._language = ProjectLanguage(language)
        self._touch()
        self.record_event(ProjectInfoChanged(self.id.value, "language", operator))

    def set_repo(self, *, repo_url: str = None, path: str = None,
                 operator: str = "system") -> None:
        """更新仓库地址与本地路径（聚合内部原子更新）。"""
        self._ensure_active_aggregate()
        changed = False
        if repo_url is not None:
            self._repo_url = repo_url
            changed = True
        if path is not None:
            self._path = path
            changed = True
        if changed:
            self._touch()
            self.record_event(ProjectInfoChanged(self.id.value, "repo", operator))

    def set_organization(self, organization_id: str, operator: str = "system") -> None:
        self._ensure_active_aggregate()
        self._organization_id = organization_id or ""
        self._touch()
        self.record_event(ProjectInfoChanged(self.id.value, "organization", operator))

    def archive(self, operator: str = "system") -> None:
        """归档/停用项目：active -> archived。"""
        self._ensure_active_aggregate()
        old = self._status.value.value
        self._status = ProjectStatus(ProjectStatusEnum.ARCHIVED)
        self._touch()
        self.record_event(ProjectStatusChanged(
            self.id.value, old, ProjectStatusEnum.ARCHIVED.value, operator))
        self.record_event(ProjectArchived(self.id.value, operator))

    def activate(self, operator: str = "system") -> None:
        """启用/恢复项目：archived -> active。"""
        self._ensure_active_aggregate()
        old = self._status.value.value
        self._status = ProjectStatus(ProjectStatusEnum.ACTIVE)
        self._touch()
        self.record_event(ProjectStatusChanged(
            self.id.value, old, ProjectStatusEnum.ACTIVE.value, operator))
        self.record_event(ProjectActivated(self.id.value, operator))

    def change_status(self, target: str, operator: str = "system") -> None:
        """受状态机约束的状态迁移（active/archived）。"""
        self._ensure_active_aggregate()
        target_status = ProjectStatus(target)
        ProjectLifecyclePolicy().ensure_transition_allowed(self._status, target_status)
        if self._status.value is target_status.value:
            return
        old = self._status.value.value
        self._status = target_status
        self._touch()
        self.record_event(ProjectStatusChanged(self.id.value, old, target_status.value.value, operator))

    def delete(self, operator: str = "system") -> None:
        """软删除：项目进入回收站。"""
        if self._deleted or self._status.is_deleted:
            raise DomainValidationError("项目已在回收站，不可重复删除")
        old = self._status.value.value
        self._status = ProjectStatus(ProjectStatusEnum.DELETED)
        self._deleted = True
        self._touch()
        self.record_event(ProjectSoftDeleted(self.id.value, operator))
        self.record_event(ProjectStatusChanged(
            self.id.value, old, "deleted", operator))

    def restore(self, operator: str = "system") -> None:
        """从回收站恢复为启用（active）。"""
        if not self._deleted and not self._status.is_deleted:
            raise DomainValidationError("项目不在回收站，无需恢复")
        old = self._status.value.value
        self._status = ProjectStatus(ProjectStatusEnum.ACTIVE)
        self._deleted = False
        self._touch()
        self.record_event(ProjectRestored(self.id.value, operator))
        self.record_event(ProjectStatusChanged(
            self.id.value, old, ProjectStatusEnum.ACTIVE.value, operator))

    # ── 成员管理（聚合内子实体）──────────────────────
    def add_member(self, *, user_id: str = "", username: str = "",
                   name: str = "", email: str = "", role: str = "member",
                   user_group: str = "", operator: str = "system") -> None:
        """添加项目成员（去重：同一 user_id/username 不重复加入）。"""
        self._ensure_active_aggregate()
        identity = user_id or username
        if not identity:
            raise DomainValidationError("项目成员缺少 user_id 或 username")
        normalized_role = str(MemberRole(role))
        if any(m.identity == identity for m in self._members):
            # 幂等：已存在则仅更新角色信息
            idx = next(i for i, m in enumerate(self._members) if m.identity == identity)
            self._members[idx] = ProjectMember(
                user_id=user_id, username=username, name=name or username,
                email=email, role=normalized_role, user_group=user_group,
            )
            self._touch()
            return
        self._members.append(ProjectMember(
            user_id=user_id, username=username, name=name or username,
            email=email, role=normalized_role, user_group=user_group,
        ))
        self._touch()
        self.record_event(ProjectMemberAdded(self.id.value, identity, normalized_role, operator))

    def remove_member(self, *, user_id: str = "", operator: str = "system") -> bool:
        """移除项目成员。返回是否移除成功。"""
        self._ensure_active_aggregate()
        identity = user_id
        before = len(self._members)
        self._members = [m for m in self._members if m.identity != identity]
        removed = len(self._members) < before
        if removed:
            self._touch()
            self.record_event(ProjectMemberRemoved(self.id.value, identity, operator))
        return removed

    def update_member_role(self, user_id: str, role: str) -> None:
        """更新某成员角色。"""
        self._ensure_active_aggregate()
        normalized = str(MemberRole(role))
        for i, m in enumerate(self._members):
            if m.identity == user_id:
                d = m.to_dict()
                d["role"] = normalized
                self._members[i] = ProjectMember.from_dict(d)
                self._touch()
                return
        raise DomainValidationError(f"项目成员不存在: {user_id}")

    def _ensure_active_aggregate(self) -> None:
        """聚合级不变量：回收站项目禁止一切修改命令。"""
        if self._deleted or self._status.is_deleted:
            raise DomainValidationError("项目已在回收站，不可操作")

    # ── 快照 / 持久化 ───────────────────────────────
    def snapshot(self) -> dict:
        return {
            "name": self._name,
            "description": self._description,
            "repo_url": self._repo_url,
            "language": self._language.value.value,
            "path": self._path,
            "status": self._status.value.value,
            "organization_id": self._organization_id,
        }

    def to_dict(self) -> dict:
        """导出可落库/可返回给上层视图层的字典。"""
        return {
            "id": self.id.value,
            "name": self._name,
            "description": self._description,
            "repo_url": self._repo_url,
            "language": self._language.value.value,
            "path": self._path,
            "status": self._status.value.value,
            "organization_id": self._organization_id,
            "deleted": self._deleted,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "members": [m.to_dict() for m in self._members],
        }

    @staticmethod
    def from_dict(data: dict) -> "Project":
        """从持久化字典/仓储返回行重建聚合。"""
        data = data or {}
        return Project(
            project_id=str(data.get("id") or data.get("project_id") or ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            repo_url=data.get("repo_url", ""),
            language=data.get("language", "python"),
            path=data.get("path", ""),
            status=data.get("status", "active"),
            organization_id=data.get("organization_id", ""),
            deleted=bool(data.get("deleted")),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            members=data.get("members") or [],
        )
