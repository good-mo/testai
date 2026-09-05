"""邀请注册业务逻辑层（identity 域 DDD 接入 · 阶段 C 薄门面）。

承接 app/domain/identity 领域层的对外业务语义，作为 router 层唯一业务入口。
本四层 Service 收敛为对 DDD 应用服务 `IdentityAppService` / 仓储适配器的
**薄委托门面**，仅保留历史方法签名以兼容既有调用方 / 便于回滚。对外语义
与返回形状与重构前保持一致（复用 DDD Invitation 聚合 to_dict 承载 invite_id）。

覆盖「邀请注册」全流程：
  - 创建邀请（SYSTEM / ORGANIZATION / PROJECT 三个 scope）
  - 校验邀请有效性
  - 读取邀请详情
  - 标记邀请已使用
"""
from __future__ import annotations

from typing import List, Optional

from app.domain.identity.application.dto import IssueInvitationCommand
from app.domain.identity.application.identity_app_service import (
    identity_app_service as _ddd_service,
)
from app.domain.identity.domain.repository import InvitationRepository
from app.domain.identity.infrastructure.identity_repository_impl import (
    InvitationRepoAdapter,
)


class InvitationService:
    """邀请注册服务：router 层唯一业务编排入口（identity 域 DDD 薄门面）。"""

    def __init__(self, invites: InvitationRepository = None):
        # 领域仓储适配器（防腐层：翻译为既有 InvitationRepo）
        self._invites: InvitationRepository = invites or InvitationRepoAdapter()

    # ── 创建 ──────────────────────────────────────────────
    def create_invite(self, emails: List[str], scope: str = "SYSTEM",
                      organization_id: str = "", project_id: str = "",
                      role_ids: Optional[List[str]] = None,
                      create_user: str = "admin",
                      ttl: Optional[float] = None) -> Optional[dict]:
        """为一批邮箱创建邀请记录，返回第一条（含 invite_id）。

        委托 identity 域 DDD 应用服务：聚合守护邀请不变量（邮箱合法、未用/
        未过期才能用于注册）。空邮箱列表 / 非法邮箱返回 None，兼容既有契约。
        """
        if not emails:
            return None
        email = str(emails[0] or "").strip()
        if not email or "@" not in email:
            # 兼容既有：邮箱不合法返回 None（不改动 router 分支语义）
            return None
        try:
            result = _ddd_service.issue_invitation(IssueInvitationCommand(
                email=email,
                scope=scope or "SYSTEM",
                organization_id=organization_id or "",
                project_id=project_id or "",
                role_ids=list(role_ids or []),
                create_user=create_user or "admin",
                operator=create_user or "admin",
            ))
        except Exception:
            return None
        return result if result else None

    # ── 查询 ──────────────────────────────────────────────
    def get_by_invite_id(self, invite_id: str) -> Optional[dict]:
        """按 invite_id 查找邀请（返回 Invitation 聚合字典，含 invite_id）。"""
        if not invite_id:
            return None
        return _ddd_service.get_invitation(invite_id)

    def is_valid(self, invite_id: str) -> bool:
        """邀请是否有效（存在、未过期、未使用）。"""
        if not invite_id:
            return False
        return self._invites.is_valid(invite_id)

    # ── 状态变更 ──────────────────────────────────────────
    def mark_used(self, invite_id: str) -> bool:
        """标记邀请已使用。"""
        if not invite_id:
            return False
        return self._invites.mark_used(invite_id)


# 模块级单例（与其它 service 风格一致）
invitation_service = InvitationService()


__all__ = ["invitation_service", "InvitationService"]
