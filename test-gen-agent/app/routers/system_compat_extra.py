# app/routers/system_compat_extra.py
"""system_compat 拆分：系统杂项补充段（路径参数兼容等）。

自 app/routers/system_compat.py 按业务段拆分（P4 超大文件拆分批次）。
路由定义与原文件顺序一致，纯搬移、行为不变。
"""

from typing import Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.response import ok, page_result, read_body
from app.models.workflow import WorkflowStatusSortBody
from app.services.auth_service import auth_service
from app.services.organization_service import organization_service
from app.services.project_service import project_service
from app.services.template_service import template_service
from app.services.workflow_service import workflow_service

router = APIRouter(tags=["adapter-system-extra"])


# ════════════════════════════════════════════════════════════
# P1-12: 资源池  /test/resource/pool/*
# ════════════════════════════════════════════════════════════

# 系统任务中心

# ════════════════════════════════════════════════════════════
# P2-1: 插件管理  /plugin/*
# ════════════════════════════════════════════════════════════

@router.post("/organization/template/disable")
async def organization_template_disable(request: Request):
    """禁用组织模板。"""
    await read_body(request)
    return ok()

@router.get("/organization/custom/field/list/{organization_id}/{scene}")
@router.post("/organization/custom/field/list/{organization_id}/{scene}")
def org_custom_field_list_path(organization_id: str, scene: str = "FUNCTIONAL"):
    """获取组织自定义字段列表（带路径参数）。

    前端调用: /organization/custom/field/list/{scopedId}/{scene}。
    """
    return ok([])

@router.get("/organization/status/flow/setting/status/sort/{organization_id}/{status_id}")
@router.post("/organization/status/flow/setting/status/sort/{organization_id}/{status_id}")
async def org_status_flow_sort_path(organization_id: str, status_id: str, request: Request):
    """组织状态流排序（带路径参数）。

    前端调用: POST /organization/status/flow/setting/status/sort/{scopedId}/{scene}，
    body 为排序后的状态 ID 数组。
    """
    m = WorkflowStatusSortBody.model_validate(await read_body(request))
    status_ids = [d for d in m.effective_status_ids if d]
    if status_ids:
        workflow_service.sort_statuses(status_ids)
    return ok({"organization_id": organization_id, "scene": status_id, "sorted": True})

@router.get("/organization/template/delete/{template_id}")
@router.post("/organization/template/delete/{template_id}")
def org_template_delete_path(template_id: str):
    """删除组织模板（带路径参数）。

    前端调用点: deleteOrdTemplate -> /organization/template/delete/{id}。
    """
    deleted = template_service.delete_template(template_id)
    return ok({"id": template_id, "deleted": deleted})

@router.get("/organization/template/disable/{template_id}/{organization_id}")
@router.post("/organization/template/disable/{template_id}/{organization_id}")
def org_template_disable_path(template_id: str, organization_id: str):
    """禁用组织模板（带路径参数）。"""
    return ok({"id": template_id, "organization_id": organization_id, "disabled": True})

@router.get("/organization/template/get/{template_id}")
@router.post("/organization/template/get/{template_id}")
def org_template_get_path(template_id: str):
    """获取组织模板（带路径参数）。

    前端调用点: getOrganizeTemplateInfo -> /organization/template/get/{id}。
    """
    return ok(template_service.get_template("ORGANIZATION", template_id) or {})

@router.get("/organization/template/list/{organization_id}/{scene}")
@router.post("/organization/template/list/{organization_id}/{scene}")
def org_template_list_path(organization_id: str, scene: str):
    """获取组织模板列表（带路径参数）。

    前端调用点: getOrganizeTemplateList -> /organization/template/list/{organizationId}/{scene}，
    scene 为 FUNCTIONAL/BUG 等场景，返回模板数组。
    """
    return ok(template_service.list_templates("ORGANIZATION", organization_id, scene))

