"""用例评审应用层输入/输出 DTO。

应用层面向"用例评审"操作接收显式 DTO（而非裸 dict），与 Web 层的
Pydantic 请求体解耦。此处用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CreateReviewCommand:
    """创建评审会话。"""

    name: str
    description: str = ""
    project_id: str = ""
    module_id: str = "root"
    status: str = "UNDERWAY"
    review_pass_rule: str = "SINGLE"
    reviewers: Optional[List[dict]] = None
    tags: Optional[List[str]] = None
    start_time: float = 0
    end_time: float = 0
    operator: str = "admin"
    case_ids: Optional[List[str]] = None  # 可选：创建后立即关联的用例


@dataclass
class UpdateReviewCommand:
    """更新评审基本信息。"""

    review_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    module_id: Optional[str] = None
    project_id: Optional[str] = None
    status: Optional[str] = None
    review_pass_rule: Optional[str] = None
    reviewers: Optional[List[dict]] = None
    tags: Optional[List[str]] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    operator: str = "system"


@dataclass
class DeleteReviewCommand:
    """软删除评审会话。"""

    review_id: str
    operator: str = "system"


@dataclass
class CopyReviewCommand:
    """复制评审会话。"""

    source_id: str
    new_name: str = ""
    operator: str = "system"


@dataclass
class LinkCasesCommand:
    """向评审关联用例。"""

    review_id: str
    case_ids: List[str] = field(default_factory=list)
    operator: str = "system"


@dataclass
class UnlinkCasesCommand:
    """解除评审与用例的关联。"""

    review_id: str
    case_ids: List[str] = field(default_factory=list)
    operator: str = "system"


@dataclass
class UpdateLinkResultCommand:
    """批量更新评审中关联用例的评审结果。"""

    review_id: str
    case_ids: List[str] = field(default_factory=list)
    status: str = "UNDER_REVIEWED"
    reviewer: str = ""
    comment: str = ""
    operator: str = "system"


@dataclass
class ToggleFollowCommand:
    """关注 / 取消关注评审。"""

    review_id: str
    user_id: str


@dataclass
class CaseReviewListQuery:
    """评审列表分页查询。"""

    keyword: str = ""
    project_id: str = ""
    status: str = ""
    limit: int = 500
    offset: int = 0
