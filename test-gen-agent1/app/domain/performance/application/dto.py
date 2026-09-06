"""性能测试应用层输入/输出 DTO。

应用层面向「性能测试任务」操作接收显式 DTO（而非裸 dict），与 Web 层
Pydantic 请求体解耦。此处用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CreatePerformanceTestCommand:
    """新建一次性能测试任务。"""

    target_name: str
    source_ref: str = ""
    thresholds: List[Dict[str, Any]] = field(default_factory=list)
    operator: str = "system"


@dataclass
class StartTestCommand:
    test_id: str
    operator: str = "system"


@dataclass
class RecordResultCommand:
    """写入一次基准结果（自动判定 SLO 达标）。"""

    test_id: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    slo_result: Optional[Dict[str, Any]] = None
    operator: str = "system"


@dataclass
class FailTestCommand:
    test_id: str
    reason: str = ""
    operator: str = "system"


@dataclass
class SkipTestCommand:
    test_id: str
    reason: str = ""
    operator: str = "system"


@dataclass
class ConfigureThresholdsCommand:
    test_id: str
    thresholds: List[Dict[str, Any]] = field(default_factory=list)
    operator: str = "system"


@dataclass
class PerformanceListQuery:
    status: str = ""
    target_name: str = ""
    limit: int = 100
    offset: int = 0


__all__ = [
    "CreatePerformanceTestCommand",
    "StartTestCommand",
    "RecordResultCommand",
    "FailTestCommand",
    "SkipTestCommand",
    "ConfigureThresholdsCommand",
    "PerformanceListQuery",
]
