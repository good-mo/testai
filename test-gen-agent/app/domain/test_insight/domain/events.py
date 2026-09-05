"""TestInsight 领域事件。

表达"一次执行追溯已入账"等已发生的事实，供应用层在事务提交后
发布，驱动统计/审计/通知等副作用解耦。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class TraceRunRecorded(DomainEvent):
    """一次测试执行已记录入账。"""

    def __init__(self, trace_id: str, file_path: str, operator: str = "system"):
        super().__init__(aggregate_id=trace_id)
        self.file_path = file_path
        self.operator = operator
