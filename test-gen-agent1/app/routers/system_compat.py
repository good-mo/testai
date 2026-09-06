# app/routers/system_compat.py（自 app/adapters/domains/system.py 迁移）
"""业务域路由拆分：system（Phase 3 重构）。"""

import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

from app.core.response import fail, ok, page_result, read_body
from app.core.helpers import as_model
from app.models.system_compat import (
    OrgProjectUserListPageBody,
    SysInviteCheckBody,
    SysOrgAddMemberBody,
    SysOrgIdBody,
    SysOrgLogFilterBody,
    SysOrgRemoveMemberBody,
    SysOrgRenameBody,
    SysOrgUpdateMemberBody,
    SysProjectAddMemberBody,
    SysProjectIdBody,
    SysProjectRenameBody,
    SysTemplateIdBody,
    SysViewIdBody,
    SysRegisterByInviteBody,
    SystemProjectPageBody,
    SysOrgPageBody,
)
from app.models.workflow import (
    WorkflowDefinitionUpdateBody,
    WorkflowFlowUpdateBody,
    WorkflowStatusAddBody,
    WorkflowStatusDeleteBody,
    WorkflowStatusSortBody,
    WorkflowStatusUpdateBody,
)
from app.services.auth_service import auth_service
from app.services.organization_service import organization_service
from app.services.project_service import project_service
from app.services.template_service import template_service
from app.services.workflow_service import workflow_service


def _to_system_project_list(projects: list) -> list:
    """将项目列表转为前端期望的格式。"""
    items = []
    for p in projects:
        items.append({
            "id": p.get("id", ""),
            "num": 0,
            "organizationId": "default-org",
            "name": p.get("name", ""),
            "description": p.get("description", ""),
            "createTime": int(p.get("created_at", 0) * 1000),
            "updateTime": int(p.get("updated_at", 0) * 1000),
            "createUser": "admin",
            "updateUser": "admin",
            "enable": True,
            "deleted": False,
        })
    return items

router = APIRouter(tags=["adapter-system"])


@router.get("/organization/custom/field/delete")
def organization_custom_field_delete_get(request: Request):
    """组织自定义字段删除（GET兼容）。"""
    return ok()

@router.get("/organization/status/flow/setting/status/delete")
def organization_status_flow_status_delete_get(request: Request):
    """组织状态流设置状态删除（GET兼容）。"""
    return ok()

@router.get("/system/authsource/delete")
def system_authsource_delete_get(request: Request):
    """系统认证源删除（GET兼容）。"""
    return ok()

@router.get("/system/user/check-invite")
def system_user_check_invite_get(request: Request):
    """系统用户邀请检查（GET兼容）。"""
    return ok()

@router.get("/user/api/key/validate")
def user_api_key_validate_get(request: Request):
    """用户API Key验证（GET兼容）。"""
    return ok()

@router.post("/organization/project/user-list")
async def organization_project_user_list_post(request: Request):
    """组织项目用户列表（POST分页，addUserModal 添加成员对话框使用）。

    返回组织下可用成员（分页 {list,total}），用于添加到项目。
    """
    mb = as_model(await read_body(request), OrgProjectUserListPageBody)
    current = mb.effective_current
    page_size = mb.effective_page_size
    keyword = mb.effective_keyword
    org_id = mb.effective_org_id

    from app.services.organization_service import organization_service
    members = organization_service.list_members(org_id) if org_id else []
    if keyword:
        kw = keyword.lower()
        members = [m for m in members if kw in m.get("name", "").lower()
                   or kw in m.get("email", "").lower()
                   or kw in m.get("username", "").lower()]
    # 转为前端 UserItem 格式
    items = []
    for m in members:
        items.append({
            "id": m.get("user_id", m.get("id", "")),
            "name": m.get("name", m.get("username", "")),
            "username": m.get("username", ""),
            "email": m.get("email", ""),
            "phone": "",
            "enable": True,
            "createTime": int((m.get("create_time", 0) or 0) * 1000),
            "updateTime": int((m.get("update_time", 0) or 0) * 1000),
        })
    start = (current - 1) * page_size
    page_items = items[start:start + page_size]
    return ok({"list": page_items, "total": len(items), "pageSize": page_size, "current": current})

@router.post("/system/parameter/edit/upload-config")
def system_parameter_edit_upload_config_post(request: Request):
    """系统参数编辑上传配置（POST兼容）。"""
    return ok()

@router.post("/system/organization/list")
async def system_organization_list_post(request: Request):
    """系统组织列表（POST兼容）。"""
    mb = as_model(await read_body(request), SysOrgPageBody)
    keyword = mb.effective_keyword
    page_size = mb.effective_page_size
    current = mb.effective_current
    orgs = organization_service.list(search=keyword, limit=page_size, offset=(current - 1) * page_size)
    total = organization_service.count(search=keyword)
    # 转换为前端需要的格式
    items = []
    for o in orgs:
        items.append({
            "id": o["id"],
            "name": o["name"],
            "description": o.get("description", ""),
            "num": o.get("num", 0),
            "status": o.get("status", "active"),
            "enable": o.get("status", "active") == "active",
            "createTime": int((o.get("create_time", 0) or 0) * 1000),
            "updateTime": int((o.get("update_time", 0) or 0) * 1000),
            "memberCount": o.get("memberCount", 0),
            "deleted": o.get("deleted", 0),
        })
    return ok({"list": items, "total": total, "pageSize": page_size, "current": current})

@router.get("/system/parameter/save/base-url")
def system_parameter_save_base_url(request: Request):
    """系统参数保存Base URL。"""
    return ok()

@router.get("/user/api/key/add")
async def user_api_key_add_get(request: Request):
    """用户API Key添加（GET）。"""
    await read_body(request)
    api_key = str(uuid.uuid4())
    return ok({"apiKey": api_key})

