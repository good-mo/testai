"""应用层输入/输出 DTO。

应用层面向"用例"操作接收显式 DTO（而非裸 dict），与 Web 层的
Pydantic 请求体解耦。此处用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CreateCaseCommand:
    title: str
    case_id: str = ""
    status: str = "draft"
    description: str = ""
    source_code: str = ""
    test_code: str = ""
    file_path: str = ""
    tags: List[str] = field(default_factory=list)
    priority: str = "P2"
    requirement_ref: str = ""
    test_type: str = "functional"
    structured_cases: Optional[list] = None
    metadata: Optional[dict] = None
    operator: str = "system"


@dataclass
class UpdateCaseCommand:
    case_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    source_code: Optional[str] = None
    test_code: Optional[str] = None
    file_path: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[str] = None
    test_type: Optional[str] = None
    requirement_ref: Optional[str] = None
    structured_cases: Optional[list] = None
    metadata: Optional[dict] = None
    status: Optional[str] = None
    operator: str = "system"


@dataclass
class ChangeStatusCommand:
    case_id: str
    target_status: str
    operator: str = "system"


@dataclass
class ReviewCommand:
    case_id: str
    outcome: str
    reviewer: str = ""
    comment: str = ""
    operator: str = "system"


@dataclass
class DeleteCaseCommand:
    case_id: str
    operator: str = "system"
    reason: str = ""


@dataclass
class RestoreCaseCommand:
    case_id: str
    operator: str = "system"


@dataclass
class ListQuery:
    status: str = ""
    priority: str = ""
    tag: str = ""
    search: str = ""
    test_type: str = ""
    module_id: str = ""
    limit: int = 100
    offset: int = 0
