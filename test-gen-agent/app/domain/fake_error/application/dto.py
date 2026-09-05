"""误报规则应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ListRulesCommand:
    project_id: str = ""

@dataclass
class SaveRuleItem:
    id: str = ""
    name: str = ""
    type: str = ""
    enable: bool = True
    respType: str = ""
    relation: str = ""
    expression: str = ""
    projectId: str = ""

@dataclass
class AddRulesCommand:
    items: List[SaveRuleItem] = field(default_factory=list)
    project_id: str = ""

@dataclass
class UpdateRulesCommand:
    items: List[SaveRuleItem] = field(default_factory=list)

@dataclass
class DeleteRulesCommand:
    ids: List[str] = field(default_factory=list)

@dataclass
class UpdateEnableCommand:
    ids: List[str] = field(default_factory=list)
    enable: bool = True

__all__ = ["ListRulesCommand", "SaveRuleItem", "AddRulesCommand",
           "UpdateRulesCommand", "DeleteRulesCommand", "UpdateEnableCommand"]
