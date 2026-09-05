"""调试应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class GetDebugItemCommand:
    debug_id: str = ""

@dataclass
class SaveDebugItemCommand:
    debug_id: str = ""
    name: str = "未命名调试"
    protocol: str = "HTTP"
    method: str = "GET"
    path: str = "/"
    url: str = "/"
    project_id: str = ""
    module_id: str = "root"
    request_data: Dict[str, Any] = field(default_factory=dict)
    response_data: Dict[str, Any] = field(default_factory=dict)
    create_user: str = "admin"
    update_user: str = "admin"
    num: int = 0

@dataclass
class DeleteDebugItemCommand:
    debug_id: str = ""

__all__ = ["GetDebugItemCommand", "SaveDebugItemCommand", "DeleteDebugItemCommand"]
