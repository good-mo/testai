"""导出任务应用层 DTO。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RegisterTaskCommand:
    file_id: str = ""
    task_id: str = ""
    path: str = ""
    filename: str = ""
    count: int = 0
    is_successful: bool = True

@dataclass
class GetTaskCommand:
    file_id: str = ""

@dataclass
class RemoveTaskCommand:
    file_id: str = ""

__all__ = ["RegisterTaskCommand", "GetTaskCommand", "RemoveTaskCommand"]
