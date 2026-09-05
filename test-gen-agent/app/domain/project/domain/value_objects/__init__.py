"""项目上下文值对象集。

不可变值对象：ProjectStatus（生命周期）、MemberRole（成员角色）、
ProjectLanguage（主语言）、ProjectMember（成员快照）。
"""
from __future__ import annotations

from app.domain.project.domain.value_objects.language import (
    ProjectLanguage,
    ProjectLanguageEnum,
)
from app.domain.project.domain.value_objects.member import ProjectMember
from app.domain.project.domain.value_objects.member_role import MemberRole, MemberRoleEnum
from app.domain.project.domain.value_objects.project_status import (
    PERSISTABLE_STATUSES,
    ProjectStatus,
    ProjectStatusEnum,
)

__all__ = [
    "ProjectStatus",
    "ProjectStatusEnum",
    "PERSISTABLE_STATUSES",
    "MemberRole",
    "MemberRoleEnum",
    "ProjectMember",
    "ProjectLanguage",
    "ProjectLanguageEnum",
]
