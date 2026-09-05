# app/test_plan/router_system.py
"""系统设置 API 路由。"""

import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.response import ok

system_router = APIRouter(tags=["system"])


class ProjectAddBody(BaseModel):
    """新建项目（系统设置页）。"""
    name: str = Field("新项目", description="项目名称")
    description: str = Field("", description="描述")
    language: str = Field("python", description="语言")
    organizationId: str = Field("", description="组织 ID")


class OrganizationAddBody(BaseModel):
    """新建组织（系统设置页）。"""
    name: str = Field("新组织", description="组织名称")
    description: str = Field("", description="描述")
    userIds: Any = Field([], description="初始管理员用户 ID 列表")


# ── 用户组管理 ────────────────────────────────────────
@system_router.get("/system/user-group/list")
def user_group_list():
    """获取用户组列表。"""
    return ok([
        {
            "id": "admin",
            "name": "管理员",
            "description": "系统管理员",
            "scope": "SYSTEM",
            "type": "BUILT_IN",
        },
        {
            "id": "user",
            "name": "普通用户",
            "description": "普通用户",
            "scope": "SYSTEM",
            "type": "BUILT_IN",
        },
    ])


# ── 模板管理 ──────────────────────────────────────────
@system_router.get("/template/list/{project_id}/{type}")
def template_list(project_id: str, type: str):
    """获取模板列表。"""
    return ok([
        {
            "id": "default",
            "name": "默认模板",
            "type": type,
            "enable": True,
            "projectId": project_id,
        }
    ])


@system_router.get("/template/option/{project_id}/{type}")
def template_option(project_id: str, type: str):
    """获取模板选项。"""
    return ok([
        {"id": "default", "name": "默认模板"}
    ])


# ── 资源池管理 ────────────────────────────────────────
@system_router.get("/resource/pool/list")
def resource_pool_list():
    """获取资源池列表。"""
    return ok([])


# ── 插件管理 ─────────────────────────────────────────
@system_router.get("/system/plugin/list")
def plugin_list():
    """获取插件列表。"""
    return ok([])


# ── 操作日志 ──────────────────────────────────────────
@system_router.get("/system/operation-log/page")
def operation_log_page():
    """获取操作日志。"""
    return ok({
        "list": [],
        "total": 0,
    })


# ── 项目管理 ──────────────────────────────────────────
@system_router.post("/system/project/add")
def system_project_add(payload: ProjectAddBody):
    """添加项目。"""
    from app.services.project_service import project_service
    project = project_service.create({
        "name": payload.name,
        "description": payload.description,
        "language": payload.language,
    })
    return ok({
        "id": project.get("id", ""),
        "name": project.get("name", ""),
        "description": project.get("description", ""),
        "organizationId": payload.organizationId,
        "enable": True,
        "createTime": int((project.get("created_at") or time.time()) * 1000),
    })


@system_router.get("/system/project/list")
def system_project_list():
    """获取项目列表。"""
    return ok([])


# ── 组织管理 ──────────────────────────────────────────
@system_router.get("/system/organization/list")
def system_organization_list():
    """获取组织列表。"""
    from app.services.organization_service import organization_service
    orgs = organization_service.list()
    items = [{
        "id": o["id"],
        "name": o["name"],
        "description": o.get("description", ""),
        "createTime": int((o.get("create_time", 0) or 0) * 1000),
        "enable": o.get("status", "active") == "active",
        "memberCount": o.get("memberCount", 0),
    } for o in orgs]
    return ok(items)


@system_router.post("/system/organization/add")
def system_organization_add(payload: OrganizationAddBody):
    """添加组织。"""
    from app.services.organization_service import organization_service
    org = organization_service.create(
        name=payload.name,
        description=payload.description,
    )
    # 添加初始成员
    user_ids = payload.userIds or []
    if isinstance(user_ids, str):
        user_ids = [user_ids]
    if user_ids:
        for uid in user_ids:
            organization_service.add_member(org["id"], uid, role="admin")
    return ok({
        "id": org["id"],
        "name": org["name"],
        "description": org.get("description", ""),
        "createTime": int((org.get("create_time") or time.time()) * 1000),
        "enable": True,
    })