# ════════════════════════════════════════════════════════════
# 个人信息
# ════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════
# 测试计划
# ════════════════════════════════════════════════════════════

@router.get("/user/platform/validate/{platform}/{user_id}")
@router.post("/user/platform/validate/{platform}/{user_id}")
def user_platform_validate_path(platform: str, user_id: str):
    """验证用户平台（带路径参数）。"""
    return ok({"platform": platform, "user_id": user_id})

# ════════════════════════════════════════════════════════════
# 测试计划报告模块（修复缺失 API）
# ════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════
# 测试计划组列表（修复缺失 API）
# ════════════════════════════════════════════════════════════

@router.post("/organization/project/member-list")
async def api_org_project_member_list_post(request: Request):
    """组织项目成员列表（POST 兼容前端调用）。"""
    body = await read_body(request)
    project_id = body.get("projectId") or body.get("id") or ""
    members = project_service.list_members(project_id) if project_id else []
    return page_result(members, len(members), current=body.get("current", 1), page_size=body.get("pageSize", 10))

@router.post("/organization/project/pool-options")
async def api_org_project_pool_options_post(request: Request):
    """组织项目资源池选项（POST 兼容前端调用）。"""
    await read_body(request)
    return ok([])

@router.post("/system/organization/list-project")
async def api_system_org_list_project_post(request: Request):
    """系统组织项目列表（POST 兼容前端调用）。"""
    body = await read_body(request)
    org_id = body.get("organizationId") or body.get("orgId") or ""
    projects = organization_service.list_projects(org_id) if org_id else []
    return page_result(projects, len(projects), current=body.get("current", 1), page_size=body.get("pageSize", 10))

@router.post("/system/organization/member-list")
async def api_system_org_member_list_post(request: Request):
    """系统组织成员列表（POST 兼容前端调用）。"""
    body = await read_body(request)
    org_id = body.get("organizationId") or body.get("orgId") or ""
    members = organization_service.list_members(org_id) if org_id else []
    return page_result(members, len(members), current=body.get("current", 1), page_size=body.get("pageSize", 10))

@router.post("/system/organization/option/all")
async def api_system_org_option_all_post(request: Request):
    """系统组织下拉选项（POST 兼容前端调用）。"""
    await _read_body(request)
    return ok([])

@router.post("/system/project/pool-options")
async def api_system_project_pool_options_post(request: Request):
    """系统项目资源池选项（POST 兼容前端调用）。"""
    await _read_body(request)
    return ok([])

# ── 带路径参数补充 ────────────────────────────────────────

@router.get("/system/organization/delete/{id}")
def system_org_delete_path(id: str):
    """删除组织（带路径参数）。"""
    organization_service.delete(id)
    return ok({"id": id, "deleted": True})

@router.get("/system/project/delete/{id}")
def system_project_delete_path(id: str):
    """删除项目（带路径参数）。"""
    project_service.delete(id)
    return ok({"id": id, "deleted": True})

@router.get("/system/organization/recover/{id}")
def system_org_recover_path(id: str):
    """恢复组织（带路径参数）。"""
    recovered = organization_service.recover(id)
    return ok({"id": id, "recovered": recovered})

@router.get("/system/project/revoke/{id}")
def system_project_revoke_path(id: str):
    """撤销项目（带路径参数）。"""
    project_service.update(id, {"status": "active"})
    return ok({"id": id, "revoked": True})

@router.get("/system/organization/get-option/{source_id}")
def system_org_get_option_path(source_id: str, keyword: str = ""):
    """获取组织/项目用户选项（带路径参数）。"""
    return ok([])

@router.get("/organization/project/delete/{id}")
def org_project_delete_path(id: str):
    """删除组织下项目（带路径参数）。"""
    return ok({"id": id, "deleted": True})

@router.get("/organization/project/revoke/{id}")
def org_project_revoke_path(id: str):
    """撤销组织下项目（带路径参数）。"""
    return ok({"id": id, "revoked": True})

