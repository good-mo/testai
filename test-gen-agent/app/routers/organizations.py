# app/routers/organizations.py
"""组织域路由（Phase F · adapters/domains 收敛样板）。

组织成员 / 项目相关兼容路由。修复前端口径：
  - /organization/member/list  支持 GET + POST 分页，返回前端契约格式
  - /organization/remove-member/{orgId}/{userId}  路径参数 GET 兼容
  - /organization/user/role/list/{orgId}  路径参数 GET 兼容
  - /organization/project/page 返回 camelCase 前端字段
"""

from typing import Any, Dict, List

from fastapi import APIRouter

from app.core.response import ok, page_result
from app.models.organizations import (
    OrgMemberAddBody,
    OrgMemberListPageQuery,
    OrgMemberRemoveBody,
    OrgMemberUpdateBody,
    OrgProjectCreateBody,
    OrgProjectMemberAddBody,
    OrgProjectMemberPageQuery,
    OrgProjectMembersAddBody,
    OrgProjectPageQuery,
    OrgProjectRenameBody,
    OrgProjectUpdateBody,
    OrgRoleUpdateMemberBody,
)
from app.services.auth_service import auth_service
from app.services.project_service import project_service

router = APIRouter(tags=["organizations"])


def _batch_user_map(auth_svc, user_ids) -> Dict[str, Dict]:
    """批量反查用户信息，返回 {user_id: user} 内存映射。

    一次 list_users 后按 id 分组，替代循环内逐个 get_user_by_id，规避 N+1 查询。
    """
    ids = [str(u) for u in (user_ids or []) if str(u)]
    if not ids:
        return {}
    id_set = set(ids)
    result: Dict[str, Dict] = {}
    try:
        for u in auth_svc.list_users(limit=10000):
            uid = u.get("id", "")
            if uid in id_set:
                result[uid] = u
    except Exception:
        pass
    return result


def _get_org_name(org_id: str) -> str:
    """根据组织 ID 获取组织名称。"""
    try:
        from app.services.organization_service import organization_service
        org = organization_service.get(org_id)
        return org.get("name", "") if org else org_id
    except Exception:
        return org_id




def _get_org_projects_frontend(projects: List[dict], org_id: str) -> List[dict]:
    """将组织项目列表转为前端 OrgProjectTableItem 结构。"""
    org_name = _get_org_name(org_id)
    # 计算各项目成员数（经 Service 层聚合统计，不在路由层写 SQL）
    try:
        member_counts: Dict[str, int] = project_service.count_members_by_project()
    except Exception:
        member_counts = {}

    items = []
    for p in projects:
        pid = p.get("id", "")
        items.append({
            "id": pid,
            "num": int(p.get("num", 0)),
            "organizationId": p.get("organization_id", org_id),
            "organizationName": org_name,
            "name": p.get("name", ""),
            "description": p.get("description", ""),
            "createTime": int((p.get("created_at", p.get("create_time", 0)) or 0) * 1000),
            "updateTime": int((p.get("updated_at", p.get("update_time", 0)) or 0) * 1000),
            "createUser": p.get("create_user", p.get("createUser", "admin")),
            "updateUser": p.get("update_user", "admin"),
            "enable": p.get("status", "active") != "disabled",
            "deleted": bool(p.get("deleted", 0)),
            "memberCount": member_counts.get(pid, 0),
            "adminList": [],
            "moduleIds": [],
            "resourcePoolList": [],
            "allResourcePool": True,
            "orgCreateUserIsAdmin": True,
        })
    return items



# ════════════════════════════════════════════════════════════
# 组织项目
# ════════════════════════════════════════════════════════════

@router.get("/organization/project/list")
def org_project_list(org_id: str = ""):
    """组织项目列表（GET，query 或 path 两种模式兼容）。"""
    from app.services.organization_service import organization_service
    oid = org_id or "default-org"
    projects = organization_service.list_projects(oid)
    return ok(_get_org_projects_frontend(projects, oid))

@router.get("/organization/project/list/{org_id}")
def org_project_list_path(org_id: str):
    """组织项目列表（路径参数版，前端 GET /organization/project/list/{orgId}）。"""
    from app.services.organization_service import organization_service
    projects = organization_service.list_projects(org_id) if org_id else []
    return ok(_get_org_projects_frontend(projects, org_id))

