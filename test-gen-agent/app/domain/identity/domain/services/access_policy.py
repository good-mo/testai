"""身份与访问领域服务：跨聚合/对象的不变量策略。

将"组织成员能否管理成员""角色是否具备某权限""用户能否执行操作"等授权
规则抽成可测试的无状态策略，供聚合与权限校验复用，避免规则散落各处。
"""
from __future__ import annotations

from app.domain.common.exceptions import InvariantViolation
from app.domain.identity.domain.value_objects.member_role import (
    MemberRole,
    MemberRoleEnum,
)
from app.domain.identity.domain.value_objects.permission import PermissionSet


class AccessPolicy:
    """身份访问控制策略（无状态领域服务）。"""

    def ensure_can_manage_members(self, actor_role: MemberRole, target_role: MemberRole) -> None:
        """校验执行者是否有权对目标成员进行管理操作。

        规则：执行者需 owner/admin，且不能操作比自己权限更高的对象。
        """
        if not actor_role.can_manage():
            raise InvariantViolation(f"角色 '{actor_role}' 无权管理组织成员")
        if target_role.level > actor_role.level:
            raise InvariantViolation(
                f"角色 '{actor_role}' 不能管理更高权限的成员 '{target_role}'")

    def ensure_can_change_role(self, actor_role: MemberRole, new_role: str) -> None:
        """校验执行者能否将某人改为新角色（不高于自身）。"""
        if not actor_role.can_manage():
            raise InvariantViolation("无权限变更成员角色")
        new = MemberRole(new_role)
        if new.level > actor_role.level:
            raise InvariantViolation(f"不能授予高于自身 '{actor_role}' 的角色 '{new}'")

    def ensure_permission(self, granted: PermissionSet, required: str) -> None:
        """校验是否具备某权限。"""
        if not granted.has(required):
            raise InvariantViolation(f"缺少权限: {required}")

    def merge_permissions(self, *groups: PermissionSet) -> PermissionSet:
        """合并多角色权限。"""
        merged = PermissionSet([])
        for g in groups:
            merged = merged.union(g)
        return merged


# 全局默认普通成员角色（供缺省场景）
DEFAULT_MEMBER_ROLE = MemberRoleEnum.MEMBER.value
