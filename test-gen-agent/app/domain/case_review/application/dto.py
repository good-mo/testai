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


# ==============================================================================
# 从 models/case_review.py 迁移
# ==============================================================================

# app/models/case_review.py
"""用例评审（case_review）域 Pydantic 请求体模型。

字段自 `app/routers/case_review.py` 中 `read_body` 实际使用的请求体归纳，
前端 TestPilot 风格驼峰字段与后端蛇形别名并存。所有模型默认
`extra: allow`，避免遗漏新增字段导致 400。
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field

# 评审用例结果状态（与 case_review_service 常量一致）
REVIEW_STATUS_PASS = "PASS"
REVIEW_STATUS_UN_PASS = "UN_PASS"
REVIEW_STATUS_UNDER_REVIEWED = "UNDER_REVIEWED"
REVIEW_STATUS_RE_REVIEWED = "RE_REVIEWED"

# 评审头状态
HEADER_STATUS_UNDERWAY = "UNDERWAY"
HEADER_STATUS_FINISHED = "FINISHED"


class ReviewAssociateBody(BaseModel):
    """评审关联/取消关联用例请求（内嵌 baseAssociateCaseRequest）。"""

    reviewId: str = Field("", description="评审 ID")
    selectIds: List[str] = Field([], description="已选用例 ID（全选时可为空）")
    ids: List[str] = Field([], description="用例 ID（别名）")
    selectedIds: List[str] = Field([], description="已选用例 ID（别名）")
    caseId: str = Field("", description="单用例 ID")
    selectAll: bool = Field(False, description="是否全选")

    def effective_ids(self) -> List[str]:
        for key in ("ids", "selectIds", "selectedIds"):
            val = getattr(self, key)
            if isinstance(val, str):
                val = [val]
            if val:
                return [str(x) for x in val]
        if self.caseId:
            return [self.caseId]
        return []

    model_config = {"extra": "allow"}


class ReviewPageQuery(BaseModel):
    """评审列表分页查询。"""

    keyword: str = Field("", description="搜索关键字")
    projectId: str = Field("", description="项目 ID")
    pageSize: int = Field(10, ge=1, description="每页条数")
    current: int = Field(1, ge=1, description="页码")

    model_config = {"extra": "allow"}


class ReviewCreateBody(BaseModel):
    """新增评审。"""

    name: str = Field("新评审", description="评审名称")
    description: str = Field("", description="描述")
    projectId: str = Field("", description="项目 ID")
    moduleId: str = Field("root", description="模块 ID")
    reviewPassRule: str = Field("SINGLE", description="通过规则")
    reviewers: List[Any] = Field([], description="评审人（userId/用户对象 数组）")
    tags: List[str] = Field([], description="标签")
    startTime: Any = Field(0, description="开始时间（ms）")
    endTime: Any = Field(0, description="结束时间（ms）")
    baseAssociateCaseRequest: Optional[ReviewAssociateBody] = Field(
        None, description="创建后关联用例请求"
    )

    model_config = {"extra": "allow"}


class ReviewEditBody(BaseModel):
    """编辑评审。"""

    id: str = Field("", description="评审 ID")
    caseReviewId: str = Field("", description="评审 ID（别名）")
    name: Optional[str] = Field(None, description="评审名称")
    description: Optional[str] = Field(None, description="描述")
    moduleId: Optional[str] = Field(None, description="模块 ID")
    projectId: Optional[str] = Field(None, description="项目 ID")
    status: Optional[str] = Field(None, description="评审状态")
    reviewPassRule: Optional[str] = Field(None, description="通过规则")
    reviewers: Optional[List[Any]] = Field(None, description="评审人列表")

    @property
    def review_id(self) -> str:
        return self.id or self.caseReviewId

    model_config = {"extra": "allow"}


class ReviewIdBody(BaseModel):
    """按 ID 操作评审（delete/detail/get-ids/tree 等）。"""

    id: str = Field("", description="评审 ID")
    reviewId: str = Field("", description="评审 ID（别名）")
    caseReviewId: str = Field("", description="评审 ID（别名）")

    @property
    def review_id(self) -> str:
        return self.reviewId or self.id or self.caseReviewId

    model_config = {"extra": "allow"}


class ReviewCopyBody(BaseModel):
    """复制评审。"""

    copyId: str = Field("", description="被复制的评审 ID")
    id: str = Field("", description="被复制的评审 ID（别名）")
    name: str = Field("", description="新评审名称")

    @property
    def source_id(self) -> str:
        return self.copyId or self.id

    model_config = {"extra": "allow"}


class ReviewBatchMoveBody(BaseModel):
    """批量移动评审（更新 module_id）。"""

    ids: List[str] = Field([], description="评审 ID 列表")
    moveModuleId: str = Field("", description="目标模块 ID")
    moduleId: str = Field("", description="目标模块 ID（别名）")

    @property
    def target_module_id(self) -> str:
        return self.moveModuleId or self.moduleId or "root"

    model_config = {"extra": "allow"}


class ReviewMovePosBody(BaseModel):
    """评审拖拽排序。"""

    moveId: str = Field("", description="被移动评审 ID")
    pos: int = Field(0, description="目标位置")
    targetId: str = Field("", description="目标评审 ID（用于推算 pos）")

    model_config = {"extra": "allow"}


class ReviewFollowerBody(BaseModel):
    """关注/取消关注评审。"""

    caseReviewId: str = Field("", description="评审 ID")
    reviewId: str = Field("", description="评审 ID（别名）")
    userId: str = Field("", description="用户 ID")

    @property
    def review_id(self) -> str:
        return self.caseReviewId or self.reviewId

    model_config = {"extra": "allow"}


class ReviewDetailPageQuery(BaseModel):
    """评审详情-已关联用例分页。"""

    reviewId: str = Field("", description="评审 ID")
    keyword: str = Field("", description="搜索关键字")
    moduleIds: List[str] = Field([], description="模块 ID 过滤")
    viewStatusFlag: bool = Field(False, description="仅看当前用户评审状态")
    pageSize: int = Field(10, ge=1, description="每页条数")
    current: int = Field(1, ge=1, description="页码")

    model_config = {"extra": "allow"}


class ReviewUserOptionQuery(BaseModel):
    """评审人员列表查询。"""

    projectId: str = Field("", description="项目 ID")
    keyword: str = Field("", description="搜索关键字")

    model_config = {"extra": "allow"}


class ReviewModuleAddBody(BaseModel):
    """新增评审模块。"""

    name: str = Field("新模块", description="模块名称")
    projectId: str = Field("", description="项目 ID")
    parentId: str = Field("root", description="父模块 ID")

    model_config = {"extra": "allow"}


class ReviewModuleUpdateBody(BaseModel):
    """更新评审模块。"""

    id: str = Field("", description="模块 ID")
    name: str = Field("", description="模块名称")

    model_config = {"extra": "allow"}


class ReviewModuleDeleteBody(BaseModel):
    """删除评审模块。"""

    id: str = Field("", description="模块 ID")

    model_config = {"extra": "allow"}


class ReviewModuleMoveBody(BaseModel):
    """移动评审模块。"""

    dragNodeId: str = Field("", description="被拖动模块 ID")
    dropNodeId: str = Field("", description="落点模块 ID")
    dropPosition: Any = Field(0, description="落点位置")

    model_config = {"extra": "allow"}


class ReviewModuleCountBody(BaseModel):
    """模块下评审数量统计。"""

    projectId: str = Field("", description="项目 ID")

    model_config = {"extra": "allow"}


class ReviewCaseStatusBody(BaseModel):
    """批量评审单个用例状态。"""

    status: str = Field(REVIEW_STATUS_UNDER_REVIEWED,
                        description="评审结果：PASS/UN_PASS/UNDER_REVIEWED/RE_REVIEWED")
    reviewer: str = Field("", description="评审人 ID")
    userId: str = Field("", description="评审人 ID（别名，脑图评审用）")
    content: str = Field("", description="评审意见")
    comment: str = Field("", description="评审意见（别名）")

    @property
    def effective_reviewer(self) -> str:
        return self.reviewer or self.userId

    @property
    def effective_comment(self) -> str:
        return self.content or self.comment

    model_config = {"extra": "allow"}


class ReviewDetailBatchReviewBody(BaseModel):
    """评审详情-批量评审用例（继承状态 + 关联/全选字段）。"""

    reviewId: str = Field("", description="评审 ID")
    status: str = Field(REVIEW_STATUS_UNDER_REVIEWED,
                        description="评审结果：PASS/UN_PASS/UNDER_REVIEWED/RE_REVIEWED")
    reviewer: str = Field("", description="评审人 ID")
    userId: str = Field("", description="评审人 ID（别名，脑图评审用）")
    content: str = Field("", description="评审意见")
    comment: str = Field("", description="评审意见（别名）")
    selectIds: List[str] = Field([], description="已选用例 ID")
    ids: List[str] = Field([], description="用例 ID（别名）")
    selectedIds: List[str] = Field([], description="已选用例 ID（别名）")
    caseId: str = Field("", description="单用例 ID")
    selectAll: bool = Field(False, description="是否全选")

    def effective_ids(self) -> List[str]:
        for key in ("selectIds", "ids", "selectedIds"):
            val = getattr(self, key)
            if isinstance(val, str):
                val = [val]
            if val:
                return [str(x) for x in val]
        if self.caseId:
            return [self.caseId]
        return []

    @property
    def effective_reviewer(self) -> str:
        return self.reviewer or self.userId

    @property
    def effective_comment(self) -> str:
        return self.content or self.comment

    model_config = {"extra": "allow"}


class ReviewDetailBatchReviewersBody(BaseModel):
    """评审详情-批量修改评审人。"""

    reviewId: str = Field("", description="评审 ID")
    reviewerId: List[str] = Field([], description="评审人 ID 列表")
    reviewers: List[str] = Field([], description="评审人 ID 列表（别名）")

    @property
    def reviewer_ids(self) -> List[str]:
        return self.reviewerId or self.reviewers or []

    model_config = {"extra": "allow"}


class ReviewDetailTreeBody(ReviewIdBody):
    """评审详情-模块树查询。"""

    pass


__all__ = [
    "REVIEW_STATUS_PASS",
    "REVIEW_STATUS_UN_PASS",
    "REVIEW_STATUS_UNDER_REVIEWED",
    "REVIEW_STATUS_RE_REVIEWED",
    "HEADER_STATUS_UNDERWAY",
    "HEADER_STATUS_FINISHED",
    "ReviewAssociateBody",
    "ReviewPageQuery",
    "ReviewCreateBody",
    "ReviewEditBody",
    "ReviewIdBody",
    "ReviewCopyBody",
    "ReviewBatchMoveBody",
    "ReviewMovePosBody",
    "ReviewFollowerBody",
    "ReviewDetailPageQuery",
    "ReviewUserOptionQuery",
    "ReviewModuleAddBody",
    "ReviewModuleUpdateBody",
    "ReviewModuleDeleteBody",
    "ReviewModuleMoveBody",
    "ReviewModuleCountBody",
    "ReviewCaseStatusBody",
    "ReviewDetailBatchReviewBody",
    "ReviewDetailBatchReviewersBody",
    "ReviewDetailTreeBody",
]
