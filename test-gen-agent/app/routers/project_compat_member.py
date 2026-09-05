# app/routers/project_compat_member.py
"""project_compat 拆分：项目成员管理 /project/member*（P4 超大文件拆分）。

自 app/routers/project_compat.py 按业务域搬移，纯路由搬移、行为不变，
响应沿用统一 ok()/fail()/_paginate() 与 read_body() 辅助函数。
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Request

from app.auth.dependencies import get_current_user as _auth_get_user
from app.core.response import fail, ok
from app.logging_config import get_logger
from app.models.auth import ProjectMemberBody
from app.models.invitation import InviteCreateBody
from app.services.project_service import project_service

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-project-member"])


"""project_compat 拆分：member 域路由（P4 超大文件拆分）。

自 app/routers/project_compat.py 按域搬移，纯搬移、行为不变。
"""

def _project_member_user_group_options():
    """项目用户组下拉选项（与前端 ProjectUserOption 对齐）。"""
    return [
        {"id": "project-admin", "name": "项目管理员"},
        {"id": "project-member", "name": "项目成员"},
        {"id": "project-readonly", "name": "项目只读成员"},
    ]
def _set_member_user_groups(project_id: str, user_ids, role_ids):
    """为指定项目成员设置用户组。"""

    group_str = ",".join([str(r) for r in role_ids]) if role_ids else ""
    updated = 0
    for uid in user_ids:
        m = project_service.set_member_group(None, project_id, str(uid), group_str)
        if m:
            updated += 1
    return updated

@router.get("/project/member/remove")
def project_member_remove_get(request: Request):
    """项目成员移除（GET兼容）。"""
    # 前端通过 query 参数传递 projectId/userId
    params = dict(request.query_params)
    project_id = params.get("projectId", params.get("project_id", ""))
    user_id = params.get("userId", params.get("user_id", ""))

    # 也兼容从 params 字符串中解析 /projectId/userId
    if not user_id:
        p_str = params.get("params", "")
        if "/" in p_str:
            parts = p_str.split("/")
            if len(parts) == 2:
                project_id = project_id or parts[0]
                user_id = parts[1]

    if project_id and user_id:
        from app.services.project_service import project_service
        project_service.remove_member(project_id, user_id)
    return ok()

@router.post("/project/member/add-role")
def project_member_add_role(request: Request, body: ProjectMemberBody = Body(default=None)):
    """添加成员角色（批量给成员设置用户组）。

    建档模型 ProjectMemberBody（auth 域）：projectId/project_id、
    roleIds、selectIds/userIds/memberIds、selectAll、excludeIds。
    """
    if body is None:
        return ok({"updated": 0})
    project_id = body.resolve_project_id()
    role_ids = body.roleIds or []
    if isinstance(role_ids, str):
        role_ids = [role_ids]
    user_ids = body.selectIds or body.userIds or body.memberIds or []
    if isinstance(user_ids, str):
        user_ids = [user_ids]
    select_all = bool(body.selectAll)
    if select_all and not user_ids:
        # selectAll 场景：将项目内全部成员加入目标用户组
        user_ids = [str(m.get("user_id", "")) for m in project_service.list_members(project_id)]
        exclude_ids = body.excludeIds or []
        user_ids = [u for u in user_ids if u not in [str(e) for e in exclude_ids]]
    if user_ids:
        _set_member_user_groups(project_id, user_ids, role_ids)
    return ok({"updated": len(user_ids)})

@router.get("/project/member/get-role/option")
@router.get("/project/member/get-role/option/{project_id}")
def project_member_get_role_option(project_id: str = ""):
    """获取项目用户组选项。"""
    return ok(_project_member_user_group_options())

@router.post("/project/member/invite")
def project_member_invite(
    request: Request,
    user: Optional[Dict[str, Any]] = Depends(_auth_get_user),
    body: InviteCreateBody = Body(default=None),
):
    """邀请项目成员：真实创建邀请记录并返回注册链接。

    前端 inviteMember 请求体: {inviteEmails:[], userRoleIds:[], organizationId, projectId}
    建档模型 InviteCreateBody（invitation 域）。
    """
    from app.services.invitation_service import invitation_service
    inv = body if body is not None else InviteCreateBody()
    emails = inv.inviteEmails or inv.emails or []
    if isinstance(emails, str):
        emails = [e for e in emails.split(",") if e.strip()]
    if not isinstance(emails, list):
        emails = [emails]
    role_ids = inv.userRoleIds or inv.roleIds or []
    if isinstance(role_ids, str):
        role_ids = [r for r in role_ids.split(",") if r]
    org_id = str(inv.organizationId or inv.orgId or inv.organization_id or "default-org")
    project_id = str(inv.projectId or inv.project_id or inv.project or "")
    creator = (user or {}).get("username") or (user or {}).get("name") or "admin"
    record = invitation_service.create_invite(
        emails, scope="PROJECT", organization_id=org_id,
        project_id=project_id, role_ids=list(role_ids), create_user=creator,
    )
    if not record:
        return fail("邮箱列表为空", code=400)
    return ok({
        "inviteId": record["invite_id"],
        "invitationUrl": f"/#/invite?inviteId={record['invite_id']}",
        "emails": emails,
        "projectId": project_id,
        "organizationId": org_id,
    })

@router.get("/project/member/comment/user-option")
def project_member_comment_user_option(project_id: str = ""):
    """评论用户选项。"""
    return ok([])

@router.post("/project/member/update-member")
def project_member_update_member(request: Request, body: ProjectMemberBody = Body(default=None)):
    """更新项目成员。

    建档模型 ProjectMemberBody（auth 域）：id/memberId + 可写成员字段
    （username/name/email/role/user_group）。extra 字段透传由模型 extra=allow
    承接，仅将请求实际携带字段转发 Service，空体安全返回 ok()。
    """
    member_id = ""
    fields = {}
    if body is not None:
        member_id = body.id or body.memberId or ""
        fields = {k: v for k, v in body.model_dump(exclude_unset=True).items()
                  if k not in ("id", "memberId") and v is not None}
    if member_id:
        project_service.update_member(member_id, fields)
    return ok()

@router.get("/project/get-member/option")
def project_get_member_option(project_id: str = ""):
    """获取项目成员选项。"""
    return ok([])

@router.get("/project/get-member/option/{project_id}")
@router.post("/project/get-member/option/{project_id}")
def project_get_member_option_path(project_id: str, keyword: str = ""):
    """获取项目成员选项（带路径参数）。

    返回项目成员列表（用于高级搜索中的成员过滤下拉选项）。
    前端期望格式：List[{id, name, username, email, ...}]
    """
    members = []
    try:
        members = project_service.list_members(project_id)
    except Exception:
        logger.exception("Failed to list project members for options")

    options = []
    for m in members:
        uid = str(m.get("user_id") or m.get("username") or m.get("id") or "")
        name = m.get("name") or m.get("username") or uid
        uname = m.get("username", "")
        if keyword:
            kw = keyword.lower()
            if kw not in (name or "").lower() and kw not in (uname or "").lower():
                continue
        options.append({
            "id": uid,
            "value": uid,
            "name": name,
            "username": uname,
            "email": m.get("email", ""),
        })

    # 确保至少返回 admin 选项，避免高级搜索无成员可选
    if not options:
        options.append({
            "id": "admin",
            "value": "admin",
            "name": "admin",
            "username": "admin",
            "email": "",
        })
    return ok(options)

@router.get("/project/member/get-member/option/{project_id}")
@router.post("/project/member/get-member/option/{project_id}")
def project_member_get_member_option_path(project_id: str, keyword: str = ""):
    """获取可添加的项目成员候选列表（带路径参数）。"""
    from app.services.auth_service import auth_service
    users = auth_service.list_users(limit=10000)
    try:
        existing = {str(m.get("user_id", "")) for m in project_service.list_members(project_id)}
    except Exception:
        existing = set()
    options = []
    for u in users:
        uid = str(u.get("id", ""))
        if uid in existing:
            continue
        name = u.get("name") or u.get("username", "")
        if keyword and keyword.lower() not in (name or "").lower() and keyword.lower() not in (u.get("username") or "").lower():
            continue
        options.append({
            "id": uid,
            "name": name,
            "username": u.get("username", ""),
            "email": u.get("email", ""),
        })
    return ok(options)

@router.get("/project/member/comment/user-option/{project_id}")
def project_member_comment_user_option_path(project_id: str):
    """获取项目成员评论用户选项（带路径参数）。"""
    return ok([])

@router.get("/project/member/get-member/option")
def project_member_options(projectId: str = ""):
    """获取可添加的项目成员候选列表。"""
    from app.services.auth_service import auth_service
    users = auth_service.list_users(limit=10000)
    options = []
    for u in users:
        options.append({
            "id": u.get("id", ""),
            "name": u.get("name") or u.get("username", ""),
            "username": u.get("username", ""),
            "email": u.get("email", ""),
        })
    return ok(options)
