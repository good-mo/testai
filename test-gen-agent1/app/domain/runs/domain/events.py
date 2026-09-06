"""任务运行领域事件。

事件表达"聚合内发生的事实"，供应用层在事务提交后发布，
进而驱动通知、进度刷新、审计等跨域副作用解耦。

同时承载"运行记录（RunRecord / 报告）"的事件集，与 Task 任务中心
生命周期事件并存。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent

__all__ = [
    # Task 生命周期
    "TaskCreated", "TaskStarted", "TaskSucceeded", "TaskFailed",
    "TaskCancelled", "TaskRequeued",
    # 运行记录 / 报告
    "RunRecordSaved", "RunRecordRenamed", "RunRecordDeleted",
    "RunRecordBatchDeleted", "RunRecordCleared",
]


class TaskCreated(DomainEvent):
    def __init__(self, task_id: str, coro_name: str = ""):
        super().__init__(aggregate_id=task_id)
        self.coro_name = coro_name


class TaskStarted(DomainEvent):
    def __init__(self, task_id: str, worker: str = ""):
        super().__init__(aggregate_id=task_id)
        self.worker = worker


class TaskSucceeded(DomainEvent):
    def __init__(self, task_id: str):
        super().__init__(aggregate_id=task_id)


class TaskFailed(DomainEvent):
    def __init__(self, task_id: str, error: str = ""):
        super().__init__(aggregate_id=task_id)
        self.error = error


class TaskCancelled(DomainEvent):
    def __init__(self, task_id: str):
        super().__init__(aggregate_id=task_id)


class TaskRequeued(DomainEvent):
    def __init__(self, task_id: str):
        super().__init__(aggregate_id=task_id)


# ── 运行记录（RunRecord / 报告）事件 ───────────────────
class RunRecordSaved(DomainEvent):
    """一条运行记录已保存/登记。"""

    def __init__(self, record_id: str, file_path: str = "",
                 source: str = "", passed: bool = False):
        super().__init__(aggregate_id=record_id)
        self.file_path = file_path
        self.source = source
        self.passed = passed


class RunRecordRenamed(DomainEvent):
    """运行记录（报告名）已重命名。"""

    def __init__(self, record_id: str, new_name: str):
        super().__init__(aggregate_id=record_id)
        self.new_name = new_name


class RunRecordDeleted(DomainEvent):
    """一条运行记录已删除。"""

    def __init__(self, record_id: str):
        super().__init__(aggregate_id=record_id)


class RunRecordBatchDeleted(DomainEvent):
    """批量删除运行记录。"""

    def __init__(self, record_ids: list, deleted: int = 0):
        super().__init__(aggregate_id=",".join(record_ids) or "-")
        self.record_ids = list(record_ids)
        self.deleted = deleted


class RunRecordCleared(DomainEvent):
    """清空运行记录（可选按来源）。"""

    def __init__(self, source: str = "", cleared: int = 0):
        super().__init__(aggregate_id=source or "all")
        self.source = source
        self.cleared = cleared
