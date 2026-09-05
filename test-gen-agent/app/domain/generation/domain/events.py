"""生成编排领域事件。

事件表达"聚合内发生的事实"，供应用层在事务提交后发布，进而驱动审计、
通知、报告刷新等副作用（跨聚合/跨域解耦）。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class GenerationJobCreated(DomainEvent):
    """生成任务已创建（提交）。"""

    def __init__(self, job_id: str, file_path: str = "", source: str = "single",
                 operator: str = "system"):
        super().__init__(aggregate_id=job_id)
        self.file_path = file_path
        self.source = source
        self.operator = operator


class GenerationJobStarted(DomainEvent):
    """生成任务开始执行（进入 running）。"""

    def __init__(self, job_id: str, operator: str = "system"):
        super().__init__(aggregate_id=job_id)
        self.operator = operator


class GenerationStepCompleted(DomainEvent):
    """一次生成步骤完成。"""

    def __init__(self, job_id: str, node_name: str, status: str = "done",
                 operator: str = "system"):
        super().__init__(aggregate_id=job_id)
        self.node_name = node_name
        self.status = status
        self.operator = operator


class GenerationRetried(DomainEvent):
    """测试失败触发一次修复重试。"""

    def __init__(self, job_id: str, attempt: int, reason: str = "",
                 operator: str = "system"):
        super().__init__(aggregate_id=job_id)
        self.attempt = attempt
        self.reason = reason
        self.operator = operator


class GenerationJobSucceeded(DomainEvent):
    """生成任务成功（生成通过验证的测试 / 仅结构化）。"""

    def __init__(self, job_id: str, generated_tests: str = "",
                 operator: str = "system"):
        super().__init__(aggregate_id=job_id)
        self.generated_tests = generated_tests
        self.operator = operator


class GenerationJobFailed(DomainEvent):
    """生成任务失败（不可恢复错误 / 超重试上限 / 运行错误）。"""

    def __init__(self, job_id: str, reason: str = "", operator: str = "system"):
        super().__init__(aggregate_id=job_id)
        self.reason = reason
        self.operator = operator


class GenerationJobCancelled(DomainEvent):
    """生成任务被取消。"""

    def __init__(self, job_id: str, operator: str = "system"):
        super().__init__(aggregate_id=job_id)
        self.operator = operator


__all__ = [
    "GenerationJobCreated",
    "GenerationJobStarted",
    "GenerationStepCompleted",
    "GenerationRetried",
    "GenerationJobSucceeded",
    "GenerationJobFailed",
    "GenerationJobCancelled",
]
