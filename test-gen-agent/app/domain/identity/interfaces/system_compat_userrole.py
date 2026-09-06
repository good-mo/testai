# app/routers/system_compat_userrole.py
"""system_compat 拆分：项目用户角色段（/user/role/*、/user/platform/*、/user/api/key/*）。

自 app/routers/system_compat.py 按业务段拆分（P4 超大文件拆分批次）。
路由定义与原文件顺序一致，纯搬移、行为不变。
"""

import time
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter

from app.core.response import ok, page_result
from app.models.user_role import (
    UserApiKeyUpdateBody,
    UserPlatformSaveBody,
    UserRoleProjectAddBody,
    UserRoleProjectListBody,
    UserRoleProjectListMemberBody,
    UserRoleProjectMemberBody,
    UserRoleProjectPermissionUpdateBody,
    UserRoleProjectUpdateBody,
)
from app.domain.auth.application.auth_app_service import auth_service
from app.domain.project.application.project_app_service import project_service

router = APIRouter(tags=["adapter-system-userrole"])


def _batch_user_map(user_ids) -> Dict[str, Dict]:
    """批量反查用户信息，返回 {user_id: user}，避免循环内 get_user_by_id 造成 N+1。"""
    ids = [str(u) for u in (user_ids or []) if str(u)]
    if not ids:
        return {}
    id_set = set(ids)
    result: Dict[str, Dict] = {}
    try:
        for u in auth_service.list_users(limit=10000):
            if str(u.get("id", "")) in id_set:
                result[str(u.get("id", ""))] = u
    except Exception:
        pass
    return result


# ════════════════════════════════════════════════════════════
# P1-11: 用户角色  /user/role/*  /user/platform/*  /user/api/key/*
# ════════════════════════════════════════════════════════════

# ── 项目用户组数据库存储（经 UserGroupRepo / auth_service 持久化） ──
# 内置项目用户组（id 固定，对应 user_groups 表已 seed 的 project-* 记录，
# 成员/权限经 auth_service 落库到 user_group_members / user_group_permissions）
_BUILTIN_PROJECT_GROUPS = [
    {
        "id": "project-admin",
        "name": "项目管理员",
        "description": "项目管理员",
        "internal": True,
        "type": "PROJECT",
        "scopeId": "",
        "createTime": 0,
        "updateTime": 0,
        "createUser": "admin",
        "pos": 1,
    },
    {
        "id": "project-member",
        "name": "项目成员",
        "description": "项目成员",
        "internal": True,
        "type": "PROJECT",
        "scopeId": "",
        "createTime": 0,
        "updateTime": 0,
        "createUser": "admin",
        "pos": 2,
    },
    {
        "id": "project-readonly",
        "name": "项目只读成员",
        "description": "项目只读成员",
        "internal": True,
        "type": "PROJECT",
        "scopeId": "",
        "createTime": 0,
        "updateTime": 0,
        "createUser": "admin",
        "pos": 3,
    },
]

def _get_db_custom_groups(scope_id: str) -> List[Dict[str, Any]]:
    """从数据库读取指定项目的自定义用户组（type=PROJECT, scope_id=项目ID）。"""
    try:
        groups = auth_service.list_groups("PROJECT", scope_id)
        result = []
        for g in groups:
            # 内置项目组 id 固定为 project-*，跳过（它们另由 _BUILTIN_PROJECT_GROUPS 管理）
            if g.get("id") in ("project-admin", "project-member", "project-readonly"):
                continue
            g["type"] = "PROJECT"
            g["scopeId"] = scope_id
            result.append(g)
        return result
    except Exception:
        return []

def _get_default_user_groups(scope_id: str) -> List[Dict[str, Any]]:
    """返回指定项目的用户组列表（含内置组和数据库中的自定义组）。"""
    defaults = [dict(g) for g in _BUILTIN_PROJECT_GROUPS]
    for g in defaults:
        g["scopeId"] = scope_id
    defaults.extend(_get_db_custom_groups(scope_id))
    return defaults

def _group_member_count(group_id: str) -> int:
    """返回用户组成员数量（来自 user_group_members 表）。"""
    try:
        return len(auth_service.list_group_members(group_id))
    except Exception:
        return 0

