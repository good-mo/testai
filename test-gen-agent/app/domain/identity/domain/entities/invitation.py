"""邀请聚合根 Invitation。

承载邀请注册/加入组织的不变量：邀请需在有效期内且未被使用才能用于注册。
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import InvariantViolation
from app.domain.identity.domain.events import (
    InvitationAccepted,
    InvitationIssued,
    InvitationRevoked,
)
from app.domain.identity.domain.value_objects.invitation_status import (
    InvitationStatus,
    InvitationStatusEnum,
)


class Invitation(AggregateRoot):
    """邀请聚合根。"""

    def __init__(
        self,
        *,
        invite_id: str,
        email: str = "",
        scope: str = "SYSTEM",
        organization_id: str = "",
        project_id: str = "",
        role_ids: Optional[list] = None,
        expire_time: Optional[float] = None,
        used: int = 0,
        create_time: Optional[float] = None,
        create_user: str = "admin",
        ttl: float = 7 * 24 * 3600,
    ):
        self.id = Identifier.of(invite_id)
        self._email = email or ""
        self._scope = scope or "SYSTEM"
        self._organization_id = organization_id or ""
        self._project_id = project_id or ""
        self._role_ids = list(role_ids or [])
        now = time.time()
        self._create_time = create_time if create_time is not None else now
        self._expire_time = expire_time if expire_time is not None else self._create_time + ttl
        self._used = int(used or 0)
        self._create_user = create_user or "admin"
        self._domain_events = []
        self.version = 0

    # ── 只读属性 ─────────────────────────────────────
    @property
    def email(self) -> str:
        return self._email

    @property
    def scope(self) -> str:
        return self._scope

    @property
    def organization_id(self) -> str:
        return self._organization_id

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def role_ids(self) -> List[str]:
        return list(self._role_ids)

    @property
    def expire_time(self) -> float:
        return self._expire_time

    @property
    def used(self) -> bool:
        return self._used == 1

    @property
    def create_time(self) -> float:
        return self._create_time

    @property
    def create_user(self) -> str:
        return self._create_user

    def status(self, now: Optional[float] = None) -> InvitationStatus:
        now = now if now is not None else time.time()
        if self.used:
            return InvitationStatus(InvitationStatusEnum.USED.value)
        if now > self._expire_time:
            return InvitationStatus(InvitationStatusEnum.EXPIRED.value)
        return InvitationStatus(InvitationStatusEnum.PENDING.value)

    # ── 业务命令 ─────────────────────────────────────
    def revoke(self, operator: str = "system") -> None:
        self._used = 1  # 复用 used 位表达撤销（已使用不可再用）
        self.record_event(InvitationRevoked(self.id.value, operator))

    def mark_issued(self, operator: str = "system") -> None:
        self.record_event(InvitationIssued(self.id.value, self._email, self._scope, operator))

    def accept(self, operator: str = "system") -> None:
        """使用邀请注册；校验未使用且未过期。"""
        st = self.status()
        if not st.usable:
            raise InvariantViolation(f"邀请已失效（{st.value}），不能用于注册")
        self._used = 1
        self.record_event(InvitationAccepted(self.id.value, self._email, operator))

    def to_dict(self) -> dict:
        return {
            "invite_id": self.id.value,
            "email": self._email,
            "scope": self._scope,
            "organization_id": self._organization_id,
            "project_id": self._project_id,
            "role_ids": list(self._role_ids),
            "expire_time": self._expire_time,
            "used": self._used,
            "create_time": self._create_time,
            "create_user": self._create_user,
            "status": self.status().value,
        }

    @staticmethod
    def from_dict(data: dict) -> "Invitation":
        return Invitation(
            invite_id=str(data.get("invite_id") or data.get("id") or ""),
            email=data.get("email", ""),
            scope=data.get("scope", "SYSTEM"),
            organization_id=data.get("organization_id", ""),
            project_id=data.get("project_id", ""),
            role_ids=data.get("role_ids") or [],
            expire_time=data.get("expire_time"),
            used=data.get("used", 0),
            create_time=data.get("create_time"),
            create_user=data.get("create_user", "admin"),
        )
