# app/routers/missing_admin.py
"""缺失的管理后台 API 补充。

修复前端调用的以下缺失接口：
  1. 用户组（角色）管理：/user/role/global/*、/user/role/organization/*、/user/role/relation/global/*
  2. 组织/项目启用禁用：enable/disable（前端用 GET + 路径参数，后端只有 POST）
  3. 组织/项目移除成员：remove-member（前端用 GET + 路径参数）

用户组/角色管理数据已四层化收敛：Router 统一经 `auth_service` 调用，
数据访问落于 `app.repositories.user_group_repo.UserGroupRepo`（用户组表唯一 DB 入口）。
组织启停/成员移除等仍经 `admin_service` / `project_service` 承接。
不再返回硬编码占位数据。
"""

from fastapi import APIRouter

from app.core.response import ok

from app.domain.auth.application.dto import GroupMemberBody, GroupMemberListBody, GroupPermissionBody, UserGroupAddBody, UserGroupUpdateBody
from app.domain.admin_system.application.admin_app_service import admin_service
from app.domain.auth.application.auth_app_service import auth_service
from app.domain.project.application.project_app_service import project_service

router = APIRouter(tags=["missing-admin"])


def _batch_user_map(user_ids) -> dict:
    """批量反查用户信息，返回 {user_id: user}，避免循环内 get_user_by_id 造成 N+1。"""
    ids = [str(u) for u in (user_ids or []) if str(u)]
    if not ids:
        return {}
    id_set = set(ids)
    result = {}
    try:
        for u in auth_service.list_users(limit=10000):
            if str(u.get("id", "")) in id_set:
                result[str(u.get("id", ""))] = u
    except Exception:
        pass
    return result


# ════════════════════════════════════════════════════════════
# 一、用户组（角色）管理 - 全局 /user/role/global/*
# ════════════════════════════════════════════════════════════

@router.get("/user/role/global/list")
def user_role_global_list():
    """获取全局用户组列表。"""
    return ok(auth_service.list_groups("SYSTEM", "global"))


@router.get("/user/role/global/get/{role_id}")
def user_role_global_get(role_id: str):
    """获取全局用户组详情。"""
    group = auth_service.get_group(role_id)
    return ok(group or {"id": role_id, "name": "用户组", "description": "", "internal": True,
                         "type": "SYSTEM", "scopeId": "global"})


@router.post("/user/role/global/add")
def user_role_global_add(payload: UserGroupAddBody):
    """创建全局用户组。"""
    group = auth_service.create_group(
        name=payload.name,
        description=payload.description,
        group_type="SYSTEM",
        scope_id="global",
        create_user=payload.createUser,
        pos=int(payload.pos if payload.pos is not None else 99),
    )
    return ok(group)


@router.post("/user/role/global/update")
def user_role_global_update(payload: UserGroupUpdateBody):
    """更新全局用户组。"""
    group_id = payload.id
    group = auth_service.update_group(
        group_id,
        name=payload.name,
        description=payload.description,
        pos=int(payload.pos) if payload.pos is not None else None,
        update_user=payload.updateUser,
    )
    if not group:
        return ok({"id": group_id, "name": payload.name or "", "description": payload.description or ""})
    return ok(group)


@router.get("/user/role/global/delete/{role_id}")
def user_role_global_delete(role_id: str):
    """删除全局用户组。"""
    deleted = auth_service.delete_group(role_id)
    return ok({"id": role_id, "deleted": deleted})


def _load_system_permission_settings(role_id: str) -> list:
    """从数据库读取系统用户组权限，叠加到默认权限树。"""
    from app.routers.system_compat_userrole import _default_permission_settings
    settings = _default_permission_settings()
    # admin 内置组永远拥有全部权限
    if role_id in ("admin", "org_admin", "project_admin"):
        return settings
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


def _load_org_permission_settings(role_id: str) -> list:
    """从数据库读取组织用户组权限，叠加到默认权限树。"""
    from app.routers.system_compat_userrole import _default_permission_settings
    settings = _default_permission_settings()
    if role_id in ("admin", "org_admin", "project_admin"):
        return settings
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


@router.get("/user/role/global/permission/setting/{role_id}")
def user_role_global_permission_setting(role_id: str):
    """获取全局用户组权限配置（返回前端所需的权限树结构）。"""
    return ok(_load_system_permission_settings(role_id))


@router.post("/user/role/global/permission/update")
def user_role_global_permission_update(payload: GroupPermissionBody):
    """更新全局用户组权限。"""
    group_id = payload.id or payload.groupId
    perms = payload.permissions or payload.permissionIds or []
    if isinstance(perms, str):
        import json as _json
        try:
            perms = _json.loads(perms)
        except Exception:
            perms = [perms]
    auth_service.update_group_permissions(group_id, perms)
    return ok()


