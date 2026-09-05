"""项目版本应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ListVersionsCommand:
    project_id: str = ""
    keyword: str = ""

@dataclass
class GetVersionCommand:
    version_id: str = ""

@dataclass
class CreateVersionCommand:
    project_id: str = ""
    name: str = ""
    description: str = ""
    status: bool = False
    latest: bool = False
    publish_time: float = 0.0
    create_user: str = "admin"

@dataclass
class UpdateVersionCommand:
    version_id: str = ""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[bool] = None
    latest: Optional[bool] = None
    publish_time: Optional[float] = None

@dataclass
class DeleteVersionCommand:
    version_id: str = ""

@dataclass
class VersionOptionsCommand:
    project_id: str = ""

__all__ = ["ListVersionsCommand", "GetVersionCommand", "CreateVersionCommand",
           "UpdateVersionCommand", "DeleteVersionCommand", "VersionOptionsCommand"]
