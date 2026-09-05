# app/auth/router_member.py
"""项目成员管理 API 路由。

自 app/auth/router.py 拆分：承载项目成员 CRUD（list/add/update/remove/batch-remove）
与项目成员数据组装（_build_project_member_item）。
"""

from typing import Optional

from fastapi import APIRouter, Request

from app.core.response import fail, ok
from app.models.auth import ProjectMemberBody, ProjectMemberListBody
from app.services.auth_service import auth_service
from app.services.project_service import project_service

router = APIRouter(tags=["auth-member"])


# ── 项目成员管理 ─────────────────────────────────────────
def _project_user_group_options() -> list:
    """项目用户组选项（与前端 ProjectUserOption 对齐）。"""
    return [
        {"id": "project-admin", "name": "项目管理员"},
        {"id": "project-member", "name": "项目成员"},
        {"id": "project-readonly", "name": "项目只读成员"},
    ]


def _build_project_member_item(member: dict, user_map: dict = None) -> dict:
    """将后端 project_members 行转换为前端 ProjectMemberItem 所需字段。

    user_map 为预取的用户 {user_id: user} 映射，避免逐个 get_user_by_id 造成 N+1。
    """
    user = None
    uid = str(member.get("user_id", "") or "")
    if uid:
        try:
            user = (user_map or {}).get(uid)
            if user is None:
                user = auth_service.get_user_by_id(uid)
        except Exception:
            user = None
    if not user:
        user = {}

    # 用户组：兼容多值（逗号分隔/JSON数组）与单值
    ug = member.get("user_group") or ""
    group_ids = []
    if isinstance(ug, str):
        if ug.startswith("["):
            try:
                import json as _json
                group_ids = [_json.loads(ug)]
                if isinstance(group_ids[0], list):
                    group_ids = group_ids[0]
            except Exception:
                group_ids = [g.strip() for g in ug.split(",") if g.strip()]
        else:
            group_ids = [g.strip() for g in ug.split(",") if g.strip()]
    elif isinstance(ug, list):
        group_ids = ug
    if not group_ids:
        group_ids = ["project-member"]

    options = {g["id"]: g["name"] for g in _project_user_group_options()}
    user_roles = [
        {
            "id": gid,
            "name": options.get(gid, gid),
            "description": "",
            "internal": True,
            "type": "PROJECT",
            "scopeId": member.get("project_id", ""),
            "createTime": 0,
            "updateTime": 0,
            "createUser": "admin",
        }
        for gid in group_ids
    ]
    return {
        "id": member.get("user_id") or member.get("id"),
        "userId": member.get("user_id"),
        "name": member.get("name") or user.get("name") or member.get("username") or user.get("username", ""),
        "email": member.get("email") or user.get("email", ""),
        "phone": user.get("phone", ""),
        "enable": bool(user.get("enable", 1)) if user else True,
        "createTime": int(((user.get("create_time") or member.get("created_at") or 0) or 0) * 1000),
        "updateTime": int(((user.get("update_time") or member.get("updated_at") or 0) or 0) * 1000),
        "language": user.get("language", "zh-CN"),
        "lastOrganizationId": user.get("last_organization_id", ""),
        "lastProjectId": user.get("last_project_id", "") or member.get("project_id", ""),
        "source": user.get("source", ""),
        "createUser": user.get("create_user", "system"),
        "updateUser": user.get("update_user", "system"),
        "deleted": False,
        "userRoles": user_roles,
        "user_group": ug,
    }


@router.get("/project/member/list", operation_id="project_member_list_get")
@router.post("/project/member/list", operation_id="project_member_list_post")
def project_member_list(request: Request, payload: Optional[ProjectMemberListBody] = None):
    """项目成员列表。"""
    if request.method == "POST":
        payload = payload or ProjectMemberListBody()
        project_id = payload.projectId or payload.project_id
        keyword = payload.keyword
        role_ids = (payload.filter or {}).get("roleIds") or []
    else:
        qp = request.query_params
        project_id = qp.get("projectId", qp.get("project_id", ""))
        keyword = qp.get("keyword", "")
        role_ids = []
    members = project_service.list_members(project_id, keyword)
    # 用户组过滤
    if isinstance(role_ids, str):
        role_ids = [role_ids]
    role_ids = [str(r) for r in role_ids]
    if role_ids:
        members = [m for m in members if any(
            g in role_ids for g in (str(m.get("user_group", "")).split(",") if m.get("user_group") else [])
        )]
    # 批量预取成员用户信息（一次 list + 内存分组），避免每个成员 get_user_by_id 造成 N+1
    user_map = {}
    member_uids = {str(m.get("user_id", "")) for m in members if m.get("user_id")}
    if member_uids:
        try:
            for u in auth_service.list_users(limit=10000):
                if str(u.get("id", "")) in member_uids:
                    user_map[str(u.get("id", ""))] = u
        except Exception:
            pass
    items = [_build_project_member_item(m, user_map) for m in members]
    return ok({"list": items, "total": len(items)})


