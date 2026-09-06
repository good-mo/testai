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


# ==============================================================================
# 从 models/case.py 迁移
# ==============================================================================

# app/models/case.py
"""用例管理 Pydantic 模型。"""
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    title: str = Field("", description="用例标题", max_length=200)
    description: str = Field("", description="用例描述")
    source_code: str = Field("", description="源码")
    test_code: str = Field("", description="测试代码")
    file_path: str = Field("", description="文件路径")
    tags: List[str] = Field([], description="标签")
    status: str = Field("draft", description="状态")
    priority: str = Field("P2", description="优先级")
    requirement_ref: str = Field("", description="需求引用")
    test_type: str = Field("functional", description="测试类型")
    structured_cases: Any = Field([], description="结构化用例")


class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, description="用例标题")
    description: Optional[str] = None
    source_code: Optional[str] = None
    test_code: Optional[str] = None
    file_path: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = Field(None, description="状态")
    priority: Optional[str] = Field(None, description="优先级")
    requirement_ref: Optional[str] = None
    test_type: Optional[str] = None
    structured_cases: Optional[Any] = None


class CaseRelationAdd(BaseModel):
    related_case_id: str = Field(..., description="关联用例ID")
    relation_type: str = Field("related", description="关联类型")


class CaseDependencyAdd(BaseModel):
    depends_on: str = Field(..., description="依赖用例ID")
    dep_type: str = Field("before", description="依赖类型: before/after")
    description: str = Field("", description="依赖描述")


class CaseReviewSubmit(BaseModel):
    reviewer: str = Field("", description="评审人")
    comment: str = Field("", description="评审意见")


class CaseRequirementAdd(BaseModel):
    requirement_id: str = Field("", description="需求ID")
    requirement_type: str = Field("jira", description="需求类型")
    requirement_title: str = Field("", description="需求标题")
    requirement_url: str = Field("", description="需求链接")


class CaseRollback(BaseModel):
    version: int = Field(0, ge=0, description="要回滚到的版本号")
    operator: str = Field("", description="操作人")


class CaseTrashBody(BaseModel):
    """软删除请求体（可选字段）。"""
    deleted_by: str = Field("", description="删除人")
    reason: str = Field("", description="删除原因")


class CaseRestoreBody(BaseModel):
    operator: str = Field("", description="恢复人")


class CaseImportBody(BaseModel):
    format: str = Field("excel", description="导入格式: excel/mindmap")
    content: str = Field("", description="导入内容")
    operator: str = Field("", description="操作人")


class CaseFunctionalPageBody(BaseModel):
    """功能用例分页查询。"""
    keyword: str = Field("", description="搜索关键字")
    pageSize: int = Field(10, ge=1, description="每页条数")
    current: int = Field(1, ge=1, description="页码")
    page: int = Field(1, ge=1, description="页码（别名）")
    page_size: int = Field(10, ge=1, description="每页条数（别名）")
    moduleIds: List[str] = Field([], description="模块 ID 列表（为空表示全部模块）")
    module_id: Optional[str] = Field(None, description="单个模块 ID（别名）")
    projectId: str = Field("", description="项目 ID")
    filter: dict = Field({}, description="筛选条件")
    combineSearch: dict = Field({}, description="高级筛选条件")
    sort: dict = Field({}, description="排序参数")
    excludeIds: list = Field([], description="排除 ID")
    selectIds: list = Field([], description="已选 ID")
    selectAll: bool = Field(False, description="是否全选")
    model_config = {"extra": "allow"}

    def get_page(self) -> int:
        return self.page if self.page > 1 else self.current

    def get_page_size(self) -> int:
        return self.page_size if self.page_size != 10 else self.pageSize

    def effective_module_ids(self) -> List[str]:
        if self.moduleIds:
            return self.moduleIds
        if self.module_id:
            return [self.module_id]
        return []


class CaseFunctionalIdBody(BaseModel):
    """功能用例单 ID 操作。"""
    id: str = Field("", description="用例 ID")

    model_config = {"extra": "allow"}


class CaseFunctionalIdsBody(BaseModel):
    """功能用例批量操作。"""
    ids: List[str] = Field([], description="用例 ID 列表")
    selectIds: List[str] = Field([], description="已选 ID（别名）")
    selectAll: bool = Field(False, description="是否全选")

    def effective_ids(self) -> List[str]:
        for key in ("ids", "selectIds"):
            val = getattr(self, key)
            if isinstance(val, str):
                val = [val]
            if val:
                return val
        return []

    model_config = {"extra": "allow"}