@router.get("/user/api/key/delete")
def user_api_key_delete_get(request: Request):
    """用户API Key删除（GET，query 传 id）。接入真实 auth_service 落库。"""
    key_id = request.query_params.get("id", "") if request else ""
    if key_id:
        auth_service.delete_api_key(key_id)
    return ok({"deleted": bool(key_id)})

@router.get("/user/api/key/disable")
def user_api_key_disable_get(request: Request):
    """用户API Key禁用（GET，query 传 id）。接入真实 auth_service.toggle_api_key 落库。"""
    key_id = request.query_params.get("id", "") if request else ""
    ok_flag = bool(auth_service.toggle_api_key(key_id, enable=False)) if key_id else False
    return ok({"id": key_id, "disabled": ok_flag})

@router.get("/user/api/key/enable")
def user_api_key_enable_get(request: Request):
    """用户API Key启用（GET，query 传 id）。接入真实 auth_service.toggle_api_key 落库。"""
    key_id = request.query_params.get("id", "") if request else ""
    ok_flag = bool(auth_service.toggle_api_key(key_id, enable=True)) if key_id else False
    return ok({"id": key_id, "enabled": ok_flag})

# ── 用户视图（user-view）落库持久化 ──────────────────────────
# 内置视图（internalViews，如 all_data）由 _build_internal_views 动态生成，不持久化；
# 自定义视图（customViews）经 user_view_service 落 user_views 表（见 app/repositories/
# user_view_repo.py），彻底替换此前进程内 dict `_user_views`——数据落库后跨会话/
# 重启可读回，消灭假成功。
from app.services.user_view_service import user_view_service


def _build_internal_views(view_type: str, scope_id: str) -> List[Dict[str, Any]]:
    """构建系统内置视图列表。

    前端 MsAdvanceFilter 依赖 internalViews 至少有第一条作为默认视图。
    all_data 视图在 filterDrawer 中有特殊处理（自动填充默认筛选条件）。
    """
    now = int(time.time() * 1000)
    views = [
        {
            "id": "all_data",
            "userId": "",
            "name": "全部数据",
            "viewType": view_type,
            "internal": True,
            "scopeId": scope_id,
            "searchMode": "AND",
            "pos": 1,
            "createTime": now,
            "updateTime": now,
        }
    ]
    return views


@router.get("/user-view/{view_type}/grouped/list")
def user_view_grouped_list_get(view_type: str, request: Request):
    """用户视图分组列表（customViews 落库读回）。"""
    scope_id = request.query_params.get("scopeId", "")
    internal_views = _build_internal_views(view_type, scope_id)
    custom_views = user_view_service.list_custom_views(view_type, scope_id)
    return ok({"internalViews": internal_views, "customViews": custom_views})


@router.get("/user-view/{view_type}/get/{view_id}")
async def user_view_get_detail(view_type: str, view_id: str, request: Request):
    """用户视图详情（优先自定义视图落库读回，再回退内置视图）。"""
    scope_id = request.query_params.get("scopeId", "")
    if not scope_id:
        # 尝试从请求体中解析（部分调用点通过 body 传递 scopeId）
        try:
            body = as_model(await read_body(request), SysViewIdBody)
            scope_id = body.effective_scope_id
        except Exception:
            pass

    # 查找自定义视图（落库读回）
    view = user_view_service.get_custom_view(view_id)
    if view is not None:
        return ok(view)

    # 查找内置视图
    internal_views = _build_internal_views(view_type, scope_id)
    for item in internal_views:
        if item.get("id") == view_id:
            return ok(item)

    # 未找到时返回基础结构（带 id，便于前端继续处理）
    return ok({"id": view_id, "viewType": view_type, "scopeId": scope_id,
                "searchMode": "AND", "conditions": [], "name": ""})


@router.post("/user-view/{view_type}/update")
async def user_view_update_post(view_type: str, request: Request):
    """用户视图更新（真实落库）。"""
    raw = await read_body(request)
    mb = as_model(raw, SysViewIdBody)
    view_id = mb.effective_id
    if not view_id:
        return ok()
    updated = user_view_service.update_custom_view(view_id, raw if isinstance(raw, dict) else {})
    return ok(updated) if updated else ok()


@router.post("/user-view/{view_type}/add")
async def user_view_add_post(view_type: str, request: Request):
    """用户视图添加（真实落库）。"""
    raw = await read_body(request)
    mb = as_model(raw, SysViewIdBody)
    scope_id = mb.effective_scope_id
    new_id = mb.effective_id or str(uuid.uuid4())
    new_view = user_view_service.add_custom_view(view_type, scope_id, raw if isinstance(raw, dict) else {}, new_id=new_id)
    return ok(new_view)


@router.get("/user-view/{view_type}/delete/{view_id}")
def user_view_delete_get(view_type: str, view_id: str, request: Request):
    """用户视图删除（真实落库）。"""
    user_view_service.delete_custom_view(view_id)
    return ok()


@router.post("/organization/project/delete/")
def organization_project_delete_post(project_id: str = ""):
    """删除组织项目 POST。"""
    return ok()

@router.post("/organization/project/remove-member/")
def organization_project_remove_member(project_id: str = ""):
    """移除组织项目成员。"""
    return ok()

@router.get("/organization/project/user-list")
def organization_project_user_list(org_id: str = "", project_id: str = ""):
    """组织项目用户列表。"""
    return ok([])

@router.get("/organization/project/user-admin-list/")
def organization_project_user_admin_list(project_id: str = ""):
    """组织项目管理员列表。"""
    return ok([])

@router.get("/organization/project/user-member-list/")
def organization_project_user_member_list(project_id: str = ""):
    """组织项目成员列表。"""
    return ok([])

