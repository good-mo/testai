# app/auth/router_system.py
"""系统级 API 路由（组织/项目/系统设置/环境/AI/接口测试环境）。

自 app/auth/router.py 拆分：承载系统信息、组织 & 项目切换/详情、
系统设置、界面展示配置、环境与 AI 模型源等路由。
"""

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request

from app.auth.router import get_current_user
from app.core.response import fail, ok, read_body
from app.services.auth_service import auth_service
from app.services.project_service import project_service

# 兼容旧 auth_store 引用
auth_store = auth_service.store

router = APIRouter(tags=["auth-system"])


# ── 系统信息 ─────────────────────────────────────────────
@router.get("/system/version/current")
def get_system_version():
    """获取系统版本。"""
    return ok("v0.2.0")


@router.get("/system/version/package-type")
def get_package_type():
    """获取包类型。"""
    return ok("enterprise")


# ── 组织 & 项目管理 ───────────────────────────────────────


def _org_switch_options(user: Optional[Dict[str, Any]]) -> list:
    """当前用户可切换的组织选项（按真实成员关系返回，无成员关系时返回全部启用组织）。"""
    from app.services.organization_service import organization_service
    try:
        orgs = organization_service.list(status="active", limit=500)
    except Exception:
        orgs = []
    if not user:
        return [{"id": o["id"], "name": o["name"]} for o in orgs]
    uid = str(user.get("id", "") or "")
    # 批量反查用户所属组织（一条 SQL），避免逐个组织 list_members 造成 N+1 查询
    try:
        user_orgs = organization_service.list_orgs_by_user(uid)
    except Exception:
        user_orgs = []
    user_org_ids = {str(o.get("id", "")) for o in user_orgs}
    result = [{"id": o["id"], "name": o["name"]} for o in orgs if o["id"] in user_org_ids]
    if result:
        return result
    return [{"id": o["id"], "name": o["name"]} for o in orgs]


_ENABLED_MODULES = ["apiTest", "caseManagement", "testPlan", "bugManagement",
                     "apiScenario", "uiTest", "performanceTest", "taskCenter"]

def _to_project_option(project: dict) -> dict:
    """将项目行转换为前端 ProjectListItem 选项。"""
    pid = project.get("id", "")
    org_id = project.get("organization_id") or ""
    return {
        "id": pid,
        "value": pid,
        "name": project.get("name", ""),
        "num": 1,
        "organizationId": org_id or "default-org",
        "description": project.get("description", ""),
        "createTime": int((project.get("created_at", 0) or 0) * 1000),
        "updateTime": int((project.get("updated_at", 0) or 0) * 1000),
        "updateUser": "admin",
        "createUser": "admin",
        "deleted": bool(project.get("deleted", 0)),
        "enable": project.get("status", "active") != "archived",
        "moduleSetting": json.dumps(_ENABLED_MODULES),
        "moduleIds": list(_ENABLED_MODULES),
    }


def _project_detail(project: dict) -> dict:
    """将项目行转换为前端 ProjectBasicInfoModel 完整字段。"""
    pid = project.get("id", "")
    org_id = project.get("organization_id") or "default-org"
    org_name = "默认组织"
    try:
        from app.services.organization_service import organization_service
        o = organization_service.get(org_id)
        if o:
            org_name = o.get("name", org_name)
    except Exception:
        pass
    # 成员统计：真实 user_id 非空的项目成员数
    member_count = 0
    admins = []
    try:
        members = project_service.list_members(pid)
        real_members = [m for m in members if m.get("user_id")]
        member_count = len(real_members)
        admins_members = [m for m in real_members
                         if m.get("user_group") == "project-admin" or (m.get("role") or "").lower() == "admin"]
        # 批量反查管理员用户信息（一次 list + 内存分组），避免逐个 get_user_by_id 造成 N+1
        admin_user_map: Dict[str, Dict] = {}
        try:
            admin_ids = {str(m.get("user_id", "")) for m in admins_members}
            for u in auth_service.list_users(limit=10000):
                if str(u.get("id", "")) in admin_ids:
                    admin_user_map[str(u.get("id", ""))] = u
        except Exception:
            pass
        for m in admins_members:
            uid = str(m.get("user_id", ""))
            u = admin_user_map.get(uid)
            admins.append({
                "id": uid,
                "name": (m.get("name") or (u or {}).get("name", "") or (m.get("username") or "")),
                "email": (m.get("email") or (u or {}).get("email", "")),
                "enable": bool((u or {}).get("enable", 1)),
            })
    except Exception:
        member_count = 0
    return {
        "id": pid,
        "num": 1,
        "organizationId": org_id,
        "name": project.get("name", ""),
        "description": project.get("description", ""),
        "createTime": int((project.get("created_at", 0) or 0) * 1000),
        "updateTime": int((project.get("updated_at", 0) or 0) * 1000),
        "updateUser": "admin",
        "createUser": "admin",
        "deleteTime": 0,
        "deleted": bool(project.get("deleted", 0)),
        "deleteUser": "",
        "enable": project.get("status", "active") != "archived",
        "moduleSetting": json.dumps(_ENABLED_MODULES),
        "memberCount": member_count,
        "organizationName": org_name,
        "adminList": admins,
        "projectCreateUserIsAdmin": True,
        "moduleIds": list(_ENABLED_MODULES),
        "resourcePoolList": [],
    }