@router.post("/project/member/add")
def project_member_add(request: Request, payload: ProjectMemberBody):
    """添加项目成员。"""
    project_id = payload.projectId or payload.project_id
    member_ids = payload.memberIds or payload.userIds or []
    if isinstance(member_ids, str):
        member_ids = [member_ids]
    if not member_ids:
        member_ids = [payload.userId or payload.user_id]
    role = payload.role or "member"
    role_ids = payload.roleIds or []
    if isinstance(role_ids, str):
        role_ids = [role_ids]
    user_group = ",".join([str(r) for r in role_ids]) if role_ids else (payload.userRoleId or payload.user_group)
    if not project_service.get(project_id):
        # Try to find by name first
        found = project_service.list(search=project_id)
        if not found:
            project_service.create({"name": project_id, "description": "auto-created"})
    added = []
    for uid in member_ids:
        if not uid:
            continue
        member = project_service.add_member(
            project_id=project_id,
            user_id=str(uid),
            username=payload.username,
            name=payload.name,
            email=payload.email,
            role=role,
            user_group=user_group,
        )
        if member:
            added.append(member)
    if not added:
        # 成员可能已存在，视为操作成功
        existing = project_service.list_members(project_id)
        return ok(existing)
    return ok(added)


@router.post("/project/member/update")
def project_member_update(request: Request, payload: ProjectMemberBody):
    """更新项目成员（编辑成员用户组等）。"""
    member_id = payload.memberId or ""
    project_id = payload.projectId or payload.project_id
    user_id = payload.userId or payload.user_id
    # 前端编辑成员用户组：body = {projectId, userId, roleIds}
    role_ids = payload.roleIds or payload.userRoleId or []
    if isinstance(role_ids, str):
        role_ids = [role_ids]
    if role_ids:
        group_str = ",".join([str(r) for r in role_ids])
        member = project_service.set_member_group(member_id, project_id, user_id, group_str)
        if member:
            return ok(member)
    updates = payload.model_dump()
    member = project_service.update_member(member_id, {
        k: updates[k] for k in ("username", "name", "email", "role", "user_group") if k in updates
    })
    if not member:
        return fail("成员不存在", code=404)
    return ok(member)


@router.post("/project/member/remove", operation_id="project_member_remove_post")
def project_member_remove_post(request: Request, payload: ProjectMemberBody):
    """移除项目成员。body: {projectId, userId}"""
    project_id = payload.projectId or payload.project_id
    user_id = payload.userId or payload.user_id
    removed = project_service.remove_member(project_id, user_id)
    return ok(None) if removed else fail("成员不存在", code=404)


@router.get("/project/member/remove/{project_id}/{user_id}")
def project_member_remove(project_id: str, user_id: str):
    """移除项目成员。"""
    removed = project_service.remove_member(project_id, user_id)
    return ok(None) if removed else fail("成员不存在", code=404)


@router.post("/project/member/batch/remove")
def project_member_batch_remove(request: Request, payload: ProjectMemberBody):
    """批量移除项目成员。"""
    project_id = payload.projectId or payload.project_id
    user_ids = payload.selectIds or payload.userIds or payload.memberIds or []
    if isinstance(user_ids, str):
        user_ids = [user_ids]
    select_all = payload.selectAll
    if select_all and not user_ids:
        # selectAll 场景：移除项目内除 excludeIds 外全部成员
        user_ids = [str(m.get("user_id", "")) for m in project_service.list_members(project_id)]
        exclude_ids = payload.excludeIds or []
        user_ids = [u for u in user_ids if u not in [str(e) for e in exclude_ids]]
    removed = 0
    for uid in user_ids:
        if project_service.remove_member(project_id, uid):
            removed += 1
    return ok({"removed": removed})