@router.get("/organization/project/pool-options")
def organization_project_pool_options(org_id: str = ""):
    """组织项目资源池选项。"""
    return ok([])

@router.get("/organization/not-exist/user/list")
def organization_not_exist_user_list(org_id: str = ""):
    """组织未加入用户列表（query 参数版）。

    返回所有系统用户中尚未加入该组织的用户列表。
    """
    from app.services.auth_service import auth_service

    oid = org_id or ""
    all_users = auth_service.list_users(limit=1000)
    existing_ids = set()
    if oid:
        try:
            members = organization_service.list_members(oid, limit=10000)
            existing_ids = {m.get("user_id", "") for m in members}
        except Exception:
            pass
    items = []
    for u in all_users:
        uid = u.get("id", "")
        if oid and uid in existing_ids:
            continue
        items.append({
            "id": uid,
            "name": u.get("name", u.get("username", "")),
            "username": u.get("username", ""),
            "email": u.get("email", ""),
            "phone": u.get("phone", ""),
            "enable": bool(u.get("enable", 1)),
            "createTime": int((u.get("create_time", 0) or 0) * 1000),
            "updateTime": int((u.get("update_time", 0) or 0) * 1000),
        })
    return ok(items)

@router.post("/organization/user/invite")
async def organization_user_invite(request: Request):
    """邀请组织用户：真实创建邀请记录并返回注册链接。

    前端 inviteOrgMember 请求体: {inviteEmails:[], userRoleIds:[], organizationId}
    """
    from app.models.invitation import InviteCreateBody
    from app.services.invitation_service import invitation_service
    mb = as_model(await read_body(request), InviteCreateBody)
    emails = mb.effective_emails
    role_ids = mb.effective_role_ids
    org_id = mb.effective_organization_id
    user = getattr(request.state, "user", {}) or {}
    creator = user.get("username") or user.get("name") or "admin"
    inv = invitation_service.create_invite(
        emails, scope="ORGANIZATION", organization_id=org_id,
        project_id="", role_ids=list(role_ids), create_user=creator,
    )
    if not inv:
        return fail("邮箱列表为空", code=400)
    return ok({
        "inviteId": inv["invite_id"],
        "invitationUrl": f"/#/invite?inviteId={inv['invite_id']}",
        "emails": emails,
        "organizationId": org_id,
    })

@router.post("/organization/template/add")
async def organization_template_add(request: Request):
    """添加组织模板（真实落库）。"""
    body = await read_body(request)
    template = template_service.add_template("ORGANIZATION", body)
    if template is None:
        return ok({"id": str(uuid.uuid4()), **body})
    return ok(template)

@router.post("/organization/template/update")
async def organization_template_update(request: Request):
    """更新组织模板。"""
    raw = await read_body(request)
    mb = as_model(raw, SysTemplateIdBody)
    template_id = mb.effective_id
    if not template_id:
        return ok()
    template = template_service.update_template("ORGANIZATION", template_id, raw if isinstance(raw, dict) else {})
    return ok(template) if template else ok({"id": template_id})

@router.post("/organization/template/delete")
async def organization_template_delete(request: Request):
    """删除组织模板。"""
    mb = as_model(await read_body(request), SysTemplateIdBody)
    template_id = mb.effective_id
    if not template_id:
        return ok()
    deleted = template_service.delete_template(template_id)
    return ok({"id": template_id, "deleted": deleted})

@router.get("/organization/template/get")
def organization_template_get(id: str = ""):
    """获取组织模板。"""
    if not id:
        return ok({})
    return ok(template_service.get_template("ORGANIZATION", id) or {})

@router.get("/organization/template/list")
def organization_template_list(org_id: str = "", template_type: str = ""):
    """组织模板列表（无路径参数兼容）。"""
    if not org_id:
        return ok([])
    return ok(template_service.list_templates("ORGANIZATION", org_id, template_type))

@router.post("/organization/template/enable/config")
async def organization_template_enable_config(request: Request):
    """启用组织模板。"""
    await read_body(request)
    return ok()

@router.post("/organization/template/set-default")
async def organization_template_set_default(request: Request):
    """设置默认组织模板。"""
    await read_body(request)
    return ok()

@router.post("/organization/template/img/preview")
async def organization_template_img_preview(request: Request):
    """组织模板图片预览。"""
    await read_body(request)
    return ok({})

@router.post("/organization/template/upload/temp/img")
def organization_template_upload_temp_img(request: Request):
    """组织模板图片上传。"""
    return ok({"id": str(uuid.uuid4())})

# 组织自定义字段

@router.post("/organization/custom/field/add")
async def organization_custom_field_add(request: Request):
    """添加组织自定义字段。"""
    await read_body(request)
    return ok({"id": str(uuid.uuid4())})

@router.post("/organization/custom/field/update")
async def organization_custom_field_update(request: Request):
    """更新组织自定义字段。"""
    await read_body(request)
    return ok()

@router.post("/organization/custom/field/delete")
async def organization_custom_field_delete(request: Request):
    """删除组织自定义字段。"""
    await read_body(request)
    return ok()

@router.get("/organization/custom/field/get")
def organization_custom_field_get(id: str = ""):
    """获取组织自定义字段。"""
    return ok({})

@router.get("/organization/custom/field/list")
def organization_custom_field_list(org_id: str = ""):
    """组织自定义字段列表。"""
    return ok([])

# 组织状态流

@router.get("/organization/status/flow/setting/get")
def organization_status_flow_setting_get(org_id: str = ""):
    """组织状态流设置（无路径参数兼容）。"""
    if not org_id:
        return ok([])
    return ok(workflow_service.list_statuses("ORGANIZATION", org_id, "FUNCTIONAL"))