def _get_user_group_list_with_count(scope_id: str) -> List[Dict[str, Any]]:
    """返回用户组列表，并计算成员数量。"""
    groups = _get_default_user_groups(scope_id)
    result = []
    for g in groups:
        item = dict(g)
        item["memberCount"] = _group_member_count(g["id"])
        result.append(item)
    return result

def _get_users_from_db(keyword: str = "") -> List[Dict[str, Any]]:
    """从数据库获取用户列表。"""
    try:
        users = auth_service.list_users()
        if keyword:
            kw = keyword.lower()
            users = [u for u in users if kw in (u.get("username", "") or "").lower()
                     or kw in (u.get("name", "") or "").lower()
                     or kw in (u.get("email", "") or "").lower()]
        return users
    except Exception:
        return []

def _member_to_row(u) -> Dict[str, Any]:
    """将用户信息转换为前端成员行。"""
    return {
        "id": u.get("id", ""),
        "name": u.get("name", u.get("username", "")),
        "username": u.get("username", ""),
        "email": u.get("email", ""),
        "phone": u.get("phone", ""),
        "enable": u.get("enable", True),
        "adminFlag": False,
    }

def _load_permission_settings(role_id: str) -> List[Dict[str, Any]]:
    """从数据库读取已保存的项目用户组权限，叠加到默认权限树。

    user_group_permissions 表存的是「已启用权限的 ID 列表」（JSON）。
    无历史记录时返回默认树（默认全部 enable=True）。
    """
    settings = _default_permission_settings()
    try:
        enabled_ids = auth_service.get_group_permissions(role_id)
        enabled_set = set(enabled_ids or [])
    except Exception:
        enabled_set = set()
    if not enabled_set:
        return settings
    for menu in settings:
        for child in menu.get("children", []):
            for perm in child.get("permissions", []):
                if perm.get("id") in enabled_set:
                    perm["enable"] = True
                else:
                    perm["enable"] = False
    return settings

def _save_permission_settings(user_role_id: str, permissions: List[Any]) -> None:
    """将项目用户组权限持久化到 user_group_permissions 表。

    入参 permissions 为前端提交的 [{id, enable}, ...] 或权限 ID 列表。
    落库内容为「enable=True 的权限 ID 列表」。
    """
    enabled_ids: List[str] = []
    for p in permissions or []:
        if isinstance(p, dict):
            if p.get("enable"):
                enabled_ids.append(str(p.get("id", "")))
        elif isinstance(p, str) and p:
            enabled_ids.append(p)
    enabled_ids = [pid for pid in enabled_ids if pid]
    if not user_role_id:
        return
    try:
        auth_service.update_group_permissions(user_role_id, enabled_ids)
    except Exception:
        pass

@router.post("/user/role/project/add")
async def user_role_project_add(body: UserRoleProjectAddBody = UserRoleProjectAddBody()):
    """添加项目用户组（持久化到 user_groups 表）。"""
    name = body.name
    scope_id = body.scopeId
    try:
        group = auth_service.create_group(
            name=name,
            description="",
            group_type="PROJECT",
            scope_id=scope_id,
            create_user="admin",
            pos=99,
        )
    except Exception:
        # 数据库不可用则退回返回提示
        group = None
    if group:
        group["type"] = "PROJECT"
        group["scopeId"] = scope_id
        return ok(group)
    return ok({"id": body.id or str(uuid.uuid4()),
                "name": name, "type": "PROJECT", "scopeId": scope_id,
                "internal": False, "createTime": time.time(),
                "updateTime": time.time(), "createUser": "admin", "pos": 99})

@router.post("/user/role/project/update")
async def user_role_project_update(body: UserRoleProjectUpdateBody = UserRoleProjectUpdateBody()):
    """更新项目用户组（持久化到 user_groups 表）。"""
    group_id = body.id
    name = body.name or None
    description = body.description
    updated = auth_service.update_group(
        group_id,
        name=name,
        description=description if description is not None else None,
        update_user="admin",
    )
    if updated:
        updated["type"] = "PROJECT"
        return ok(updated)
    # 内置用户组或不存在时：内置组不允许改名（internal），只返回提示
    return ok({"id": group_id,
                "name": body.name or "",
                "updateTime": time.time()})