@router.get("/organization/project/remove-member/{project_id}/{user_id}")
def org_project_remove_member_path(project_id: str, user_id: str):
    """移除组织项目成员（带路径参数）。"""
    return ok({"project_id": project_id, "user_id": user_id, "removed": True})

@router.get("/organization/project/user-member-list/{organization_id}/{project_id}")
def org_project_user_member_list_path(organization_id: str, project_id: str, keyword: str = ""):
    """获取组织项目用户成员列表（带路径参数）。"""
    return ok([])

async def _read_body(request: Request) -> dict:
    """安全读取请求体。"""
    try:
        return await read_body(request)
    except Exception:
        return {}

# 组织不存在成员列表（前端: /organization/not-exist/user/list/{organizationId}）

@router.get("/organization/not-exist/user/list/{organization_id}")
def organization_not_exist_user_list_path(organization_id: str, keyword: str = ""):
    """获取组织不存在成员列表（带路径参数，前端 getUser 下拉调用）。

    返回所有系统用户中尚未加入该组织的用户列表。
    """
    from app.services.auth_service import auth_service

    all_users = auth_service.list_users(limit=1000)
    # 获取组织现有成员 userId 集合
    existing_ids = set()
    try:
        members = organization_service.list_members(organization_id, limit=10000)
        existing_ids = {m.get("user_id", "") for m in members}
    except Exception:
        pass

    items = []
    for u in all_users:
        uid = u.get("id", "")
        if uid in existing_ids:
            continue
        if keyword:
            kw = keyword.lower()
            if (kw not in u.get("username", "").lower()
                    and kw not in u.get("name", "").lower()
                    and kw not in u.get("email", "").lower()):
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

# 组织项目列表已由 organizations.py 的 /organization/project/list/{org_id} 提供。
# 此处原注册 /organization/project/list/{organization_id} 与前者同形不同名，
# 因注册顺序靠后永远不可达，已删除（见 route_conflict_check 门禁）。

# 组织状态流设置（前端: /organization/status/flow/setting/get/{scopedId}/{scene}）

@router.get("/organization/status/flow/setting/get/{scoped_id}/{scene}")
def organization_status_flow_setting_get_path(scoped_id: str, scene: str):
    """获取组织状态流设置（带路径参数）。

    返回 WorkFlowType[]（默认播种新建/处理中/已完成），供组织模板工作流表格使用。
    """
    items = workflow_service.list_statuses("ORGANIZATION", scoped_id, scene)
    if not items:
        items = workflow_service.seed_default_statuses("ORGANIZATION", scoped_id, scene)
    return ok(items)

# 组织模板启用配置（前端: /organization/template/enable/config/{scopedId}）

def _org_default_template_status() -> Dict:
    """默认组织模板启用状态（前端: Record<string, boolean>）。"""
    return {
        "FUNCTIONAL": True,
        "API": False,
        "UI": False,
        "TEST_PLAN": False,
        "BUG": True,
    }

@router.get("/organization/template/enable/config/{scoped_id}")
def organization_template_enable_config_path(scoped_id: str):
    """获取组织模板启用配置（带路径参数）。"""
    return ok(_org_default_template_status())

# 个人模型详情（前端: /personal/model/get/{modelId}）

# ════════════════════════════════════════════════════════════
# 路径参数兼容路由（自 path_param_fixes.py 迁移）
# ════════════════════════════════════════════════════════════

@router.get("/organization/custom/field/delete/{id}")
@router.post("/organization/custom/field/delete/{id}")
def organization_custom_field_delete_path(id: str):
    """/organization/custom/field/delete 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"id": id, "deleted": True})

@router.get("/organization/custom/field/get/{id}")
@router.post("/organization/custom/field/get/{id}")
def organization_custom_field_get_path(id: str):
    """/organization/custom/field/get 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"id": id, "field": None})

