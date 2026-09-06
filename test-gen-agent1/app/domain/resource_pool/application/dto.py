"""资源池应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ListPoolsCommand:
    keyword: str = ""

@dataclass
class GetPoolCommand:
    pool_id: str = ""

@dataclass
class CreatePoolCommand:
    name: str = "未命名资源池"
    description: str = ""
    enable: bool = True

@dataclass
class UpdatePoolCommand:
    pool_id: str = ""
    name: Optional[str] = None
    description: Optional[str] = None

@dataclass
class DeletePoolCommand:
    pool_id: str = ""

@dataclass
class SetEnableCommand:
    pool_id: str = ""
    enable: bool = True

__all__ = ["ListPoolsCommand", "GetPoolCommand", "CreatePoolCommand",
           "UpdatePoolCommand", "DeletePoolCommand", "SetEnableCommand"]
