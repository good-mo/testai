"""项目应用层输入/输出 DTO。

面向聚合操作接收显式 DTO（而非裸 dict），与 Web 层的 Pydantic 请求体解耦。
此处用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CreateProjectCommand:
    name: str
    description: str = ""
    repo_url: str = ""
    language: str = "python"
    path: str = ""
    organization_id: str = ""
    operator: str = "system"


@dataclass
class UpdateProjectCommand:
    project_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    repo_url: Optional[str] = None
    language: Optional[str] = None
    path: Optional[str] = None
    organization_id: Optional[str] = None
    operator: str = "system"


@dataclass
class ChangeStatusCommand:
    project_id: str
    target_status: str
    operator: str = "system"


@dataclass
class AddMemberCommand:
    project_id: str
    user_id: str = ""
    username: str = ""
    name: str = ""
    email: str = ""
    role: str = "member"
    user_group: str = ""
    operator: str = "system"


@dataclass
class RemoveMemberCommand:
    project_id: str
    user_id: str = ""
    operator: str = "system"


@dataclass
class GetMemberCommand:
    member_id: str


@dataclass
class UpdateMemberCommand:
    member_id: str
    data: dict = field(default_factory=dict)
    operator: str = "system"


@dataclass
class BatchRemoveMembersCommand:
    project_id: str
    user_ids: list = field(default_factory=list)
    operator: str = "system"


@dataclass
class ListQuery:
    search: str = ""
    status: str = ""
    limit: int = 100
    include_deleted: bool = False


# ── 自定义函数（custom_funcs）旁路 DDD 覆盖 ───────────────
@dataclass
class CustomFuncListQuery:
    project_id: str = ""
    keyword: str = ""


@dataclass
class CreateCustomFuncCommand:
    func_id: str
    name: str = ""
    script: str = ""
    func_type: str = "HTTP"
    description: str = ""
    status: str = "DRAFT"
    project_id: str = ""
    tags: Optional[list] = None
    params: str = "[]"
    result: str = ""
    create_user: str = "admin"


@dataclass
class UpdateCustomFuncCommand:
    func_id: str
    updates: dict
    update_user: str = "admin"


@dataclass
class UpdateCustomFuncStatusCommand:
    func_id: str
    status: str


# ── 自定义字段（project_custom_fields）旁路 DDD 覆盖 ──────
@dataclass
class CustomFieldListQuery:
    scope_id: str
    scene: str = ""


@dataclass
class UpsertCustomFieldCommand:
    field_id: str
    body: dict


# ==============================================================================
# 从 models/project.py 迁移
# ==============================================================================

# app/models/project.py
"""项目管理 Pydantic 模型。"""
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("")
    repo_url: str = Field("")
    language: str = Field("python")
    path: str = Field("")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    repo_url: Optional[str] = None
    language: Optional[str] = None
    path: Optional[str] = None
    status: Optional[str] = None


class ProjectScanRequest(BaseModel):
    project_path: str = Field("", description="要扫描的项目目录路径")


class ProjectGenerateRequest(BaseModel):
    project_path: str = Field("", description="要批量生成的项目目录路径")