# ════════════════════════════════════════════════════════════
# 功能用例适配路由（app/routers/functional_cases.py / _extra.py）
# 请求体为 read_body 读取，字段前端 TestPilot 驼峰为主、多别名并存。
# 统一经模型 `model_validate` 归一，收敛路由内联 .get() 解析。
# ════════════════════════════════════════════════════════════

class _FunctionalLenientRequest(BaseModel):
    """功能用例适配路由请求体基类：默认忽略未知字段，避免 400。"""

    model_config = {"extra": "allow"}


class FunctionalCaseRefBody(_FunctionalLenientRequest):
    """功能用例单引用操作（删除 GET / 回收站恢复、删除）。

    兼容字段：id / caseId / functionalCaseId，优先级 id > caseId >
    functionalCaseId（对齐旧内联解析 id→caseId）。
    """

    id: str = Field("", description="用例 ID")
    caseId: str = Field("", description="用例 ID（别名）")
    functionalCaseId: str = Field("", description="用例 ID（别名）")

    @property
    def effective_id(self) -> str:
        return self.id or self.caseId or self.functionalCaseId

    model_config = {"extra": "allow"}


class FunctionalCaseFollowBody(_FunctionalLenientRequest):
    """功能用例关注/取消关注请求体。

    兼容 body 与 query 取参：functionalCaseId/caseId/id + userId/user_id。
    """

    functionalCaseId: str = Field("", description="功能用例 ID")
    caseId: str = Field("", description="功能用例 ID（别名）")
    id: str = Field("", description="功能用例 ID（别名）")
    userId: str = Field("", description="操作用户 ID")
    user_id: str = Field("", description="操作用户 ID（别名）")

    @property
    def effective_case_id(self) -> str:
        return self.functionalCaseId or self.caseId or self.id

    @property
    def effective_user_id(self) -> str:
        # 对齐旧内联：userId 优先；缺省时回退 user_id，最终兜底 admin
        if self.userId:
            return self.userId
        if self.user_id:
            return self.user_id
        return "admin"

    model_config = {"extra": "allow"}


class FunctionalModuleBody(_FunctionalLenientRequest):
    """功能用例模块新增/更新请求体。

    新增：name/parentId/projectId；更新：id/name。scope 固定 functional。
    """

    id: str = Field("", description="模块 ID（更新时必填）")
    name: str = Field("", description="模块名称")
    parentId: str = Field("root", description="父模块 ID")
    projectId: str = Field("", description="所属项目 ID")
    module_id: str = Field("", description="模块 ID（别名）")

    @property
    def effective_module_id(self) -> str:
        return self.id or self.module_id

    model_config = {"extra": "allow"}


class FunctionalModuleDeleteBody(_FunctionalLenientRequest):
    """功能用例模块删除请求体。"""

    id: str = Field("", description="模块 ID")
    module_id: str = Field("", description="模块 ID（别名）")

    @property
    def effective_module_id(self) -> str:
        return self.id or self.module_id

    model_config = {"extra": "allow"}


class FunctionalTrashPageBody(_FunctionalLenientRequest):
    """功能用例回收站分页查询请求体（keyword/pageSize/current）。"""

    keyword: str = Field("", description="搜索关键字")
    pageSize: int = Field(10, description="每页条数")
    current: int = Field(1, description="页码")

    model_config = {"extra": "allow"}


class FunctionalTrashBatchBody(_FunctionalLenientRequest):
    """功能用例回收站批量操作请求体（批量恢复/批量删除）。

    兼容 selectIds / ids / id / selectedIds，单值自动转列表。
    """

    ids: Any = Field(None, description="用例 ID 列表")
    selectIds: Any = Field(None, description="已选用例 ID（别名）")
    selectedIds: Any = Field(None, description="已选用例 ID（别名）")
    id: Any = Field(None, description="单个用例 ID")

    def effective_ids(self) -> List[str]:
        # 对齐旧内联优先级：selectIds > ids > id > selectedIds
        for key in ("selectIds", "ids", "id", "selectedIds"):
            val = getattr(self, key)
            if val is None:
                continue
            if isinstance(val, str):
                val = [val]
            if isinstance(val, list):
                return [str(x) for x in val if x]
            if val:
                return [str(val)]
        return []

    model_config = {"extra": "allow"}
