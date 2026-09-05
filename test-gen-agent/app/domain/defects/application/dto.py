"""缺陷应用层输入/输出 DTO。

应用层面向"缺陷"操作接收显式 DTO（而非裸 dict），与 Web 层 Pydantic
请求体解耦。此处用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CreateDefectCommand:
    title: str
    description: str = ""
    severity: str = "major"
    status: str = "open"
    file_path: str = ""
    test_case_id: str = ""
    error_snippet: str = ""
    assignee: str = ""
    tags: List[str] = field(default_factory=list)
    operator: str = "system"


@dataclass
class UpdateDefectCommand:
    defect_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    file_path: Optional[str] = None
    test_case_id: Optional[str] = None
    error_snippet: Optional[str] = None
    assignee: Optional[str] = None
    tags: Optional[List[str]] = None
    operator: str = "system"


@dataclass
class ChangeStatusCommand:
    defect_id: str
    target_status: str
    operator: str = "system"


@dataclass
class DefectListQuery:
    status: str = ""
    severity: str = ""
    limit: int = 100
    offset: int = 0


@dataclass
class CreateCommentCommand:
    bug_id: str
    content: str = ""
    parent_id: str = ""
    create_user: str = ""
    reply_user: str = ""
    notifier: str = ""


@dataclass
class UpdateCommentCommand:
    comment_id: str
    content: str


@dataclass
class DeleteCommentCommand:
    comment_id: str


@dataclass
class ListCommentsQuery:
    bug_id: str


@dataclass
class AutoCreateFromResultCommand:
    file_path: str
    test_result: dict
    test_case_id: str = ""


@dataclass
class PermanentDeleteCommand:
    defect_id: str