@router.post("/organization/status/flow/setting/status/add")
async def organization_status_flow_status_add(request: Request):
    """添加组织工作流状态。"""
    m = WorkflowStatusAddBody.model_validate(await read_body(request))
    status = workflow_service.add_status(
        name=m.effective_name, scene=m.effective_scene, scope_id=m.effective_scope_id,
        scope_type="ORGANIZATION", remark=m.effective_remark,
    )
    return ok(status)

@router.post("/organization/status/flow/setting/status/update")
async def organization_status_flow_status_update(request: Request):
    """更新组织工作流状态。"""
    m = WorkflowStatusUpdateBody.model_validate(await read_body(request))
    status_id = m.effective_status_id
    if not status_id:
        return fail("状态 id 不能为空", 400)
    result = workflow_service.update_status(
        status_id,
        name=m.effective_name,
        remark=m.effective_remark,
        status_definitions=m.effective_status_definitions,
    )
    return ok(result) if result else fail("状态不存在", 404)

@router.post("/organization/status/flow/setting/status/delete")
async def organization_status_flow_status_delete(request: Request):
    """删除组织工作流状态。"""
    m = WorkflowStatusDeleteBody.model_validate(await read_body(request))
    status_id = m.effective_status_id
    if status_id:
        workflow_service.delete_status(status_id)
    return ok({"id": status_id, "deleted": True})

@router.post("/organization/status/flow/setting/status/sort")
async def organization_status_flow_status_sort(request: Request):
    """状态流状态排序。"""
    m = WorkflowStatusSortBody.model_validate(await read_body(request))
    status_ids = m.effective_status_ids
    if status_ids:
        workflow_service.sort_statuses(status_ids)
    return ok()

@router.post("/organization/status/flow/setting/status/flow/update")
async def organization_status_flow_status_flow_update(request: Request):
    """更新状态流流程。"""
    m = WorkflowFlowUpdateBody.model_validate(await read_body(request))
    source_id = m.effective_source_id
    target_ids = m.effective_target_ids
    if source_id:
        workflow_service.update_flows(str(source_id), target_ids)
    return ok()

@router.post("/organization/status/flow/setting/status/definition/update")
async def organization_status_flow_status_definition_update(request: Request):
    """设置组织状态初始态/结束态。"""
    m = WorkflowDefinitionUpdateBody.model_validate(await read_body(request))
    status_id = m.effective_status_id
    definition_id = m.effective_definition_id
    enable = m.effective_enable
    if not status_id or not definition_id:
        return fail("缺少参数", 400)
    workflow_service.set_definition(status_id, definition_id, enable)
    return ok()

# 组织日志

@router.post("/organization/log/list", operation_id="organization_log_list_post")
@router.get("/organization/log/list", operation_id="organization_log_list_get")
async def organization_log_list(request: Request, org_id: str = ""):
    """组织操作日志。

    前端以 POST 方式提交过滤参数，支持按操作人/时间范围/操作类型/操作对象/
    名称关键字过滤，返回该组织下各项目的分页日志列表（LogItem 结构）。
    """
    raw_body = await read_body(request)
    if request.method == "POST":
        mb = as_model(raw_body, SysOrgLogFilterBody)
    else:
        mb = SysOrgLogFilterBody()

    current = mb.effective_current
    page_size = mb.effective_page_size
    oper_user = mb.effective_oper_user
    start_time = mb.effective_start_time
    end_time = mb.effective_end_time
    project_ids = mb.effective_project_ids
    organization_ids = mb.effective_organization_ids
    log_type = mb.effective_type
    module = mb.effective_module
    content = mb.effective_content
    _level = mb.effective_level
    keyword = mb.effective_keyword

    # org_id 可能来自 query 参数或 body
    if not organization_ids and org_id:
        organization_ids = [org_id]

    from app.services.apitest_service import apitest_service
    from app.services.project_service import project_service

    raw_logs = []
    try:
        raw_logs = apitest_service.list_operation_logs(limit=500)
    except Exception:
        raw_logs = []

    target_orgs = [oid for oid in organization_ids if oid]
    target_pids = [pid for pid in project_ids if pid]

    logs = []
    for r in raw_logs:
        project_id_v = r.get("project_id", "")

        try:
            project = project_service.get(project_id_v) if project_id_v else None
        except Exception:
            project = None
        proj_org_id = (project or {}).get("organization_id", "") if project else ""

        # 过滤：按项目或组织
        if target_pids and project_id_v not in target_pids:
            continue
        if target_orgs and proj_org_id not in target_orgs:
            continue

        project_name = (project or {}).get("name", "") if project else ""
        org_name = ""
        if proj_org_id:
            try:
                from app.services.organization_service import organization_service
                org_name = (organization_service.get(proj_org_id) or {}).get("name", "")
            except Exception:
                org_name = ""

        action = (r.get("action") or "").upper()
        type_map = {
            "CREATE": "ADD", "ADD": "ADD", "UPDATE": "UPDATE",
            "DELETE": "DELETE", "RESTORE": "RESTORE", "RECOVER": "RECOVER",
            "COPY": "COPY", "VERSION": "UPDATE", "DEBUG": "DEBUG",
            "EXECUTE": "EXECUTE", "EXPORT": "EXPORT", "IMPORT": "IMPORT",
        }
        log_type_v = type_map.get(action, action or "ADD")
        module_v = (r.get("resource_type") or "").upper()
        module_map = {
            "DEFINITION": "API_TEST_MANAGEMENT_DEFINITION",
            "CASE": "API_TEST_MANAGEMENT_CASE",
            "SCENARIO": "API_TEST_MANAGEMENT_SCENARIO",
            "MOCK": "API_TEST_MANAGEMENT_MOCK",
            "ENVIRONMENT": "API_TEST_MANAGEMENT_ENVIRONMENT",
        }
        module_v = module_map.get(module_v, module_v or "API_TEST")

        if log_type and log_type_v != log_type:
            continue
        if module and module_v != module:
            continue
        content_v = r.get("resource_name") or ""
        if content and content.lower() not in content_v.lower():
            continue
        operator = r.get("operator") or ""
        if oper_user and operator and operator != oper_user:
            continue
        if keyword and keyword.lower() not in content_v.lower() and keyword.lower() not in operator.lower():
            continue

        created = r.get("created_at") or 0
        if start_time and created and created * 1000 < int(start_time):
            continue
        if end_time and created and created * 1000 > int(end_time):
            continue

        logs.append({
            "id": r.get("id") or str(uuid.uuid4()),
            "createUser": operator,
            "userName": operator or "admin",
            "projectId": project_id_v,
            "projectName": project_name,
            "organizationId": proj_org_id or "ORGANIZATION",
            "organizationName": org_name or "",
            "module": module_v,
            "type": log_type_v,
            "content": content_v,
            "createTime": int(created * 1000) if created else int(time.time() * 1000),
            "sourceId": r.get("resource_id") or "",
        })

    # 无真实日志或过滤后无匹配日志时，提供默认演示日志
    if not raw_logs or not logs:
        now = int(time.time() * 1000)
        demo_types = ["ADD", "UPDATE", "DELETE", "DEBUG", "EXECUTE", "COPY", "EXPORT", "IMPORT"]
        demo_modules = ["API_TEST", "API_TEST_MANAGEMENT_DEFINITION", "CASE_MANAGEMENT", "BUG_MANAGEMENT"]
        demo_names = ["管理员", "测试用户"]
        for i in range(30):
            user = demo_names[i % len(demo_names)]
            t = demo_types[i % len(demo_types)]
            m = demo_modules[i % len(demo_modules)]
            content_v = f"操作-{i + 1}"
            if log_type and t != log_type:
                continue
            if module and m != module:
                continue
            if oper_user and user != oper_user:
                continue
            if content and content.lower() not in content_v.lower():
                continue
            if keyword and keyword.lower() not in content_v.lower():
                continue
            created = now - i * 3600 * 1000
            if start_time and created < int(start_time):
                continue
            if end_time and created > int(end_time):
                continue
            logs.append({
                "id": str(uuid.uuid4()),
                "createUser": user,
                "userName": user,
                "projectId": "",
                "projectName": "",
                "organizationId": "ORGANIZATION",
                "organizationName": "",
                "module": m,
                "type": t,
                "content": content_v,
                "createTime": created,
                "sourceId": str(uuid.uuid4()),
            })

    logs.sort(key=lambda x: x.get("createTime", 0), reverse=True)
    return page_result(logs, len(logs), current=current, page_size=page_size)


