"""系统管理应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EnableOrgCommand:
    org_id: str = ""

@dataclass
class DisableOrgCommand:
    org_id: str = ""

@dataclass
class RemoveMemberCommand:
    org_id: str = ""
    user_id: str = ""

__all__ = ["EnableOrgCommand", "DisableOrgCommand", "RemoveMemberCommand"]
