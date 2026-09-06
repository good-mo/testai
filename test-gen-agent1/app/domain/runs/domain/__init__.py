"""任务运行领域层（domain layer）。

仅表达任务生命周期业务概念与规则（Task 聚合 + TaskStatus 状态机），
不依赖 FastAPI / sqlite / 具体存储实现。
"""
from app.domain.runs.domain.entities.task import Task
from app.domain.runs.domain.repository import TaskRepository
from app.domain.runs.domain.value_objects.task_status import (
    TaskStatus,
    TaskStatusEnum,
)

__all__ = ["Task", "TaskRepository", "TaskStatus", "TaskStatusEnum"]