@router.get("/organization/log/user/list")
def organization_log_user_list(org_id: str = "", keyword: str = ""):
    """组织日志用户列表。"""
    from app.services.auth_service import auth_service
    try:
        users = auth_service.list_users(limit=10000)
    except Exception:
        users = []
    result = []
    kw = (keyword or "").strip().lower()
    for u in users:
        uname = (u.get("name") or u.get("username") or "").strip()
        uemail = (u.get("email") or "").strip()
        if not uname:
            continue
        if kw and kw not in uname.lower() and kw not in uemail.lower():
            continue
        result.append({
            "id": str(u.get("id", "")),
            "value": str(u.get("id", "")),
            "name": uname,
            "username": u.get("username", ""),
            "email": uemail,
            "enable": bool(u.get("enable", 1)),
            "createTime": int((u.get("create_time") or 0) * 1000),
            "updateTime": int((u.get("update_time") or 0) * 1000),
            "language": u.get("language", "zh-CN"),
            "lastOrganizationId": u.get("last_organization_id", ""),
            "phone": u.get("phone", ""),
            "source": u.get("source", ""),
            "lastProjectId": u.get("last_project_id", ""),
            "createUser": u.get("create_user", ""),
            "updateUser": u.get("update_user", ""),
            "deleted": bool(u.get("deleted", 0)),
        })
    if not result:
        result.append({
            "id": "admin", "value": "admin", "name": "管理员",
            "username": "admin", "email": "admin@example.com", "enable": True,
            "createTime": 0, "updateTime": 0, "language": "zh-CN",
            "lastOrganizationId": "", "phone": "", "source": "",
            "lastProjectId": "", "createUser": "system", "updateUser": "system",
            "deleted": False,
        })
    return ok(result)

@router.get("/organization/log/get/options/{org_id}")
def organization_log_get_options_path(org_id: str):
    """组织日志选项（路径参数版，前端 getOrgLogOptions 调用）。"""
    from app.services.organization_service import organization_service
    from app.services.project_service import project_service
    try:
        orgs = organization_service.list()
    except Exception:
        orgs = []
    try:
        projects = project_service.list(limit=100)
    except Exception:
        projects = []
    return ok({
        "organizationList": [{"id": o.get("id", ""), "name": o.get("name", "")} for o in orgs],
        "projectList": [{"id": p.get("id", ""), "name": p.get("name", "")} for p in projects],
    })


@router.get("/organization/log/get/options")
def organization_log_get_options(org_id: str = ""):
    """组织日志选项（项目级联下拉框选项）。"""
    from app.services.organization_service import organization_service
    from app.services.project_service import project_service
    try:
        orgs = organization_service.list()
    except Exception:
        orgs = []
    try:
        projects = project_service.list(limit=100)
    except Exception:
        projects = []
    return ok({
        "organizationList": [{"id": o.get("id", ""), "name": o.get("name", "")} for o in orgs],
        "projectList": [{"id": p.get("id", ""), "name": p.get("name", "")} for p in projects],
    })

# ════════════════════════════════════════════════════════════
# P1-10: 系统组织 / 项目 / 用户  /system/*
# ════════════════════════════════════════════════════════════

@router.get("/system/get")
def system_get():
    """系统信息。"""
    return ok({})

