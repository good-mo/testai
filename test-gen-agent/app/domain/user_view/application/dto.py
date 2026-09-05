"""用户视图应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ListUserViewsCommand:
    view_type: str = ""
    scope_id: str = ""

@dataclass
class GetUserViewCommand:
    view_id: str = ""

@dataclass
class CreateUserViewCommand:
    view_type: str = ""
    scope_id: str = ""
    body: Dict[str, Any] = field(default_factory=dict)
    user_id: str = "admin"
    new_id: str = ""

@dataclass
class UpdateUserViewCommand:
    view_id: str = ""
    body: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DeleteUserViewCommand:
    view_id: str = ""

__all__ = ["ListUserViewsCommand", "GetUserViewCommand", "CreateUserViewCommand",
           "UpdateUserViewCommand", "DeleteUserViewCommand"]
