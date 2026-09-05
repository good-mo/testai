"""数据工厂应用层输入/输出 DTO。

应用层面向"数据模板/批次"操作接收显式 DTO（而非裸 dict），与 Web 层
Pydantic 请求体解耦。用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CreateTemplateCommand:
    name: str
    description: str = ""
    category: str = "custom"
    schema_def: Optional[Dict[str, Any]] = None
    deps: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    operator: str = "system"


@dataclass
class UpdateTemplateCommand:
    template_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    schema_def: Optional[Dict[str, Any]] = None
    deps: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    operator: str = "system"


@dataclass
class GenerateCommand:
    template_id: str
    batch_size: int = 1
    env_key: str = ""
    operator: str = "system"


@dataclass
class CleanupCommand:
    batch_id: str = ""
    template_id: str = ""
    env_key: str = ""
    operator: str = "system"


@dataclass
class TemplateListQuery:
    category: str = ""
    search: str = ""
    limit: int = 100
    offset: int = 0


__all__ = [
    "CreateTemplateCommand",
    "UpdateTemplateCommand",
    "GenerateCommand",
    "CleanupCommand",
    "TemplateListQuery",
]
