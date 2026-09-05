"""AI 配置应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class GetAiConfigCommand:
    """获取 AI 配置。"""
    scope: str = "functional_case"
    owner: str = ""
    project_id: str = ""
    config_type: str = "default"


@dataclass
class SaveAiConfigCommand:
    """保存 AI 配置。"""
    scope: str = "functional_case"
    config_value: Dict[str, Any] = field(default_factory=dict)
    owner: str = ""
    project_id: str = ""
    config_type: str = "default"
    create_user: str = "admin"


@dataclass
class DeleteAiConfigCommand:
    """删除 AI 配置。"""
    scope: str = "functional_case"
    owner: str = ""
    project_id: str = ""
    config_type: str = "default"


__all__ = ["GetAiConfigCommand", "SaveAiConfigCommand", "DeleteAiConfigCommand"]
