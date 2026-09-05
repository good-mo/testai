# app/models/defect.py
"""缺陷管理 Pydantic 请求体模型。

第一部分：modern 四层路由 `app/routers/defects.py` 使用的模型
（DefectCreate / DefectUpdate / DefectPageQuery / DefectIdsBody）。

第二部分：MeterSphere 兼容路由 `app/routers/defects_compat*.py`
前端 `/bug/*` 实际使用到的请求体模型（Bug* 前缀），
字段自路由中 `read_body`/`read_form_or_json` 实际读取项归纳，
TestPilot 风格驼峰字段与旧下划线别名并存。所有模型默认
`extra: allow`，避免遗漏新增字段导致 400。
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class _LenientRequest(BaseModel):
    """历史兼容：容忍前端经 axios 拦截器发送的裸标量请求体。

    旧路由用 read_body() 读取请求体时会把裸字符串 `"x"` 归一化成
    `{"id": "x"}`、数组归一化成 `{"ids": [...]}`、空体归一化成 `{}`
    （见 app/core/response.py）。改用 Pydantic 请求体模型后若不处理，
    FastAPI 会把裸标量判 422。故把同一段归一化上移到模型层。
    """

    @model_validator(mode="before")
    @classmethod
    def _lenient_coerce(cls, raw):
        if isinstance(raw, str):
            return {"id": raw}
        if isinstance(raw, list):
            return {"ids": raw}
        if raw is None:
            return {}
        return raw


class DefectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field("")
    severity: str = Field("major", pattern="^(blocker|critical|major|minor)$")
    status: str = Field("open", pattern="^(open|in_progress|fixed|closed|wont_fix)$")
    file_path: str = Field("")
    test_case_id: str = Field("")
    error_snippet: str = Field("")
    assignee: str = Field("")


class DefectUpdate(BaseModel):
    # 注意：status/severity 不在 Pydantic 层做枚举 pattern 约束，
    # 交由业务层(app.services.defect_service -> app.defects.tracker)校验并返回 400，
    # 与 cases 域及历史缺陷接口语义保持一致（非法业务值一律 400）。
    title: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    file_path: Optional[str] = None
    test_case_id: Optional[str] = None
    error_snippet: Optional[str] = None
    assignee: Optional[str] = None


class DefectPageQuery(BaseModel):
    keyword: str = Field("")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    status: Optional[str] = None
    severity: Optional[str] = None


class DefectIdsBody(BaseModel):
    """批量操作缺陷 ID 列表。"""
    ids: List[str] = Field([], description="缺陷 ID 列表")


# ═══════════════════════════════════════════════════════════
# 兼容路由 /bug/* 请求体模型
# ═══════════════════════════════════════════════════════════

class BugIdBody(_LenientRequest):
    """按缺陷 ID 操作（trash/delete/recover/follow/unfollow 等）。

    兼容 body 三种主键别名：id / bugId / bug_id。
    """

    id: str = Field("", description="缺陷 ID")
    bug_id: str = Field("", description="缺陷 ID（别名）")
    bugId: str = Field("", description="缺陷 ID（别名）")

    @property
    def effective_id(self) -> str:
        return self.id or self.bug_id or self.bugId

    model_config = {"extra": "allow"}


class BugPageQuery(_LenientRequest):
    """缺陷分页列表查询（/bug/page、/bug/trash/page）。

    pageSize/current 为前端分页参数（驼峰）；旧 read_body 侧还支持
    page_size/page。condition.filter / filter 用于简单列筛选，sort 用于排序。
    """

    keyword: str = Field("", description="搜索关键字")
    pageSize: int = Field(10, description="每页条数")
    current: int = Field(1, description="页码")
    page_size: int = Field(0, description="每页条数（别名，>0 时优先）")
    page: int = Field(0, description="页码（别名，>0 时优先）")
    condition: Optional[Dict[str, Any]] = Field(None, description="筛选条件容器")
    filter: Optional[Dict[str, Any]] = Field(None, description="简单筛选 {field: value}")
    sort: Optional[Dict[str, Any]] = Field(None, description="排序 {field: 'ascend'|'descend'}")

    @property
    def effective_page_size(self) -> int:
        if getattr(self, "page_size", 0) and self.page_size > 0:
            return self.page_size
        return self.pageSize or 10

    @property
    def effective_current(self) -> int:
        if getattr(self, "page", 0) and self.page > 0:
            return self.page
        return self.current or 1

    @property
    def effective_filter(self) -> dict:
        if self.condition and self.condition.get("filter"):
            return self.condition["filter"]
        return self.filter or {}

    model_config = {"extra": "allow"}


class BugBatchIdsBody(_LenientRequest):
    """批量操作缺陷（batch-delete / batch-recover / batch-delete-trash）。

    兼容前端 selectIds/selectAll/excludeIds 与旧式 ids/id。
    """

    selectAll: bool = Field(False, description="是否全选")
    selectIds: List[Any] = Field([], description="已选 ID（全选时可为空）")
    select_ids: List[Any] = Field([], description="已选 ID（下划线别名）")
    excludeIds: List[Any] = Field([], description="排除 ID（全选时）")
    exclude_ids: List[Any] = Field([], description="排除 ID（下划线别名）")
    ids: List[Any] = Field([], description="缺陷 ID（旧式）")
    id: Any = Field(None, description="单个缺陷 ID（旧式，字符串归一）")

    @property
    def select_all(self) -> bool:
        return self.selectAll

    @property
    def selected_ids(self) -> List[str]:
        for key in ("selectIds", "select_ids"):
            val = getattr(self, key) or []
            if isinstance(val, str):
                val = [val]
            return [str(x) for x in val]
        return []

    @property
    def excluded_ids(self) -> List[str]:
        for key in ("excludeIds", "exclude_ids"):
            val = getattr(self, key) or []
            if isinstance(val, str):
                val = [val]
            return [str(x) for x in val]
        return []

    @property
    def legacy_ids(self) -> List[str]:
        """旧式 ids / id（用于非全选的直接指定）。"""
        ids = self.ids or []
        if isinstance(ids, str):
            ids = [ids]
        res = [str(x) for x in ids]
        if self.id is not None and not res:
            res = [str(self.id)]
        return res

    model_config = {"extra": "allow"}


class BugCommentAddBody(_LenientRequest):
    """新增缺陷评论（/bug/comment/add）。"""

    bugId: str = Field("", description="缺陷 ID")
    bug_id: str = Field("", description="缺陷 ID（别名）")
    content: str = Field("", description="评论内容")
    parentId: str = Field("", description="父评论 ID（回复）")
    parent_id: str = Field("", description="父评论 ID（下划线别名）")
    replyUser: str = Field("", description="被回复人 ID")
    notifier: str = Field("", description="通知人 ID")

    @property
    def effective_bug_id(self) -> str:
        return self.bugId or self.bug_id

    @property
    def effective_parent_id(self) -> str:
        return self.parentId or self.parent_id

    model_config = {"extra": "allow"}


class BugCommentUpdateBody(_LenientRequest):
    """更新缺陷评论（/bug/comment/update）。"""

    id: str = Field("", description="评论 ID")
    commentId: str = Field("", description="评论 ID（别名）")
    content: str = Field("", description="新评论内容")

    @property
    def effective_comment_id(self) -> str:
        return self.id or self.commentId

    model_config = {"extra": "allow"}


class BugBatchUpdateBody(_LenientRequest):
    """批量更新缺陷（/bug/batch-update）。

    前端批量编辑提交：{ selectIds/selectAll/excludeIds, projectId,
    [attribute]: value|inputValue, append, clear }，其中 attribute 为
    tags 或系统字段(severity/status/assignee)对应的自定义字段 fieldId。
    """

    selectAll: bool = Field(False, description="是否全选")
    selectIds: List[Any] = Field([], description="已选 ID")
    select_ids: List[Any] = Field([], description="已选 ID（下划线别名）")
    excludeIds: List[Any] = Field([], description="排除 ID")
    exclude_ids: List[Any] = Field([], description="排除 ID（下划线别名）")
    ids: List[Any] = Field([], description="旧式 ID 列表")
    id: Any = Field(None, description="旧式单个 ID")
    attribute: str = Field("", description="要批量设置的字段/自定义字段 fieldId")
    field: str = Field("", description="要批量设置的字段（别名）")
    value: Any = Field(None, description="字段值")
    inputValue: Any = Field(None, description="字段值（别名）")
    append: bool = Field(False, description="tags 追加模式")
    clear: bool = Field(False, description="tags 清空模式")
    projectId: str = Field("", description="项目 ID")
    project_id: str = Field("", description="项目 ID（下划线别名）")

    @property
    def select_all(self) -> bool:
        return self.selectAll

    @property
    def selected_ids(self) -> List[str]:
        for key in ("selectIds", "select_ids"):
            val = getattr(self, key) or []
            if isinstance(val, str):
                val = [val]
            return [str(x) for x in val]
        return []

    @property
    def excluded_ids(self) -> List[str]:
        for key in ("excludeIds", "exclude_ids"):
            val = getattr(self, key) or []
            if isinstance(val, str):
                val = [val]
            return [str(x) for x in val]
        return []

    @property
    def legacy_ids(self) -> List[str]:
        ids = self.ids or []
        if isinstance(ids, str):
            ids = [ids]
        res = [str(x) for x in ids]
        if self.id is not None and not res:
            res = [str(self.id)]
        return res

    @property
    def effective_attribute(self) -> str:
        return self.attribute or self.field

    @property
    def effective_value(self) -> Any:
        return self.value if self.value is not None else self.inputValue

    model_config = {"extra": "allow"}


__all__ = [
    "DefectCreate",
    "DefectUpdate",
    "DefectPageQuery",
    "DefectIdsBody",
    "BugIdBody",
    "BugPageQuery",
    "BugBatchIdsBody",
    "BugCommentAddBody",
    "BugCommentUpdateBody",
    "BugBatchUpdateBody",
]