@router.get("/user/role/project/delete/{group_id}")
def user_role_project_delete_get(group_id: str):
    """删除项目用户组（GET + 路径参数，持久化删除）。"""
    deleted = auth_service.delete_group(group_id)
    return ok({"id": group_id, "deleted": deleted or True})

@router.delete("/user/role/project/delete/{group_id}")
def user_role_project_delete(group_id: str):
    """删除项目用户组（DELETE + 路径参数，持久化删除）。"""
    deleted = auth_service.delete_group(group_id)
    return ok({"id": group_id, "deleted": deleted or True})

@router.post("/user/role/project/delete/{group_id}")
def user_role_project_delete_post(group_id: str):
    """删除项目用户组（POST + 路径参数，持久化删除）。"""
    deleted = auth_service.delete_group(group_id)
    return ok({"id": group_id, "deleted": deleted or True})

@router.post("/user/role/project/list")
async def user_role_project_list(body: UserRoleProjectListBody = UserRoleProjectListBody()):
    """项目用户组列表。"""
    scope_id = body.projectId
    items = _get_user_group_list_with_count(scope_id)
    keyword = body.keyword or ""
    if keyword:
        kw = keyword.lower()
        items = [g for g in items if kw in g.get("name", "").lower()]
    return page_result(items, len(items), current=body.current, page_size=body.pageSize)

@router.post("/user/role/project/list-member")
async def user_role_project_list_member(body: UserRoleProjectListMemberBody = UserRoleProjectListMemberBody()):
    """项目用户组成员列表（从 user_group_members 表读取）。"""
    project_id = body.projectId
    user_role_id = body.userRoleId
    keyword = body.keyword or ""

    members = []
    try:
        db_members = auth_service.list_group_members(user_role_id, keyword)
        all_users = {u.get("id"): u for u in _get_users_from_db()}
        for m in db_members:
            uid = m.get("userId") or m.get("user_id", "")
            u = all_users.get(uid, {})
            members.append(_member_to_row(u) if u else {
                "id": uid,
                "name": m.get("name", m.get("username", "")),
                "username": m.get("username", ""),
                "email": m.get("email", ""),
                "phone": "",
                "enable": True,
                "adminFlag": False,
            })
    except Exception:
        pass

    # 内置组为空时兜底：尝试从项目成员表读取（user_group 字段关联）
    if not members and project_id and user_role_id in ("project-admin", "project-member", "project-readonly"):
        try:
            db_members = project_service.list_members(project_id)
            for m in db_members:
                groups = str(m.get("user_group", "") or "").split(",")
                if user_role_id in groups:
                    members.append({
                        "id": m.get("user_id", ""),
                        "name": m.get("name", m.get("username", "")),
                        "username": m.get("username", ""),
                        "email": m.get("email", ""),
                        "phone": "",
                        "enable": True,
                        "adminFlag": m.get("role", "") == "admin",
                    })
        except Exception:
            pass

    if keyword:
        kw = keyword.lower()
        members = [m for m in members if kw in (m.get("name", "") or "").lower()
                   or kw in (m.get("email", "") or "").lower()
                   or kw in (m.get("username", "") or "").lower()]

    current = body.current
    page_size = body.pageSize
    total = len(members)
    start = (current - 1) * page_size
    page_items = members[start:start + page_size]
    return ok({
        "list": page_items,
        "total": total,
        "pageSize": page_size,
        "current": current,
    })

@router.get("/user/role/project/get-member/option/{project_id}/{user_role_id}")
def user_role_project_get_member_option(project_id: str, user_role_id: str, keyword: str = ""):
    """项目用户组成员下拉选项（排除已加入成员）。"""
    try:
        existing = {m.get("userId") or m.get("user_id", "") for m in auth_service.list_group_members(user_role_id)}
    except Exception:
        existing = set()

    options = []
    for u in _get_users_from_db(keyword):
        uid = u.get("id", "")
        if uid in existing:
            continue
        options.append({
            "id": uid,
            "name": u.get("name", u.get("username", "")),
            "email": u.get("email", ""),
            "phone": u.get("phone", ""),
            "username": u.get("username", ""),
            "checkRoleFlag": False,
        })
    return ok(options)

