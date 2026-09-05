# app/models/other_compat.py
"""other（other_compat.py）域请求体模型建档。

对应 `app/routers/other_compat.py` 中手写 read_body 解析的兼容端点。
该路由是「跨域杂项」：分享 /api/doc/share/*、LDAP 登录 /ldap/login、
个人模型 /personal/model/*、操作日志 /operation/log/list、用例评审
回放 /review/functional/case/* 等，各 body 独立建档。

分享域统一建档 `Share*Body`；SSO callback（/sso/callback/*）仅为
GET 占位（POST 处理器只消费体、不解析字段），故无需建档、直接移除
冗余 read_body。

全部模型保持与旧 read_body 归一化一致的宽松语义（空体 / 裸标量 /
数组不抛 422），接入后行为零回归。
"""

from typing import Any

from pydantic import BaseModel, Field, model_validator


def _first_nonempty(*values: Any, default: Any = "") -> Any:
    """返回首个非空值，全部为空则取 default。"""
    for v in values:
        if v is not None and v != "":
            return v
    return default


class _LenientRequest(BaseModel):
    """历史兼容：容忍裸字符串 / 数组 / 空请求体，语义与旧 read_body 一致。

    旧路由用 read_body() 会把裸字符串 `"x"` 归一化成 `{"id": "x"}`、
    数组归一化成 `{"ids": [...]}`、空体归一化成 `{}`。改 Pydantic 模型后
    若不处理，FastAPI 会对裸标量判 422，故把同一段归一化上移到模型层
    （等价空体 / 无效体返回 200 的既有契约）。
    """

    model_config = {"extra": "allow", "populate_by_name": True}

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


def _int(val: Any, default: int) -> int:
    """宽松转 int，失败回落 default。"""
    try:
        return int(val) if val is not None and val != "" else default
    except (TypeError, ValueError):
        return default


class _LenientPageBody(_LenientRequest):
    """通用宽松分页基类：current / pageSize 兼容驼峰与整型字符串。"""

    current: Any = Field(None, description="当前页")
    pageSize: Any = Field(None, description="每页条数")

    @property
    def effective_current(self) -> int:
        c = _int(self.current, 1)
        return c if c >= 1 else 1

    @property
    def effective_page_size(self) -> int:
        p = _int(self.pageSize, 10)
        return p if p >= 1 else 10


# ── 分享域 /api/doc/share/* ─────────────────────────────────
class ShareModuleTreeBody(_LenientRequest):
    """分享模块树（shareId + projectId）。"""

    shareId: Any = Field(None, description="分享 ID")
    projectId: Any = Field(None, description="项目 ID")

    @property
    def effective_share_id(self) -> str:
        return str(_first_nonempty(self.shareId, default=""))

    @property
    def effective_project_id(self) -> str:
        return str(_first_nonempty(self.projectId, default=""))


class ShareDetailBody(_LenientRequest):
    """查看分享链接：id 为主、shareId 兜底。"""

    id: Any = Field(None, description="分享 ID（主）")
    shareId: Any = Field(None, description="分享 ID（别名）")

    @property
    def effective_share_id(self) -> str:
        return str(_first_nonempty(self.id, self.shareId, default=""))


class SharePageBody(_LenientPageBody):
    """文档分享分页列表。"""


