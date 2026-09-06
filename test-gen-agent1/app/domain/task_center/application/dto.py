"""任务中心应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class StopTasksCommand:
    ids: List[str] = field(default_factory=list)

@dataclass
class DeleteTasksCommand:
    ids: List[str] = field(default_factory=list)

@dataclass
class RerunTaskCommand:
    task_id: str = ""

@dataclass
class ListTasksCommand:
    pass

@dataclass
class SubmitTaskCommand:
    """提交命名执行任务到 legacy manager 队列的协调命令。"""
    name: str = ""
    payload: dict = field(default_factory=dict)

@dataclass
class GetTaskCommand:
    """按 id 查询执行任务详情的协调命令（原始 dict 形态）。"""
    task_id: str = ""

@dataclass
class ListRawTasksCommand:
    """列出最近执行任务的协调命令（原始摘要，不做展示态归一）。"""
    limit: int = 50

@dataclass
class SwitchSchedulesCommand:
    ids: List[str] = field(default_factory=list)

@dataclass
class EnableSchedulesCommand:
    ids: List[str] = field(default_factory=list)
    enable: bool = True

@dataclass
class DeleteSchedulesCommand:
    ids: List[str] = field(default_factory=list)

@dataclass
class UpdateCronCommand:
    ids: List[str] = field(default_factory=list)
    cron: str = ""

__all__ = ["StopTasksCommand", "DeleteTasksCommand", "RerunTaskCommand",
           "ListTasksCommand", "SubmitTaskCommand", "GetTaskCommand",
           "ListRawTasksCommand", "SwitchSchedulesCommand", "EnableSchedulesCommand",
           "DeleteSchedulesCommand", "UpdateCronCommand"]
