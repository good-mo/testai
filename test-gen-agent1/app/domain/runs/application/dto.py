"""任务运行应用层输入/输出 DTO。

面向聚合操作接收显式 DTO（而非裸 dict），与 Web 层的 Pydantic
请求体解耦。此处用 dataclass 表达简单命令，保持零框架依赖。

包含任务中心（Task）与运行记录 / 报告（RunRecord）两套命令 DTO。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


# ══════════════════════════════════════════════════════════
# 任务中心（Task）
# ══════════════════════════════════════════════════════════
@dataclass
class EnqueueTaskCommand:
    coro_name: str = ""
    args: List[Any] = field(default_factory=list)
    handler_name: str = ""
    handler_args: List[Any] = field(default_factory=list)
    handler_kwargs: dict = field(default_factory=dict)
    restartable: bool = False
    status: str = "pending"
    operator: str = "system"


@dataclass
class CompleteTaskCommand:
    task_id: str
    status: str            # success / failed / cancelled
    result: Any = None
    error: str = ""
    operator: str = "system"


@dataclass
class StartTaskCommand:
    task_id: str
    worker: str = ""
    operator: str = "system"


@dataclass
class TaskListQuery:
    limit: int = 50
    operator: str = "system"


# ══════════════════════════════════════════════════════════
# 运行记录 / 报告（RunRecord）
# ══════════════════════════════════════════════════════════
@dataclass
class SaveRunRecordCommand:
    """保存一次运行/报告的完整快照。"""

    file_path: str = ""
    source_code: str = ""
    generated_tests: str = ""
    test_result: Optional[dict] = None
    coverage_report: Optional[dict] = None
    performance_report: Optional[dict] = None
    retry_count: int = 0
    saved_to: str = ""
    error: str = ""
    source: str = "single"
    metadata: Optional[dict] = None
    operator: str = "system"


@dataclass
class UpdateRunRecordCommand:
    """原位更新运行记录（保留主键）。"""

    record_id: str
    file_path: Optional[str] = None
    source_code: Optional[str] = None
    generated_tests: Optional[str] = None
    test_result: Optional[dict] = None
    coverage_report: Optional[dict] = None
    performance_report: Optional[dict] = None
    retry_count: Optional[int] = None
    saved_to: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None
    operator: str = "system"


@dataclass
class RenameRunRecordCommand:
    """重命名运行记录（file_path 充当报告名）。"""

    record_id: str
    new_name: str
    operator: str = "system"


@dataclass
class RunRecordListQuery:
    """运行记录列表查询。"""

    file_path: str = ""
    source: str = ""
    passed: Optional[bool] = None
    search: str = ""
    limit: int = 50
    offset: int = 0


@dataclass
class ClearRunRecordsCommand:
    """清空运行记录（可选按来源）。"""

    source: str = ""
    operator: str = "system"


__all__ = [
    # Task
    "EnqueueTaskCommand", "CompleteTaskCommand", "StartTaskCommand",
    "TaskListQuery",
    # RunRecord
    "SaveRunRecordCommand", "UpdateRunRecordCommand", "RenameRunRecordCommand",
    "RunRecordListQuery", "ClearRunRecordsCommand",
]