# ── 操作日志 /operation/log/list ────────────────────────────
class OperationLogListBody(_LenientPageBody):
    """系统操作日志列表过滤（GET/POST 共用）。"""

    operUser: Any = Field(None, description="操作人")
    startTime: Any = Field(None, description="开始时间（毫秒）")
    endTime: Any = Field(None, description="结束时间（毫秒）")
    projectIds: Any = Field(None, description="项目 ID 列表")
    organizationIds: Any = Field(None, description="组织 ID 列表")
    type: Any = Field(None, description="日志类型")
    module: Any = Field(None, description="模块")
    content: Any = Field(None, description="内容关键字")
    level: Any = Field(None, description="级别")
    keyword: Any = Field(None, description="关键字")

    @property
    def effective_oper_user(self) -> str:
        return str(self.operUser or "").strip()

    @property
    def effective_log_type(self) -> str:
        return str(self.type or "").strip()

    @property
    def effective_module(self) -> str:
        return str(self.module or "").strip()

    @property
    def effective_content(self) -> str:
        return str(self.content or "").strip()

    @property
    def effective_keyword(self) -> str:
        return str(self.keyword or "").strip()

    @property
    def effective_level(self) -> str:
        return str(self.level or "").strip() or "SYSTEM"

    def effective_project_ids(self) -> list:
        ids = self.projectIds if self.projectIds is not None else []
        if isinstance(ids, str):
            ids = [ids]
        return [str(x) for x in ids] if isinstance(ids, (list, tuple)) else []

    def effective_organization_ids(self) -> list:
        ids = self.organizationIds if self.organizationIds is not None else []
        if isinstance(ids, str):
            ids = [ids]
        return [str(x) for x in ids] if isinstance(ids, (list, tuple)) else []


# ── LDAP 登录 /ldap/login ────────────────────────────────────
class LdapLoginBody(_LenientRequest):
    """LDAP 登录（取 username）。"""

    username: Any = Field(None, description="登录用户名")

    @property
    def effective_username(self) -> str:
        return str(self.username or "")


# ── 个人模型 /personal/model/* ──────────────────────────────
class PersonalModelIdBody(_LenientRequest):
    """个人模型删除（body 携带 id 时真实删除）。"""

    id: Any = Field(None, description="模型 ID")

    @property
    def effective_id(self) -> str:
        return str(self.id or "")


class PersonalModelPageBody(_LenientPageBody):
    """个人模型源集合分页：providerName/keyword 过滤。"""

    providerName: Any = Field(None, description="供应商")
    keyword: Any = Field(None, description="搜索关键字")

    @property
    def effective_provider_name(self) -> str:
        return str(self.providerName or "")

    @property
    def effective_keyword(self) -> str:
        return str(self.keyword or "")


# ── 用例评审回放 /review/functional/case/* ──────────────────
class ReviewCaseHistoryBody(_LenientRequest):
    """评审详情-获取用例评审历史：reviewId 为主、id 兜底。"""

    reviewId: Any = Field(None, description="评审 ID（主）")
    id: Any = Field(None, description="评审 ID（别名）")
    caseId: Any = Field(None, description="用例 ID")

    @property
    def effective_review_id(self) -> str:
        return str(_first_nonempty(self.reviewId, self.id, default=""))

    @property
    def effective_case_id(self) -> str:
        return str(self.caseId or "")


class ReviewCaseSaveBody(_LenientRequest):
    """评审详情-提交评审结果。

    body: {caseId, reviewId, status, notifier, content, ...}
    status 为前端 StartReviewStatus（PASS/UN_PASS/UNDER_REVIEWED/RE_REVIEWED）。
    """

    caseId: Any = Field(None, description="用例 ID")
    reviewId: Any = Field(None, description="评审 ID")
    status: Any = Field(None, description="评审状态（前端 StartReviewStatus）")
    notifier: Any = Field(None, description="评审人（回写）")
    content: Any = Field(None, description="评审意见")

    @property
    def effective_case_id(self) -> str:
        return str(self.caseId or "")

    @property
    def effective_review_id(self) -> str:
        return str(self.reviewId or "")

    @property
    def effective_status(self) -> str:
        return str(self.status or "")

    @property
    def effective_notifier(self) -> str:
        return str(self.notifier or "")

    @property
    def effective_content(self) -> str:
        return str(self.content or "")


__all__ = [
    "ShareModuleTreeBody",
    "ShareDetailBody",
    "SharePageBody",
    "OperationLogListBody",
    "LdapLoginBody",
    "PersonalModelIdBody",
    "PersonalModelPageBody",
    "ReviewCaseHistoryBody",
    "ReviewCaseSaveBody",
]