@router.post("/organization/project/page")
async def org_project_page(body: OrgProjectPageQuery = OrgProjectPageQuery()):
    """组织项目分页。返回前端 OrgProjectTableItem 结构。"""
    org_id = body.organizationId or body.orgId or ""
    keyword = body.keyword
    current = body.current
    page_size = body.pageSize

    from app.services.organization_service import organization_service
    projects = organization_service.list_projects(org_id) if org_id else []
    # 过滤关键词
    if keyword:
        kw = str(keyword).lower()
        projects = [p for p in projects if kw in p.get("name", "").lower() or kw in p.get("description", "").lower()]
    items = _get_org_projects_frontend(projects, org_id)
    return page_result(items, len(items), current=current, page_size=page_size)

@router.post("/organization/project/add")
async def org_project_add(body: OrgProjectCreateBody = OrgProjectCreateBody()):
    """组织添加项目。"""
    org_id = body.organizationId or "default-org"
    from app.services.organization_service import organization_service
    from app.services.project_service import project_service
    proj = project_service.create({
        "name": body.name,
        "description": body.description,
    })
    if proj and proj.get("id"):
        organization_service.bind_project(proj["id"], org_id)
    return ok(proj)

@router.post("/organization/project/update")
async def org_project_update(body: OrgProjectUpdateBody = OrgProjectUpdateBody()):
    """组织更新项目。"""
    pid = body.id or body.projectId or ""
    if pid:
        from app.services.project_service import project_service
        data = body.model_dump(exclude_unset=True)
        fields = {k: v for k, v in data.items()
                  if k not in ("id", "projectId", "organizationId", "userIds", "moduleIds",
                               "resourcePoolIds", "allResourcePool")}
        project_service.update(pid, fields)
        # 处理 userIds（管理员列表）
        admin_ids = body.userIds or []
        if isinstance(admin_ids, list) and admin_ids:
            for uid in admin_ids:
                project_service.add_member(pid, user_id=uid, role="admin")
    return ok()

@router.post("/organization/project/rename")
async def org_project_rename(body: OrgProjectRenameBody = OrgProjectRenameBody()):
    """组织重命名项目。"""
    pid = body.id or body.projectId or ""
    name = body.name
    if pid and name:
        from app.services.project_service import project_service
        project_service.update(pid, {"name": name})
    return ok()

@router.get("/organization/project/delete/")
@router.delete("/organization/project/delete/")
def org_project_delete(project_id: str = ""):
    """组织删除项目（query / path / body）。"""
    if project_id:
        from app.services.project_service import project_service
        project_service.set_status(project_id, 'deleted')
    return ok()

@router.get("/organization/project/delete/{id}")
@router.post("/organization/project/delete/{id}")
def org_project_delete_path(id: str):
    """组织删除项目（路径参数版）。"""
    from app.services.project_service import project_service
    project_service.set_status(id, 'deleted')
    return ok({"id": id, "deleted": True})

@router.post("/organization/project/enable/")
def org_project_enable(project_id: str = ""):
    """组织启用项目。"""
    if project_id:
        from app.services.project_service import project_service
        project_service.set_status(project_id, 'active')
    return ok()

@router.post("/organization/project/disable/")
def org_project_disable(project_id: str = ""):
    """组织禁用项目。"""
    if project_id:
        from app.services.project_service import project_service
        project_service.set_status(project_id, 'disabled')
    return ok()

@router.post("/organization/project/revoke/")
def org_project_revoke(project_id: str = ""):
    """组织恢复项目。"""
    if project_id:
        from app.services.project_service import project_service
        project_service.set_status(project_id, 'active')
    return ok()

@router.get("/organization/project/revoke/{id}")
def org_project_revoke_path(id: str):
    """组织恢复项目（路径参数版）。"""
    from app.services.project_service import project_service
    project_service.set_status(id, 'active')
    return ok({"id": id, "revoked": True})

@router.post("/organization/project/add-member")
async def org_project_add_member(body: OrgProjectMemberAddBody = OrgProjectMemberAddBody()):
    """组织项目添加成员。"""
    project_id = body.projectId or body.id or ""
    user_ids = body.userIds or body.memberIds or []
    if isinstance(user_ids, str):
        user_ids = [user_ids]
    from app.services.project_service import project_service
    result = []
    for uid in user_ids:
        m = project_service.add_member(project_id, user_id=uid, role=body.role)
        if m:
            result.append(m)
    return ok(result)