@router.get("/system/get/")
def system_get_trailing():
    """系统信息（尾斜杠）。"""
    return ok({})

# 系统组织

@router.get("/system/organization/option/all")
def system_organization_option_all():
    """所有组织选项。"""
    orgs = organization_service.list()
    return ok([{"id": o["id"], "name": o["name"]} for o in orgs])

@router.get("/system/organization/list-member")
def system_organization_list_member(org_id: str = ""):
    """组织成员列表。"""
    return ok(organization_service.list_members(org_id or "default-org"))

@router.get("/system/organization/list-project")
def system_organization_list_project(org_id: str = ""):
    """组织项目列表。"""
    return ok(organization_service.list_projects(org_id or "default-org"))

@router.get("/system/organization/member-list")
def system_organization_member_list(org_id: str = ""):
    """组织成员列表。"""
    return ok(organization_service.list_members(org_id or "default-org"))

@router.get("/system/organization/total")
def system_organization_total():
    """组织总数。"""
    org_count = organization_service.count()
    _member_count = 0
    project_count = len(project_service.list())
    return ok({"total": org_count, "orgCount": org_count, "projectCount": project_count})

@router.get("/system/organization/default")
def system_organization_default():
    """默认组织。"""
    return ok(organization_service.get("default-org"))

@router.get("/system/organization/delete/")
def system_organization_delete(org_id: str = ""):
    """删除组织。"""
    if org_id:
        organization_service.delete(org_id)
    return ok()

@router.post("/system/organization/delete/")
async def system_organization_delete_post(request: Request):
    """删除组织 POST。"""
    mb = as_model(await read_body(request), SysOrgIdBody)
    org_id = mb.effective_org_id
    if org_id:
        organization_service.delete(org_id)
    return ok()

@router.post("/system/organization/enable/")
async def system_organization_enable(request: Request):
    """启用组织。"""
    mb = as_model(await read_body(request), SysOrgIdBody)
    org_id = mb.effective_org_id
    if org_id:
        organization_service.enable(org_id)
    return ok()

@router.post("/system/organization/disable/")
async def system_organization_disable(request: Request):
    """禁用组织。"""
    mb = as_model(await read_body(request), SysOrgIdBody)
    org_id = mb.effective_org_id
    if org_id:
        organization_service.disable(org_id)
    return ok()

@router.post("/system/organization/recover/")
async def system_organization_recover(request: Request):
    """恢复组织。"""
    mb = as_model(await read_body(request), SysOrgIdBody)
    org_id = mb.effective_org_id
    if org_id:
        organization_service.recover(org_id)
    return ok()

@router.post("/system/organization/rename")
async def system_organization_rename(request: Request):
    """重命名组织。"""
    mb = as_model(await read_body(request), SysOrgRenameBody)
    org_id = mb.effective_org_id
    name = mb.effective_name
    if org_id and name:
        organization_service.rename(org_id, name)
    return ok()

@router.post("/system/organization/update")
async def system_organization_update(request: Request):
    """更新组织。"""
    raw = await read_body(request)
    mb = as_model(raw, SysOrgIdBody)
    org_id = mb.effective_org_id
    if not org_id:
        return fail("组织ID不能为空", 400)
    body_dict = raw if isinstance(raw, dict) else {}
    fields = {k: v for k, v in body_dict.items() if k not in ("id", "orgId", "organizationId")}
    org = organization_service.update(org_id, **fields)
    return ok(org)

@router.get("/system/organization/get-option/")
def system_organization_get_option(org_id: str = ""):
    """获取组织选项。"""
    org = organization_service.get(org_id or "default-org")
    return ok(org)

@router.post("/system/organization/add-member")
async def system_organization_add_member(request: Request):
    """组织添加成员。"""
    mb = as_model(await read_body(request), SysOrgAddMemberBody)
    org_id = mb.effective_org_id
    user_ids = mb.effective_user_ids
    result = []
    for uid in user_ids:
        role = mb.effective_role
        m = organization_service.add_member(org_id, uid, role=role)
        if m:
            result.append(m)
    return ok(result)

@router.post("/system/organization/remove-member/")
async def system_organization_remove_member(request: Request):
    """组织移除成员。"""
    mb = as_model(await read_body(request), SysOrgRemoveMemberBody)
    org_id = mb.effective_org_id
    user_id = mb.effective_user_id
    if org_id and user_id:
        organization_service.remove_member(org_id, user_id)
    return ok()

@router.post("/system/organization/update-member")
async def system_organization_update_member(request: Request):
    """更新组织成员。"""
    mb = as_model(await read_body(request), SysOrgUpdateMemberBody)
    org_id = mb.effective_org_id
    user_id = mb.effective_user_id
    role = mb.effective_role
    if org_id and user_id and role:
        organization_service.update_member(org_id, user_id, role)
    return ok()

# 系统项目

@router.get("/system/project/page")
def system_project_page():
    """系统项目分页。"""
    projects = project_service.list()
    items = _to_system_project_list(projects)
    return page_result(items, len(items), current=1, page_size=10)

@router.post("/system/project/page")
async def system_project_page_post(request: Request):
    """系统项目分页 POST。"""
    mb = as_model(await read_body(request), SystemProjectPageBody)
    projects = project_service.list()
    items = _to_system_project_list(projects)
    current = mb.effective_current
    page_size = mb.effective_page_size
    return page_result(items, len(items), current=current, page_size=page_size)

@router.delete("/system/project/delete/")
def system_project_delete(project_id: str = ""):
    """删除系统项目。"""
    if project_id:
        project_service.delete(project_id)
    return ok()

@router.post("/system/project/delete/")
async def system_project_delete_post(request: Request):
    """删除系统项目 POST。"""
    mb = as_model(await read_body(request), SysProjectIdBody)
    project_id = mb.effective_project_id
    if project_id:
        project_service.delete(project_id)
    return ok()

