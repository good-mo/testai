"""工作流状态应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ListStatusesCommand:
    scope_type: str = "PROJECT"
    scope_id: str = ""
    scene: str = "FUNCTIONAL"

@dataclass
class GetStatusCommand:
    status_id: str = ""

@dataclass
class CreateStatusCommand:
    name: str = ""
    scene: str = "FUNCTIONAL"
    scope_id: str = ""
    scope_type: str = "PROJECT"
    remark: str = ""
    all_transfer_to: bool = False
    create_user: str = "admin"

@dataclass
class UpdateStatusCommand:
    status_id: str = ""
    name: Optional[str] = None
    remark: Optional[str] = None
    all_transfer_to: Optional[bool] = None
    status_definitions: Optional[List[str]] = None

@dataclass
class DeleteStatusCommand:
    status_id: str = ""

@dataclass
class SortStatusesCommand:
    status_ids: List[str] = field(default_factory=list)

@dataclass
class UpdateFlowsCommand:
    status_id: str = ""
    target_ids: List[str] = field(default_factory=list)

@dataclass
class SetDefinitionCommand:
    status_id: str = ""
    definition_id: str = ""
    enable: bool = True

@dataclass
class SeedDefaultsCommand:
    scope_type: str = "PROJECT"
    scope_id: str = ""
    scene: str = "FUNCTIONAL"

__all__ = ["ListStatusesCommand", "GetStatusCommand", "CreateStatusCommand",
           "UpdateStatusCommand", "DeleteStatusCommand", "SortStatusesCommand",
           "UpdateFlowsCommand", "SetDefinitionCommand", "SeedDefaultsCommand"]