@router.post("/organization/project/add-members")
async def org_project_add_members(body: OrgProjectMembersAddBody = OrgProjectMembersAddBody()):
    """组织项目批量添加成员。"""
    project_id = body.projectId or body.id or ""
    org_id = body.organizationId
    user_ids = body.userIds or body.memberIds or []
    if isinstance(user_ids, str):
        user_ids = [user_ids]
    from app.services.auth_service import auth_service
    from app.services.project_service import project_service
    # 批量预取用户信息（一次 list + 内存分组），避免循环内 get_user_by_id 造成 N+1
    user_map = _batch_user_map(auth_service, [str(u) for u in user_ids])
    result = []
    for uid in user_ids:
        user = user_map.get(str(uid), {})
        m = project_service.add_member(project_id, user_id=str(uid),
                                        role=body.role,
                                        username=user.get("username", "") if user else "",
                                        name=user.get("name", "") if user else "",
                                        email=user.get("email", "") if user else "")
        if m:
            result.append(m)
        # 同步加入组织
        if org_id:
            try:
                from app.services.organization_service import organization_service
                organization_service.add_member(org_id, str(uid), role="member")
            except Exception:
                pass
    return ok(result)

@router.get("/organization/project/member-list")
def org_project_member_list(project_id: str = ""):
    """组织项目成员列表。"""
    from app.services.project_service import project_service
    members = project_service.list_members(project_id) if project_id else []
    # 转 camelCase 前端格式
    items = []
    for m in members:
        items.append({
            "id": m.get("id", ""),
            "userId": m.get("user_id", ""),
            "name": m.get("name", ""),
            "email": m.get("email", ""),
            "role": m.get("role", ""),
            "createTime": int((m.get("created_at", m.get("create_time", 0)) or 0) * 1000),
            "updateTime": int((m.get("updated_at", m.get("update_time", 0)) or 0) * 1000),
        })
    return ok(items)

@router.post("/organization/project/member-list")
async def org_project_member_list_post(body: OrgProjectMemberPageQuery = OrgProjectMemberPageQuery()):
    """组织项目成员列表（POST 分页）。"""
    project_id = body.projectId or body.id or ""
    keyword = body.keyword
    current = body.current
    page_size = body.pageSize
    from app.services.project_service import project_service
    members = project_service.list_members(project_id) if project_id else []
    if keyword:
        kw = str(keyword).lower()
        members = [m for m in members if kw in m.get("name", "").lower()
                   or kw in m.get("email", "").lower()
                   or kw in m.get("username", "").lower()]
    items = []
    for m in members:
        items.append({
            "id": m.get("id", ""),
            "userId": m.get("user_id", ""),
            "name": m.get("name", ""),
            "email": m.get("email", ""),
            "role": m.get("role", ""),
            "createTime": int((m.get("created_at", m.get("create_time", 0)) or 0) * 1000),
            "updateTime": int((m.get("updated_at", m.get("update_time", 0)) or 0) * 1000),
        })
    return page_result(items, len(items), current=current, page_size=page_size)


# ════════════════════════════════════════════════════════════
# 组织成员
# ════════════════════════════════════════════════════════════


# ── 组织成员数据转换 ────────────────────────────────────
_ROLE_NAME_MAP = {
    "admin": "组织管理员",
    "member": "组织成员",
    "viewer": "只读成员",
}


def _enrich_org_members(members: List[Dict]) -> List[Dict]:
    """将组织成员记录转换为前端 MemberItem 格式。

    原始 organization_members 表记录字段为 organization_id / user_id / username /
    name / email / role / create_time / update_time，与前端 MemberItem
    (id / email / phone / enable / projectIdNameMap / userRoleIdNameMap ...) 不对齐。

    这里按 user_id 批量反查用户、项目与角色，拼接成前端可直接消费的结构。
    """
    if not members:
        return []
    result: List[Dict] = []
    # 批量反查用户信息（避免 N+1）
    user_id_set = {m.get("user_id", "") for m in members if m.get("user_id")}
    user_map: Dict[str, Dict] = {}
    try:
        users = auth_service.list_users()
        for u in users:
            uid = u.get("id", "")
            if uid in user_id_set:
                user_map[uid] = u
    except Exception:
        pass
    # 批量反查项目成员关系（单条 SQL 联查，避免逐项目 list_members 造成 N+1）
    project_user_map: Dict[str, List[Dict]] = {}
    try:
        project_user_map = project_service.list_projects_by_user_ids(list(user_id_set))
    except Exception:
        project_user_map = {}

    for m in members:
        uid = m.get("user_id", "")
        user = user_map.get(uid, {})
        role = m.get("role", "member")
        item = {
            "id": user.get("id", uid),
            "username": user.get("username", m.get("username", "")),
            "name": user.get("name", m.get("name", "")),
            "email": user.get("email", m.get("email", "")),
            "phone": user.get("phone", ""),
            "enable": bool(user.get("enable", 1)) if user else True,
            "createTime": int((m.get("create_time", 0) or 0) * 1000),
            "updateTime": int((m.get("update_time", 0) or 0) * 1000),
            "language": user.get("language", "zh-CN"),
            "lastOrganizationId": m.get("organization_id", ""),
            "source": "LOCAL",
            "lastProjectId": [],
            "createUser": user.get("create_user", "admin"),
            "updateUser": user.get("update_user", "admin"),
            "deleted": False,
            # 项目与用户组标签
            "projectIdNameMap": project_user_map.get(uid, []),
            "userRoleIdNameMap": [{"id": role, "name": _ROLE_NAME_MAP.get(role, role)}],
        }
        result.append(item)
    return result


