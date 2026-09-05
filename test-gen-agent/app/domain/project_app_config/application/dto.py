"""项目应用配置应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class GetModuleConfigCommand:
    project_id: str = ""
    module: str = ""

@dataclass
class SaveModuleConfigCommand:
    project_id: str = ""
    module: str = ""
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SetConfigValueCommand:
    project_id: str = ""
    module: str = ""
    config_key: str = ""
    value: Any = ""

@dataclass
class GetConfigValueCommand:
    project_id: str = ""
    module: str = ""
    config_key: str = ""
    default: str = ""

@dataclass
class ListAllModulesCommand:
    project_id: str = ""

__all__ = ["GetModuleConfigCommand", "SaveModuleConfigCommand", "SetConfigValueCommand",
           "GetConfigValueCommand", "ListAllModulesCommand"]
