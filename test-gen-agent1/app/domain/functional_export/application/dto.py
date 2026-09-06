"""功能用例导出应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ExportCasesCommand:
    body: Dict[str, Any] = field(default_factory=dict)
    kind: str = "excel"  # "excel" or "xmind"

__all__ = ["ExportCasesCommand"]