@router.get("/organization/member/list")
def org_member_list(org_id: str = ""):
    """组织成员列表（GET）。"""
    from app.services.organization_service import organization_service
    return ok(organization_service.list_members(org_id or "default-org"))

@router.get("/organization/member/list/{org_id}")
def org_member_list_path(org_id: str):
    """组织成员列表（路径参数版）。"""
    from app.services.organization_service import organization_service
    return ok(organization_service.list_members(org_id or "default-org"))

@router.post("/organization/member/list")
async def org_member_list_post(body: OrgMemberListPageQuery = OrgMemberListPageQuery()):
    """组织成员列表（POST - 前端分页查询兼容）。

    前端 organization/member 页面经 useTable 调用 POST /organization/member/list，
    body 含 current/pageSize/keyword 等分页与过滤参数。
    """
    org_id = body.organizationId or body.orgId or "default-org"
    keyword = body.keyword
    from app.services.organization_service import organization_service
    members = organization_service.list_members(org_id, search=keyword)
    enriched = _enrich_org_members(members)
    return page_result(enriched, len(enriched), current=body.current, page_size=body.pageSize)


@router.get("/organization/user/role/list")
def org_user_role_list(org_id: str = ""):
    """组织用户角色/用户组列表（GET query 版本）。

    优先读取 user_groups 表中 type=ORGANIZATION 的用户组，
    退回硬编码内置组。
    """
    try:
        from app.services.auth_service import auth_service
        groups = auth_service.list_groups("ORGANIZATION", org_id or "")
        if groups:
            return ok(groups)
    except Exception:
        pass
    return ok([
        {"id": "org-admin", "name": "组织管理员", "type": "ORGANIZATION", "internal": True},
        {"id": "org-member", "name": "组织成员", "type": "ORGANIZATION", "internal": True},
    ])


@router.get("/organization/user/role/list/{org_id}")
def org_user_role_list_path(org_id: str):
    """组织用户角色/用户组列表（路径参数版，前端 getGlobalUserGroup 调用）。"""
    return org_user_role_list(org_id)


@router.post("/organization/role/update-member")
async def org_role_update_member(body: OrgRoleUpdateMemberBody = OrgRoleUpdateMemberBody()):
    """更新成员角色/批量添加成员到用户组。"""
    org_id = body.organizationId or body.orgId or ""
    member_ids = body.memberIds or body.userIds or []
    user_role_ids = body.userRoleIds or body.roleIds or []
    if isinstance(member_ids, str):
        member_ids = [member_ids]
    if isinstance(user_role_ids, str):
        user_role_ids = [user_role_ids]

    from app.services.auth_service import auth_service
    from app.services.organization_service import organization_service

    # 批量预取成员用户信息（一次 list + 内存分组），避免循环内 get_user_by_id 造成 N+1
    user_map = _batch_user_map(auth_service, [str(m) for m in member_ids])
    # 向指定用户组添加成员
    for gid in user_role_ids:
        for mid in member_ids:
            user = user_map.get(str(mid), {})
            auth_service.add_group_member(
                group_id=gid,
                user_id=str(mid),
                username=user.get("username", "") if user else "",
                name=user.get("name", "") if user else "",
                email=user.get("email", "") if user else "",
                group_type="ORGANIZATION",
                scope_id=org_id,
            )
    # 同步更新组织成员关系
    for mid in member_ids:
        organization_service.add_member(org_id or "default-org", str(mid), role="member")
    return ok()


