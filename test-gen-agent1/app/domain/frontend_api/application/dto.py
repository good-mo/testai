"""前端兼容应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ImportFromPostmanCommand:
    data: dict = field(default_factory=dict)

@dataclass
class ImportFromSwaggerCommand:
    data: dict = field(default_factory=dict)

__all__ = ["ImportFromPostmanCommand", "ImportFromSwaggerCommand"]