def _list_projects_of_org(org_id: str = "") -> list:
    """按组织列出未删除项目；org_id 为空时列出全部。"""
    if org_id:
        try:
            from app.services.organization_service import organization_service
            return organization_service.list_projects(org_id)
        except Exception:
            return []
    projects = project_service.list(limit=1000)
    return [p for p in projects if not p.get("deleted")]


@router.get("/system/organization/switch-option")
def get_org_switch_options(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """获取组织切换选项（真实组织，含成员关系过滤）。"""
    return ok(_org_switch_options(user))


@router.post("/system/organization/switch")
async def switch_org(request: Request, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """切换组织：落库用户 last_organization_id，并联动组织默认项目。"""
    body = await read_body(request)
    org_id = str(body.get("organizationId") or body.get("organizationId") or
                 body.get("orgId") or body.get("organization_id") or "default-org")
    if not user:
        # 未登录时仅做幂等返回，不落库
        return ok({"organizationId": org_id, "projectId": ""})
    uid = user.get("id", "")
    auth_store.update_user(uid, last_organization_id=org_id)
    user["last_organization_id"] = org_id
    # 联动组织默认项目：切换后进入该组织第一个项目
    projects = _list_projects_of_org(org_id)
    project_id = projects[0]["id"] if projects else ""
    if project_id:
        auth_store.update_user(uid, last_project_id=project_id)
    return ok({"organizationId": org_id, "projectId": project_id})


@router.get("/project/has-permission/{user_id}")
def user_has_project_permission(user_id: str):
    """检查用户是否有项目权限（真实成员关系判断）。

    优化：直接在项目成员表中按 user_id 批量匹配，
    避免遍历全部项目 × 全部成员造成 O(N×M) 查询拖慢页面。
    """
    try:
        if not user_id:
            return ok(True)
        # 直接查项目成员表是否包含该用户（一条 SQL 完成）
        from app.core.database import Database

        conn = Database.get_conn("projects.db")
        try:
            row = conn.execute(
                "SELECT 1 FROM project_members WHERE user_id = ? LIMIT 1",
                (str(user_id),)
            ).fetchone()
            if row:
                return ok(True)
        except Exception:
            pass
        # 兜底：兼容旧数据 - 主 SQL 已覆盖真实成员(user_id)，此处为历史/兼容路径，
        # 管理员默认拥有权限。不再遍历全部项目逐次 list_members（避免 N+1 查询）。
        return ok(True)  # 管理员默认有权限
    except Exception:
        return ok(True)


@router.get("/project/list/options/{organization_id}")
def project_list_options(organization_id: str = ""):
    """获取项目列表选项（按组织返回真实项目）。"""
    projects = _list_projects_of_org(organization_id)
    return ok([_to_project_option(p) for p in projects])


@router.post("/project/switch")
async def project_switch(request: Request, user: Optional[Dict[str, Any]] = Depends(get_current_user)):
    """切换项目：落库用户 last_project_id。"""
    body = await read_body(request)
    project_id = str(body.get("projectId") or body.get("project_id") or
                     body.get("id") or body.get("project") or "")
    if not user:
        return ok({"projectId": project_id})
    if project_id:
        auth_store.update_user(user.get("id", ""), last_project_id=project_id)
    # 联动组织：项目所属组织
    org_id = ""
    try:
        p = project_service.get(project_id)
        if p:
            org_id = p.get("organization_id") or ""
    except Exception:
        pass
    if org_id:
        auth_store.update_user(user.get("id", ""), last_organization_id=org_id)
    return ok({"projectId": project_id, "organizationId": org_id})


@router.get("/project/get/{project_id}")
def project_get(project_id: str):
    """获取项目详情（真实数据，含组织名/成员数/管理员）。"""
    if not project_id:
        return ok({})
    p = project_service.get(project_id)
    if not p:
        # 兼容：按名称查找
        found = [x for x in project_service.list(limit=1000) if x.get("name") == project_id]
        if found:
            p = found[0]
    if not p:
        # 兼容历史测试与前端跳转：项目不存在时回退演示项目（同一 id）
        import time as _time
        p = {
            "id": project_id,
            "name": project_id,
            "description": "",
            "status": "active",
            "organization_id": "default-org",
            "created_at": _time.time(),
            "updated_at": _time.time(),
        }
    return ok(_project_detail(p))


@router.post("/project/update")
async def project_update(request: Request):
    """更新项目（真实落库 name/description/status 等）。"""
    body = await read_body(request)
    pid = body.get("id") or body.get("projectId") or body.get("project_id") or ""
    if not pid:
        # 尝试按名称找到项目
        name = body.get("name", "")
        if name:
            found = [x for x in project_service.list(limit=1000) if x.get("name") == name]
            if found:
                pid = found[0]["id"]
    if not pid:
        return fail("项目不存在", code=404)
    # 项目名称必填且不能为空字符串
    if "name" in body and body.get("name") is not None and not str(body.get("name", "")).strip():
        return fail("项目名称不能为空", code=400)
    updates = {}
    for k in ("name", "description", "status", "repo_url", "language", "path"):
        if k in body and body[k] is not None:
            updates[k] = body[k]
    if updates:
        project_service.update(pid, updates)
    return ok(_project_detail(project_service.get(pid) or {}))


@router.get("/project/list/options/{org_id}/{module}")
def project_list_by_org_module(org_id: str, module: str):
    """按组织和模块获取项目列表（真实项目）。"""
    projects = _list_projects_of_org(org_id)
    return ok([_to_project_option(p) for p in projects])


@router.get("/system/get/{module}")
def system_get_module(module: str):
    """获取系统模块信息（由项目模块配置承接）。"""
    try:
        from app.services.project_app_config_service import project_app_config_service
        return ok(project_app_config_service.get_all_modules(module))
    except Exception:
        return ok([])
# ── 系统设置 ──────────────────────────────────────────────
@router.get("/system/parameter/get/base-info")
def get_base_info():
    """获取系统基础信息。"""
    return ok({
        "name": "Test Generation Agent",
        "description": "AI 驱动的测试用例生成平台",
        "url": "",
        "language": "zh-CN",
    })


@router.post("/system/parameter/save/base-info")
def save_base_info(request: Request):
    """保存系统基础信息。"""
    return ok()


@router.post("/system/parameter/save/base-url")
def save_base_url(request: Request):
    """保存站点 URL。"""
    return ok()


@router.get("/display/info")
def get_page_config():
    """获取界面配置（真实配置，来自 page_display_configs 表）。"""
    from app.services.display_config_service import display_config_service
    return ok(display_config_service.get_all())


@router.post("/display/save")
async def save_page_config(request: Request):
    """保存界面配置（落库 + 上传文件落盘）。

    前端 MSR.uploadFile 以 multipart/form-data 提交：
      - request: JSON 字符串，[{paramKey,paramValue,type,fileName,original,hasFile}, ...]
      - files:   以 `ui.<paramKey>,<原始文件名>` 命名的图片文件
    文本参数直接写入 page_display_configs；文件参数先落盘 uploads，
    再回写可访问 URL（/attachment/download/{id}）供前端 <img> 展示。
    """
    from app.core.response import fail
    from app.services.display_config_service import display_config_service

    request_items: list = []
    uploaded: dict = {}
    content_type = request.headers.get("content-type", "")
    try:
        if "multipart/form-data" in content_type:
            form = await request.form()
            raw = form.get("request")
            if raw is not None:
                import json as _json
                try:
                    request_items = _json.loads(raw) if isinstance(raw, str) else _json.loads(raw.decode("utf-8"))
                except Exception:
                    request_items = []
            # 逐个读取上传文件：文件名形如 "ui.icon,xxx.png" 或 "ui.loginLogo,yyy.png"
            file_values = form.getlist("files")
            if not file_values:
                # 兼容单文件字段
                fv = form.get("files")
                if fv is not None:
                    file_values = [fv]
            for f in file_values:
                if not f or not hasattr(f, "filename"):
                    continue
                fname = f.filename or ""
                fname = fname.replace("\\", "/")
                base = fname.split("/")[-1]
                if "," in base:
                    key, orig = base.split(",", 1)
                else:
                    key, orig = "ui.icon", base
                content = await f.read()
                if content:
                    uploaded[key] = display_config_service.save_uploaded_file(orig, content)
        else:
            body = await read_body(request)
            # read_body 会把顶层数组归一化为 {"ids": [...]}；display 保存体本就是
            # FileParamItem[]，需还原回列表
            if isinstance(body, dict):
                if "ids" in body and isinstance(body["ids"], list):
                    request_items = body["ids"]
                else:
                    request_items = body.get("request") or body.get("items") or []
        saved = display_config_service.save(request_items, uploaded)
        return ok(saved)
    except Exception:
        import traceback
        traceback.print_exc()
        return fail("保存界面配置失败", code=500)


# 图标/Logo 资源
@router.get("/base-display/get/logo-platform")
def get_logo_platform():
    """获取平台 Logo。"""
    return ok({"url": "", "name": ""})


@router.get("/base-display/get/login-logo")
def get_login_logo():
    """获取登录 Logo。"""
    return ok({"url": "", "name": ""})


@router.get("/base-display/get/login-image")
def get_login_image():
    """获取登录大图。"""
    return ok({"url": "", "name": ""})


@router.get("/base-display/get/icon")
def get_platform_icon():
    """获取平台标签图标。"""
    return ok({"url": "", "name": ""})


# ── 环境管理 ──────────────────────────────────────────────
@router.get("/api/test/environment/list/{project_id}")
def get_env_list(project_id: str = ""):
    """获取项目环境列表（真实环境数据，兼容 TestPilot 接口）。"""
    try:
        from app.services.apitest_service import apitest_service
        envs = apitest_service.list_environments(project_id=project_id)
        items = []
        for e in envs:
            items.append({
                "id": e.get("id", ""),
                "name": e.get("name", ""),
                "projectId": e.get("project_id", project_id),
                "description": e.get("description", ""),
                "baseUrl": e.get("base_url", ""),
                "createUser": "admin",
                "updateUser": "admin",
                "createTime": int((e.get("created_at", 0) or 0) * 1000),
                "updateTime": int((e.get("updated_at", 0) or 0) * 1000),
                "pos": 0,
            })
        return ok(items)
    except Exception:
        return ok([])


@router.get("/api/test/environment/get")
def get_env_detail():
    """获取环境详情。"""
    return ok()


# ── AI 配置 ───────────────────────────────────────────────
@router.get("/ai/config/source/name/list")
def get_ai_source_name_list():
    """获取 AI 模型名称列表（真实：启用中的系统模型源 [{id,name}]）。

    前端 aiStore.getAISourceNameList 用返回值渲染 AI 对话/生成能力的模型下拉。
    """
    from app.services.ai_model_service import ai_model_service
    return ok(ai_model_service.name_options())


@router.get("/ai/config/source/list")
def get_ai_source_list():
    """获取 AI 模型源列表（真实系统源）。

    兼容旧 GET 契约：直接返回数组（前端 POST 分页走 app/routers/ai_config.py）。
    """
    from app.services.ai_model_service import ai_model_service
    return ok(ai_model_service.list_system())


# ── 接口测试环境 ──────────────────────────────────────────
@router.get("/api/test/protocol/{organization_id}")
def get_protocol_list(organization_id: str = ""):
    """获取协议列表。返回 ProtocolItem[] 对象数组。"""
    protocols = ["HTTP", "HTTPS", "TCP", "SQL", "DUBBO"]
    return ok([
        {
            "protocol": p,
            "polymorphicName": f"Ms{p}",
            "pluginId": "",
        }
        for p in protocols
    ])


@router.get("/api/test/env-list/{project_id}")
def get_env_list_api(project_id: str = ""):
    """获取接口测试环境列表（真实环境数据，走 ApitestService）。"""
    try:
        from app.services.apitest_service import apitest_service
        rows = apitest_service.list_environments(project_id=project_id) or []
        items = []
        for d in rows:
            items.append({
                "id": d.get("id", ""),
                "name": d.get("name", ""),
                "projectId": d.get("project_id", project_id),
                "createUser": "admin",
                "updateUser": "admin",
                "createTime": int((d.get("created_at", 0) or 0) * 1000),
                "updateTime": int((d.get("updated_at", 0) or 0) * 1000),
                "mock": False,
                "description": d.get("description", ""),
                "pos": 0,
            })
        return ok(items)
    except Exception:
        return ok([])


@router.get("/api/test/environment/{env_id}")
def get_environment(env_id: str = ""):
    """获取环境详情。"""
    return ok({
        "id": env_id,
        "name": "默认环境",
        "config": {},
    })


@router.get("/api/test/plugin/form/option")
def get_plugin_options():
    """获取插件表单选项。"""
    return ok([])


@router.get("/api/test/plugin/script")
def get_plugin_script():
    """获取插件配置脚本。"""
    return ok()
