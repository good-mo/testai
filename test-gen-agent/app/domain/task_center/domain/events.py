"""任务中心领域事件。"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class TaskBatchStopped(DomainEvent):
    def __init__(self, task_ids: list, operator: str = "system"):
        super().__init__()
        self.task_ids = task_ids
        self.operator = operator

class ScheduleEnabledChanged(DomainEvent):
    def __init__(self, schedule_ids: list, enable: bool, operator: str = "system"):
        super().__init__()
        self.schedule_ids = schedule_ids
        self.enable = enable
        self.operator = operator

__all__ = ["TaskBatchStopped", "ScheduleEnabledChanged"]
