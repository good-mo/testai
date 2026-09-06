"""性能测试领域事件。

事件表达「性能测试任务聚合内发生的事实」，供应用层在事务提交后发布，
驱动报告记录、审计、通知等跨域副作用解耦。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class PerformanceTestCreated(DomainEvent):
    def __init__(self, test_id: str, target_name: str, operator: str = "system"):
        super().__init__(aggregate_id=test_id)
        self.target_name = target_name
        self.operator = operator


class PerformanceTestStarted(DomainEvent):
    def __init__(self, test_id: str, target_name: str, operator: str = "system"):
        super().__init__(aggregate_id=test_id)
        self.target_name = target_name
        self.operator = operator


class PerformanceTestCompleted(DomainEvent):
    """性能测试进入终结态（达标/不达标/跳过）。"""

    def __init__(
        self,
        test_id: str,
        target_name: str,
        status: str,
        passed: bool,
        operator: str = "system",
    ):
        super().__init__(aggregate_id=test_id)
        self.target_name = target_name
        self.status = status
        self.passed = passed
        self.operator = operator


class PerformanceTestPassed(DomainEvent):
    def __init__(self, test_id: str, target_name: str, operator: str = "system"):
        super().__init__(aggregate_id=test_id)
        self.target_name = target_name
        self.operator = operator


class PerformanceTestFailed(DomainEvent):
    def __init__(
        self, test_id: str, target_name: str, reason: str = "", operator: str = "system"
    ):
        super().__init__(aggregate_id=test_id)
        self.target_name = target_name
        self.reason = reason
        self.operator = operator


class PerformanceTestSkipped(DomainEvent):
    def __init__(
        self, test_id: str, target_name: str, reason: str = "", operator: str = "system"
    ):
        super().__init__(aggregate_id=test_id)
        self.target_name = target_name
        self.reason = reason
        self.operator = operator


class SLOThresholdUpdated(DomainEvent):
    def __init__(self, test_id: str, operator: str = "system"):
        super().__init__(aggregate_id=test_id)
        self.operator = operator


__all__ = [
    "PerformanceTestCreated",
    "PerformanceTestStarted",
    "PerformanceTestCompleted",
    "PerformanceTestPassed",
    "PerformanceTestFailed",
    "PerformanceTestSkipped",
    "SLOThresholdUpdated",
]