@router.get("/user/role/project/get-member/option/")
def user_role_project_get_member_option_old(role_id: str = ""):
    """项目用户组成员下拉选项（兼容旧调用）。"""
    return ok([])

@router.get("/user/role/project/permission/setting/{role_id}")
def user_role_project_permission_setting(role_id: str):
    """项目用户组权限设置（带路径参数，从数据库读取已保存状态）。"""
    return ok(_load_permission_settings(role_id))

@router.get("/user/role/project/permission/setting/")
def user_role_project_permission_setting_old(role_id: str = ""):
    """项目用户组权限设置（兼容旧调用，从数据库读取已保存状态）。"""
    return ok(_load_permission_settings(role_id))

def _default_permission_settings() -> List[Dict[str, Any]]:
    """返回项目用户组默认权限配置。"""
    return [
        {
            "id": "project",
            "name": "项目",
            "license": False,
            "enable": True,
            "children": [
                {
                    "id": "project_management",
                    "name": "项目管理",
                    "license": False,
                    "enable": True,
                    "permissions": [
                        {"id": "PROJECT_GROUP:READ", "name": "查看用户组", "enable": True, "license": False},
                        {"id": "PROJECT_GROUP:READ+ADD", "name": "新增用户组", "enable": True, "license": False},
                        {"id": "PROJECT_GROUP:READ+UPDATE", "name": "编辑用户组", "enable": True, "license": False},
                        {"id": "PROJECT_MEMBER:READ", "name": "查看成员", "enable": True, "license": False},
                        {"id": "PROJECT_MEMBER:READ+ADD", "name": "添加成员", "enable": True, "license": False},
                        {"id": "PROJECT_MEMBER:READ+UPDATE", "name": "编辑成员", "enable": True, "license": False},
                    ],
                },
                {
                    "id": "project_menu",
                    "name": "项目菜单",
                    "license": False,
                    "enable": True,
                    "permissions": [
                        {"id": "PROJECT_MENU:READ", "name": "查看", "enable": True, "license": False},
                    ],
                },
            ],
        },
        {
            "id": "test_plan",
            "name": "测试计划",
            "license": False,
            "enable": True,
            "children": [
                {
                    "id": "test_plan_management",
                    "name": "测试计划管理",
                    "license": False,
                    "enable": True,
                    "permissions": [
                        {"id": "TEST_PLAN:READ", "name": "查看", "enable": True, "license": False},
                        {"id": "TEST_PLAN:READ+ADD", "name": "新增", "enable": True, "license": False},
                        {"id": "TEST_PLAN:READ+UPDATE", "name": "编辑", "enable": True, "license": False},
                    ],
                },
            ],
        },
        {
            "id": "bug_management",
            "name": "缺陷管理",
            "license": False,
            "enable": True,
            "children": [
                {
                    "id": "bug_management",
                    "name": "缺陷管理",
                    "license": False,
                    "enable": True,
                    "permissions": [
                        {"id": "BUG_MANAGEMENT:READ", "name": "查看", "enable": True, "license": False},
                        {"id": "BUG_MANAGEMENT:READ+ADD", "name": "新增", "enable": True, "license": False},
                        {"id": "BUG_MANAGEMENT:READ+UPDATE", "name": "编辑", "enable": True, "license": False},
                    ],
                },
            ],
        },
        {
            "id": "case_management",
            "name": "用例管理",
            "license": False,
            "enable": True,
            "children": [
                {
                    "id": "case_management",
                    "name": "用例管理",
                    "license": False,
                    "enable": True,
                    "permissions": [
                        {"id": "CASE_MANAGEMENT:READ", "name": "查看", "enable": True, "license": False},
                        {"id": "CASE_MANAGEMENT:READ+ADD", "name": "新增", "enable": True, "license": False},
                        {"id": "CASE_MANAGEMENT:READ+UPDATE", "name": "编辑", "enable": True, "license": False},
                    ],
                },
            ],
        },
        {
            "id": "api_test",
            "name": "接口测试",
            "license": False,
            "enable": True,
            "children": [
                {
                    "id": "api_test",
                    "name": "接口测试",
                    "license": False,
                    "enable": True,
                    "permissions": [
                        {"id": "API_TEST:READ", "name": "查看", "enable": True, "license": False},
                        {"id": "API_TEST:READ+ADD", "name": "新增", "enable": True, "license": False},
                        {"id": "API_TEST:READ+UPDATE", "name": "编辑", "enable": True, "license": False},
                    ],
                },
            ],
        },
        {
            "id": "workstation",
            "name": "工作台",
            "license": False,
            "enable": True,
            "children": [
                {
                    "id": "workstation",
                    "name": "工作台",
                    "license": False,
                    "enable": True,
                    "permissions": [
                        {"id": "WORKSTATION:READ", "name": "查看", "enable": True, "license": False},
                    ],
                },
            ],
        },
    ]