@router.get("/organization/status/flow/setting/status/delete/{id}")
@router.post("/organization/status/flow/setting/status/delete/{id}")
def organization_status_flow_setting_status_delete_path(id: str):
    """/organization/status/flow/setting/status/delete 带路径参数（前端 RESTful 调用兼容）。"""
    workflow_service.delete_status(id)
    return ok({"id": id, "deleted": True})

@router.get("/system/authsource/delete/{id}")
@router.post("/system/authsource/delete/{id}")
def system_authsource_delete_path(id: str):
    """/system/authsource/delete 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"id": id, "deleted": True})

@router.get("/system/user/check-invite/{id}")
@router.post("/system/user/check-invite/{id}")
def system_user_check_invite_path(id: str):
    """/system/user/check-invite 带路径参数（前端 RESTful 调用兼容，/invite 邀请注册页免登录）。

    前端 /#/invite 页面通过 validInvite 校验邀请链接有效性：
      - 邀请存在且未过期/未使用 -> 200，展示注册表单
      - 邀请不存在/已过期/已使用  -> 抛错，页面展示“邀请已过期”
    """
    from app.services.invitation_service import invitation_service
    if not invitation_service.is_valid(id):
        return JSONResponse(
            {"code": 400, "message": "邀请链接无效或已过期", "data": None, "success": False},
            status_code=400,
        )
    inv = invitation_service.get_by_invite_id(id) or {}
    return ok({
        "id": id,
        "invited": True,
        "expireTime": int((inv.get("expire_time") or 0) * 1000),
        "email": inv.get("email", ""),
    })

@router.get("/user/api/key/delete/{id}")
@router.post("/user/api/key/delete/{id}")
def user_api_key_delete_path(id: str):
    """/user/api/key/delete 带路径参数（前端 RESTful 调用兼容）。接入真实 auth_service 落库。"""
    ok_flag = bool(auth_service.delete_api_key(id)) if id else False
    return ok({"id": id, "deleted": ok_flag})

@router.get("/user/api/key/disable/{id}")
@router.post("/user/api/key/disable/{id}")
def user_api_key_disable_path(id: str):
    """/user/api/key/disable 带路径参数（前端 RESTful 调用兼容）。接入真实 auth_service.toggle_api_key。"""
    ok_flag = bool(auth_service.toggle_api_key(id, enable=False)) if id else False
    return ok({"id": id, "disabled": ok_flag})

@router.get("/user/api/key/enable/{id}")
@router.post("/user/api/key/enable/{id}")
def user_api_key_enable_path(id: str):
    """/user/api/key/enable 带路径参数（前端 RESTful 调用兼容）。接入真实 auth_service.toggle_api_key。"""
    ok_flag = bool(auth_service.toggle_api_key(id, enable=True)) if id else False
    return ok({"id": id, "enabled": ok_flag})

@router.get("/user/local/config/disable/{id}")
@router.post("/user/local/config/disable/{id}")
def user_local_config_disable_path(id: str):
    """/user/local/config/disable 带路径参数（前端 RESTful 调用兼容）。接入真实 auth_service.toggle_local_config。"""
    ok_flag = bool(auth_service.toggle_local_config(id, enable=False)) if id else False
    return ok({"id": id, "disabled": ok_flag})

@router.get("/user/local/config/enable/{id}")
@router.post("/user/local/config/enable/{id}")
def user_local_config_enable_path(id: str):
    """/user/local/config/enable 带路径参数（前端 RESTful 调用兼容）。接入真实 auth_service.toggle_local_config。"""
    ok_flag = bool(auth_service.toggle_local_config(id, enable=True)) if id else False
    return ok({"id": id, "enabled": ok_flag})

@router.get("/user/platform/get/{orgId}")
@router.post("/user/platform/get/{orgId}")
def user_platform_get_path(orgId: str):
    """/user/platform/get 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"id": orgId, "platforms": []})