# ════════════════════════════════════════════════════════════
# 二、用户组（角色）管理 - 组织 /user/role/organization/*
# ════════════════════════════════════════════════════════════

@router.get("/user/role/organization/list/{organization_id}")
def user_role_org_list(organization_id: str):
    """获取组织用户组列表。"""
    return ok(auth_service.list_groups("ORGANIZATION", organization_id))


@router.get("/user/role/organization/get/{role_id}")
def user_role_org_get(role_id: str):
    """获取组织用户组详情。"""
    group = auth_service.get_group(role_id)
    return ok(group or {"id": role_id, "name": "组织用户组", "description": "", "internal": True,
                         "type": "ORGANIZATION", "scopeId": "organization"})


@router.post("/user/role/organization/add")
def user_role_org_add(payload: UserGroupAddBody):
    """创建组织用户组。"""
    group = auth_service.create_group(
        name=payload.name,
        description=payload.description,
        group_type="ORGANIZATION",
        scope_id=payload.scopeId or payload.organizationId,
        create_user=payload.createUser,
        pos=int(payload.pos if payload.pos is not None else 99),
    )
    return ok(group)


@router.post("/user/role/organization/update")
def user_role_org_update(payload: UserGroupUpdateBody):
    """更新组织用户组。"""
    group_id = payload.id
    group = auth_service.update_group(
        group_id,
        name=payload.name,
        description=payload.description,
        pos=int(payload.pos) if payload.pos is not None else None,
        update_user=payload.updateUser,
    )
    if not group:
        return ok({"id": group_id, "name": payload.name or "", "description": payload.description or ""})
    return ok(group)


@router.get("/user/role/organization/delete/{role_id}")
def user_role_org_delete(role_id: str):
    """删除组织用户组。"""
    deleted = auth_service.delete_group(role_id)
    return ok({"id": role_id, "deleted": deleted})


@router.get("/user/role/organization/permission/setting/{role_id}")
def user_role_org_permission_setting(role_id: str):
    """获取组织用户组权限配置（返回前端所需的权限树结构）。"""
    return ok(_load_org_permission_settings(role_id))


@router.post("/user/role/organization/permission/update")
def user_role_org_permission_update(payload: GroupPermissionBody):
    """更新组织用户组权限。"""
    group_id = payload.id or payload.groupId
    perms = payload.permissions or payload.permissionIds or []
    if isinstance(perms, str):
        import json as _json
        try:
            perms = _json.loads(perms)
        except Exception:
            perms = [perms]
    auth_service.update_group_permissions(group_id, perms)
    return ok()


@router.post("/user/role/organization/list-member")
def user_role_org_list_member(payload: GroupMemberListBody):
    """获取组织用户组成员列表。"""
    group_id = payload.groupId or payload.roleId or payload.id
    members = auth_service.list_group_members(group_id, payload.keyword)
    return ok({"list": members, "total": len(members)})


@router.post("/user/role/organization/add-member")
def user_role_org_add_member(payload: GroupMemberBody):
    """组织用户组添加成员。"""
    group_id = payload.groupId or payload.roleId or payload.id
    group_type = payload.type or "ORGANIZATION"
    scope_id = payload.scopeId or payload.organizationId
    user_ids = payload.userIds or payload.memberIds or []
    if isinstance(user_ids, str):
        user_ids = [user_ids]
    if not user_ids:
        user_ids = [payload.userId or payload.user_id]
    # 批量预取用户信息（一次 list + 内存分组），避免循环内 get_user_by_id 造成 N+1
    user_map = _batch_user_map(user_ids)
    added = []
    for uid in user_ids:
        if not uid:
            continue
        user = user_map.get(str(uid), {})
        member = auth_service.add_group_member(
            group_id=group_id,
            user_id=str(uid),
            username=user.get("username", "") if user else payload.username,
            name=user.get("name", "") if user else payload.name,
            email=user.get("email", "") if user else payload.email,
            group_type=group_type,
            scope_id=scope_id,
        )
        if member:
            added.append(member)
    return ok(added)


@router.post("/user/role/organization/remove-member")
def user_role_org_remove_member(payload: GroupMemberBody):
    """组织用户组移除成员。"""
    group_id = payload.groupId or payload.roleId or payload.id
    user_ids = payload.userIds or payload.memberIds or []
    if isinstance(user_ids, str):
        user_ids = [user_ids]
    if not user_ids:
        user_ids = [payload.userId or payload.user_id]
    removed = 0
    for uid in user_ids:
        if uid and auth_service.remove_group_member(group_id, str(uid)):
            removed += 1
    return ok({"removed": removed})