@router.post("/organization/add-member")
async def org_add_member(body: OrgMemberAddBody = OrgMemberAddBody()):
    """组织添加成员。兼容前端 AddMemberModal 的 POST 数据格式。"""
    org_id = body.organizationId or body.orgId or "default-org"
    member_ids = body.memberIds or body.userIds or []
    if isinstance(member_ids, str):
        member_ids = [member_ids]

    from app.services.auth_service import auth_service
    from app.services.organization_service import organization_service
    # 批量预取成员用户信息（一次 list + 内存分组），避免循环内 get_user_by_id 造成 N+1
    user_map = _batch_user_map(auth_service, [str(m) for m in member_ids])
    result = []
    for mid in member_ids:
        user = user_map.get(str(mid), {})
        m = organization_service.add_member(org_id, str(mid), role="member")
        if m:
            result.append(m)
        # 同步添加到用户组
        group_ids = body.userRoleIds or []
        if isinstance(group_ids, str):
            group_ids = [group_ids]
        for gid in group_ids:
            auth_service.add_group_member(
                group_id=gid,
                user_id=str(mid),
                username=user.get("username", "") if user else "",
                name=user.get("name", "") if user else "",
                email=user.get("email", "") if user else "",
                group_type="ORGANIZATION",
                scope_id=org_id,
            )
    return ok(result)


@router.get("/organization/remove-member")
async def org_remove_member_get(organization_id: str = "", org_id: str = "",
                                source_id: str = "", userId: str = "",
                                memberId: str = "", userIds: Any = ""):
    """组织移除成员（GET query 兼容）。"""
    oid = organization_id or org_id or source_id or ""
    uid = userId or memberId or userIds or ""
    if isinstance(uid, list):
        uid = uid[0] if uid else ""
    if oid and uid:
        from app.services.organization_service import organization_service
        organization_service.remove_member(oid, str(uid))
    return ok()


@router.post("/organization/remove-member")
async def org_remove_member(body: OrgMemberRemoveBody = OrgMemberRemoveBody()):
    """组织移除成员（POST body 兼容）。"""
    oid = body.organizationId or body.orgId or body.sourceId or ""
    uid = body.userId or body.userIds or body.memberId or ""
    if isinstance(uid, list):
        uid = uid[0] if uid else ""
    if oid and uid:
        from app.services.organization_service import organization_service
        organization_service.remove_member(oid, str(uid))
    return ok()


@router.get("/organization/remove-member/{org_id}/{user_id}")
@router.post("/organization/remove-member/{org_id}/{user_id}")
def org_remove_member_path(org_id: str, user_id: str):
    """组织移除成员（路径参数版，前端 deleteMemberReq 调用）。"""
    from app.services.organization_service import organization_service
    organization_service.remove_member(org_id, user_id)
    return ok({"sourceId": org_id, "userId": user_id, "removed": True})


@router.post("/organization/update-member")
async def org_update_member(body: OrgMemberUpdateBody = OrgMemberUpdateBody()):
    """更新组织成员信息（用户组/项目关联）。"""
    org_id = body.organizationId or body.orgId or ""
    member_id = body.memberId or body.userId or body.id or ""
    role = body.role
    user_role_ids = body.userRoleIds or body.roleIds or []
    project_ids = body.projectIds or []
    if isinstance(user_role_ids, str):
        user_role_ids = [user_role_ids]
    if isinstance(project_ids, str):
        project_ids = [project_ids]

    from app.services.auth_service import auth_service
    from app.services.organization_service import organization_service
    from app.services.project_service import project_service

    if org_id and member_id:
        if role:
            organization_service.update_member(org_id, str(member_id), role=role)
        else:
            organization_service.add_member(org_id, str(member_id), role="member")

    # 更新用户组关联
    if member_id and user_role_ids:
        # 先清除该成员当前的所有 org 用户组关系（数据访问经 UserGroupRepo）
        try:
            auth_service.remove_user_org_memberships(str(member_id))
        except Exception:
            pass
        user = auth_service.get_user_by_id(str(member_id))
        for gid in user_role_ids:
            auth_service.add_group_member(
                group_id=gid,
                user_id=str(member_id),
                username=user.get("username", "") if user else "",
                name=user.get("name", "") if user else "",
                email=user.get("email", "") if user else "",
                group_type="ORGANIZATION",
                scope_id=org_id or "organization",
            )

    # 更新项目关联
    if member_id and project_ids:
        # 先移除现有项目关系（避免重复，经 Service 层批量删除）
        try:
            project_service.remove_user_all_projects(str(member_id))
        except Exception:
            pass
        for pid in project_ids:
            if pid:
                project_service.add_member(pid, user_id=str(member_id), role="member")
    return ok()
