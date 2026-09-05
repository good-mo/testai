"""报告领域事件。

事件表达"聚合内发生的事实"，供应用层在事务提交后发布，从而与审计、
统计、通知等跨域副作用解耦。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class ReportGenerated(DomainEvent):
    """一份测试报告已生成（report_name 为报告文件名）。"""

    def __init__(self, report_name: str, report_format: str = "html",
                 operator: str = "system"):
        super().__init__(aggregate_id=report_name)
        self.report_format = report_format
        self.operator = operator


class ReportTrashed(DomainEvent):
    """报告产物被移入回收站。"""

    def __init__(self, report_name: str, operator: str = "system"):
        super().__init__(aggregate_id=report_name)
        self.operator = operator


class ReportRestored(DomainEvent):
    """报告产物从回收站恢复。"""

    def __init__(self, report_name: str, operator: str = "system"):
        super().__init__(aggregate_id=report_name)
        self.operator = operator


class ReportPurged(DomainEvent):
    """报告产物被彻底删除。"""

    def __init__(self, report_name: str, operator: str = "system"):
        super().__init__(aggregate_id=report_name)
        self.operator = operator


__all__ = [
    "ReportGenerated",
    "ReportTrashed",
    "ReportRestored",
    "ReportPurged",
]
