"""系统管理仓储接口（轻域 - 委托 identity DDD）。"""
from __future__ import annotations

from typing import Protocol


class AdminRepository(Protocol):
    """系统管理委托接口。"""
    def enable_organization(self, org_id: str) -> bool: ...
    def disable_organization(self, org_id: str) -> bool: ...
    def remove_org_member(self, org_id: str, user_id: str) -> bool: ...

__all__ = ["AdminRepository"]