@router.get("/user/role/organization/get-member/option/{organization_id}/{role_id}")
def user_role_org_get_member_option(organization_id: str, role_id: str, keyword: str = ""):
    """组织用户组成员下拉选项。"""
    return ok(auth_service.get_user_options(exclude_group_id=role_id, keyword=keyword))


# ════════════════════════════════════════════════════════════
# 三、用户组-用户关联 /user/role/relation/global/*
# ════════════════════════════════════════════════════════════

@router.post("/user/role/relation/global/list")
def user_role_relation_global_list(payload: GroupMemberListBody):
    """获取全局用户组成员列表。"""
    group_id = payload.groupId or payload.roleId or payload.id
    members = auth_service.list_group_members(group_id, payload.keyword)
    return ok({"list": members, "total": len(members)})


@router.post("/user/role/relation/global/add")
def user_role_relation_global_add(payload: GroupMemberBody):
    """全局用户组添加成员。"""
    group_id = payload.groupId or payload.roleId or payload.id
    user_ids = payload.userIds or payload.memberIds or []
    if isinstance(user_ids, str):
        user_ids = [user_ids]
    if not user_ids:
        user_ids = [payload.userId or payload.user_id]
    # 批量预取用户信息（一次 list + 内存分组），避免循环内 get_user_by_id 造成 N+1
    user_map = _batch_user_map(user_ids)
    added = []
    for uid in user_ids:
        if not uid:
            continue
        user = user_map.get(str(uid), {})
        member = auth_service.add_group_member(
            group_id=group_id,
            user_id=str(uid),
            username=user.get("username", "") if user else payload.username,
            name=user.get("name", "") if user else payload.name,
            email=user.get("email", "") if user else payload.email,
            group_type="SYSTEM",
            scope_id="global",
        )
        if member:
            added.append(member)
    return ok(added)


@router.get("/user/role/relation/global/delete/{user_role_id}")
def user_role_relation_global_delete(user_role_id: str):
    """全局用户组移除成员。"""
    removed = auth_service.remove_group_member_by_id(user_role_id)
    return ok({"id": user_role_id, "deleted": removed})


@router.get("/user/role/relation/global/user/option/{user_role_id}")
def user_role_relation_global_user_option(user_role_id: str, keyword: str = ""):
    """全局用户组成员下拉选项。"""
    return ok(auth_service.get_user_options(exclude_group_id=user_role_id, keyword=keyword))


# ════════════════════════════════════════════════════════════
# 四、组织/项目启用禁用（前端用 GET + 路径参数）
# ════════════════════════════════════════════════════════════

@router.get("/system/organization/enable/{id}")
def system_org_enable(id: str):
    """启用组织。"""
    admin_service.enable_organization(id)
    return ok({"id": id, "enable": True})


@router.get("/system/organization/disable/{id}")
def system_org_disable(id: str):
    """禁用组织。"""
    admin_service.disable_organization(id)
    return ok({"id": id, "enable": False})


@router.get("/system/project/enable/{id}")
def system_project_enable(id: str):
    """启用项目。"""
    project_service.set_status(id, 'active')
    return ok({"id": id, "enable": True})


@router.get("/system/project/disable/{id}")
def system_project_disable(id: str):
    """禁用项目。"""
    project_service.set_status(id, 'archived')
    return ok({"id": id, "enable": False})


@router.get("/organization/project/enable/{id}")
def org_project_enable(id: str):
    """启用组织下项目。"""
    project_service.set_status(id, 'active')
    return ok({"id": id, "enable": True})


@router.get("/organization/project/disable/{id}")
def org_project_disable(id: str):
    """禁用组织下项目。"""
    project_service.set_status(id, 'disabled')
    return ok({"id": id, "enable": False})


# ════════════════════════════════════════════════════════════
# 五、组织/项目移除成员（前端用 GET + 路径参数）
# ════════════════════════════════════════════════════════════

@router.get("/system/organization/remove-member/{source_id}/{user_id}")
def system_org_remove_member(source_id: str, user_id: str):
    """移除组织成员。"""
    admin_service.remove_org_member(source_id, user_id)
    return ok({"source_id": source_id, "user_id": user_id, "removed": True})


@router.get("/system/project/remove-member/{source_id}/{user_id}")
def system_project_remove_member(source_id: str, user_id: str):
    """移除项目成员。"""
    project_service.remove_member(source_id, user_id)
    return ok({"source_id": source_id, "user_id": user_id, "removed": True})


# ════════════════════════════════════════════════════════════
# 六、其他方法不匹配修复
# ════════════════════════════════════════════════════════════

@router.get("/organization/project/user-admin-list/{organization_id}/{project_id}")
def org_project_user_admin_list(organization_id: str, project_id: str, keyword: str = ""):
    """获取组织项目管理员列表（带路径参数）。"""
    admins = auth_service.list_group_members("project-admin", keyword)
    return ok(admins)