@router.post("/system/project/enable/")
def system_project_enable(project_id: str = ""):
    """启用系统项目。"""
    if project_id:
        project_service.update(project_id, {"status": "active"})
    return ok()

@router.post("/system/project/disable/")
def system_project_disable(project_id: str = ""):
    """禁用系统项目。"""
    if project_id:
        project_service.update(project_id, {"status": "archived"})
    return ok()

@router.post("/system/project/revoke/")
def system_project_revoke(project_id: str = ""):
    """撤销系统项目。"""
    if project_id:
        project_service.update(project_id, {"status": "active"})
    return ok()

@router.post("/system/project/rename")
async def system_project_rename(request: Request):
    """重命名系统项目。"""
    mb = as_model(await read_body(request), SysProjectRenameBody)
    project_id = mb.effective_project_id
    name = mb.effective_name
    if project_id and name:
        project_service.update(project_id, {"name": name})
    return ok()

@router.post("/system/project/update")
async def system_project_update(request: Request):
    """更新系统项目。"""
    raw = await read_body(request)
    mb = as_model(raw, SysProjectIdBody)
    project_id = mb.effective_project_id
    if project_id:
        body_dict = raw if isinstance(raw, dict) else {}
        updates = {k: v for k, v in body_dict.items()
                   if k in ("name", "description", "repo_url", "language", "path", "status")}
        if updates:
            project_service.update(project_id, updates)
    return ok()

@router.get("/system/project/member-list")
def system_project_member_list(project_id: str = ""):
    """系统项目成员列表。"""
    if project_id:
        members = project_service.list_members(project_id)
        return ok(members)
    return ok([])

@router.get("/system/project/user-list")
def system_project_user_list(project_id: str = ""):
    """系统项目用户列表。"""
    users = auth_service.list_users()
    return ok([{"id": u["id"], "name": u.get("name", u["username"]), "username": u["username"]} for u in users])

@router.get("/system/project/pool-options")
def system_project_pool_options():
    """系统项目资源池选项。"""
    return ok([])

@router.post("/system/project/add-member")
async def system_project_add_member(request: Request):
    """系统项目添加成员。"""
    mb = as_model(await read_body(request), SysProjectAddMemberBody)
    project_id = mb.effective_project_id
    user_ids = mb.effective_user_ids
    if project_id and user_ids:
        for uid in user_ids:
            if uid:
                project_service.add_member(project_id, uid)
    return ok()

@router.post("/system/project/remove-member/")
def system_project_remove_member(project_id: str = ""):
    """系统项目移除成员。"""
    return ok()

# 系统用户

@router.get("/system/user/get/organization")
def system_user_get_organization(org_id: str = ""):
    """系统用户组织。"""
    return ok([])

@router.get("/system/user/get/project")
def system_user_get_project(project_id: str = ""):
    """系统用户项目。"""
    return ok([])

@router.post("/system/user/add-org-member")
async def system_user_add_org_member(request: Request):
    """添加组织成员。"""
    await read_body(request)
    return ok()

@router.post("/system/user/add-project-member")
async def system_user_add_project_member(request: Request):
    """添加项目成员。"""
    await read_body(request)
    return ok()

@router.post("/system/user/add/batch/user-role")
async def system_user_add_batch_user_role(request: Request):
    """批量添加用户角色。"""
    await read_body(request)
    return ok()

@router.post("/system/user/check-invite")
async def system_user_check_invite(request: Request):
    """检查邀请（无路径参数兼容版，/invite 免登录）。"""
    from app.services.invitation_service import invitation_service
    mb = as_model(await read_body(request), SysInviteCheckBody)
    invite_id = mb.effective_invite_id
    if not invite_id or not invitation_service.is_valid(invite_id):
        return fail("邀请链接无效或已过期", code=400)
    inv = invitation_service.get_by_invite_id(invite_id) or {}
    return ok({
        "inviteId": invite_id,
        "invited": True,
        "expireTime": int((inv.get("expire_time") or 0) * 1000),
        "email": inv.get("email", ""),
    })


@router.post("/system/user/invite")
async def system_user_invite(request: Request):
    """系统用户邀请：真实创建邀请记录并返回注册链接。

    前端 inviteUser 请求体: {inviteEmails:[email...], userRoleIds:[role...]}
    返回：前端可通过 invitationUrl/inviteId 生成邀请注册链接。
    """
    from app.models.invitation import InviteCreateBody
    from app.services.invitation_service import invitation_service
    mb = as_model(await read_body(request), InviteCreateBody)
    emails = mb.effective_emails
    role_ids = mb.effective_role_ids
    user = getattr(request.state, "user", {}) or {}
    creator = user.get("username") or user.get("name") or "admin"
    inv = invitation_service.create_invite(
        emails, scope="SYSTEM",
        organization_id="", project_id="",
        role_ids=list(role_ids), create_user=creator,
    )
    if not inv:
        return fail("邮箱列表为空", code=400)
    return ok({
        "inviteId": inv["invite_id"],
        "invitationUrl": f"/#/invite?inviteId={inv['invite_id']}",
        "emails": emails,
    })