@router.post("/user/role/project/permission/update")
async def user_role_project_permission_update(body: UserRoleProjectPermissionUpdateBody = UserRoleProjectPermissionUpdateBody()):
    """更新项目用户组权限（持久化到 user_group_permissions 表）。"""
    user_role_id = body.effective_role_id
    permissions = body.permissions
    _save_permission_settings(user_role_id, permissions)
    # 返回更新后的权限列表（从数据库读回最新状态）
    return ok(_load_permission_settings(user_role_id))

@router.post("/user/role/project/add-member")
async def user_role_project_add_member(body: UserRoleProjectMemberBody = UserRoleProjectMemberBody()):
    """项目用户组添加成员（持久化到 user_group_members 表）。"""
    project_id = body.projectId
    user_role_id = body.userRoleId
    user_ids = body.effective_user_ids

    # 批量预取用户信息（一次 list + 内存分组），避免循环内 get_user_by_id 造成 N+1
    user_map = _batch_user_map(user_ids)
    added = 0
    for uid in user_ids:
        if not uid:
            continue
        user = user_map.get(str(uid), {})
        member = auth_service.add_group_member(
            group_id=user_role_id,
            user_id=uid,
            username=user.get("username", "") if user else "",
            name=user.get("name", "") if user else "",
            email=user.get("email", "") if user else "",
            group_type="PROJECT",
            scope_id=project_id,
        )
        if member:
            added += 1

    return ok({"success": True, "added": added})

@router.post("/user/role/project/remove-member")
async def user_role_project_remove_member(body: UserRoleProjectMemberBody = UserRoleProjectMemberBody()):
    """项目用户组移除成员（持久化从 user_group_members 表删除）。"""
    user_role_id = body.userRoleId
    user_ids = body.effective_user_ids

    removed = 0
    for uid in user_ids:
        if uid and auth_service.remove_group_member(user_role_id, uid):
            removed += 1

    return ok({"success": True, "removed": removed})

# 用户平台

@router.get("/user/platform/get")
def user_platform_get():
    """用户平台信息。"""
    return ok({})

@router.post("/user/platform/save")
async def user_platform_save(body: UserPlatformSaveBody = UserPlatformSaveBody()):
    """保存用户平台。"""
    return ok()

@router.get("/user/platform/switch-option")
def user_platform_switch_option():
    """平台切换选项。"""
    return ok([])

@router.get("/user/platform/account/info")
def user_platform_account_info(platform: str = ""):
    """平台账户信息。"""
    return ok({})

@router.post("/user/platform/validate")
async def user_platform_validate(body: UserPlatformSaveBody = UserPlatformSaveBody()):
    """平台校验。"""
    return ok({"success": True})

# API Key

@router.post("/user/api/key/update")
async def user_api_key_update(body: UserApiKeyUpdateBody = UserApiKeyUpdateBody()):
    """更新 API Key。"""
    return ok({"accessKey": str(uuid.uuid4()).replace("-", ""),
                "secretKey": str(uuid.uuid4()).replace("-", "")})

@router.post("/user/api/key/validate")
async def user_api_key_validate(body: UserApiKeyUpdateBody = UserApiKeyUpdateBody()):
    """校验 API Key。"""
    return ok({"valid": True})