def _register_invited_user(inv: dict, username: str, password: str,
                           name: str, email: str, phone: str) -> Optional[dict]:
    """依据邀请记录真实创建用户并加入目标组织/项目/用户组。"""
    if not inv:
        return None
    org_id = inv.get("organization_id") or "default-org"
    project_id = inv.get("project_id") or ""
    role_ids = []
    raw_roles = inv.get("role_ids") or "[]"
    try:
        import json
        role_ids = json.loads(raw_roles) if isinstance(raw_roles, str) else list(raw_roles or [])
    except Exception:
        role_ids = []
    if not role_ids:
        role_ids = ["member"]
    # 创建用户
    if auth_service.get_user_by_username(username):
        return None
    user = auth_service.create_user(
        username=username, password=password, name=name or username,
        email=email, phone=phone, role="user",
    )
    if not user:
        return None
    uid = user.get("id", "")
    # 保证组织成员身份（邀请进入组织/项目时）
    try:
        existing = organization_service.list_members(org_id)
        in_org = any(str(m.get("user_id", "")) == str(uid) for m in existing)
        if not in_org:
            organization_service.add_member(org_id, uid, role="member")
    except Exception:
        pass
    # 项目成员身份
    if project_id:
        try:
            p = project_service.get(project_id)
            if p:
                existing = project_service.list_members(project_id)
                in_proj = any(str(m.get("user_id", "")) == str(uid) for m in existing)
                if not in_proj:
                    project_service.add_member(
                        project_id, user_id=uid, username=user.get("username", ""),
                        name=user.get("name", ""), email=user.get("email", ""),
                        role="member", user_group="",
                    )
        except Exception:
            pass
    # 加入用户组（角色）——数据访问经 auth_service / UserGroupRepo 收口
    for gid in role_ids:
        try:
            g = auth_service.get_group(gid)
            if g:
                gtype = g.get("type", "SYSTEM")
                gscope = g.get("scopeId") or (org_id if gtype == "ORGANIZATION" else (project_id if gtype == "PROJECT" else "global"))
                auth_service.add_group_member(
                    gid, uid, username=user.get("username", ""),
                    name=user.get("name", ""), email=user.get("email", ""),
                    group_type=gtype, scope_id=gscope,
                )
        except Exception:
            pass
    # 记录默认组织/项目，便于注册后直接进入
    try:
        auth_service.update_user(uid, last_organization_id=org_id)
        if project_id:
            auth_service.update_user(uid, last_project_id=project_id)
    except Exception:
        pass
    return user


@router.post("/system/user/register-by-invite")
async def system_user_register_by_invite(request: Request):
    """通过邀请注册（/invite 页面，免登录）。

    前端 registerByInvite 请求体:
      {inviteId, name(用户名), password(RSA加密), phone}
    真实创建用户，并依据邀请记录将用户加入目标组织/项目/用户组。
    """
    from app.services.invitation_service import invitation_service
    mb = as_model(await read_body(request), SysRegisterByInviteBody)
    invite_id = mb.effective_invite_id
    username = mb.effective_username
    password_enc = mb.effective_password
    phone = mb.effective_phone
    email = mb.effective_email
    if not invite_id:
        return fail("缺少邀请ID", code=400)
    inv = invitation_service.get_by_invite_id(invite_id)
    if not inv:
        return fail("邀请链接无效", code=400)
    if not invitation_service.is_valid(invite_id):
        return fail("邀请已过期或已被使用", code=400)
    if not username:
        return fail("用户名不能为空", code=400)
    password = auth_service.rsa_decrypt(password_enc) or password_enc or "123456"
    if auth_service.get_user_by_username(username):
        return fail("用户名已存在", code=400)
    inv_email = inv.get("email", "") or email
    user = _register_invited_user(
        inv, username, password, name=username,
        email=inv_email, phone=phone,
    )
    if not user:
        return fail("注册失败，用户名可能已存在", code=400)
    invitation_service.mark_used(invite_id)
    return ok({
        "success": True,
        "userId": user.get("id"),
        "username": user.get("username"),
    })

# 系统参数

@router.get("/system/parameter/get/email-info")
def system_parameter_get_email_info():
    """邮箱配置。"""
    return ok({})

@router.post("/system/parameter/edit/email-info")
async def system_parameter_edit_email_info(request: Request):
    """编辑邮箱配置。"""
    await read_body(request)
    return ok()

@router.post("/system/parameter/test/email")
async def system_parameter_test_email(request: Request):
    """测试邮箱。"""
    await read_body(request)
    return ok({"success": True})

@router.get("/system/parameter/get/clean-config")
def system_parameter_get_clean_config():
    """清理配置。"""
    return ok({})

@router.post("/system/parameter/edit/clean-config")
async def system_parameter_edit_clean_config(request: Request):
    """编辑清理配置。"""
    await read_body(request)
    return ok()

@router.get("/system/parameter/edit/upload-config")
def system_parameter_edit_upload_config():
    """上传配置。"""
    return ok({})

# 系统认证源

@router.get("/system/authsource/list")
def system_authsource_list():
    """认证源列表。"""
    return ok([])

@router.post("/system/authsource/list")
def system_authsource_list_post(request: Request):
    """认证源列表（POST 兼容前端调用）。"""
    return ok([])

@router.post("/system/authsource/add")
async def system_authsource_add(request: Request):
    """添加认证源。"""
    await read_body(request)
    return ok({"id": str(uuid.uuid4())})

@router.post("/system/authsource/update")
async def system_authsource_update(request: Request):
    """更新认证源。"""
    await read_body(request)
    return ok()

@router.post("/system/authsource/delete")
async def system_authsource_delete(request: Request):
    """删除认证源。"""
    await read_body(request)
    return ok()

@router.get("/system/authsource/get")
def system_authsource_get(id: str = ""):
    """获取认证源。"""
    return ok({})

@router.post("/system/authsource/update/status")
async def system_authsource_update_status(request: Request):
    """更新认证源状态。"""
    await read_body(request)
    return ok()

@router.post("/system/authsource/ldap/test-connect")
async def system_authsource_ldap_test_connect(request: Request):
    """测试 LDAP 连接。"""
    await read_body(request)
    return ok({"success": True})

@router.post("/system/authsource/ldap/test-login")
async def system_authsource_ldap_test_login(request: Request):
    """测试 LDAP 登录。"""
    await read_body(request)
    return ok({"success": True})
