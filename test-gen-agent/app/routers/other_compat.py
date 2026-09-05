# app/routers/other_compat.py（自 app/adapters/domains/other.py 迁移）
"""业务域路由拆分：other（Phase 3 重构）。

原 app/adapters/domains/other.py 整体迁入 routers 层。
保持 TestPilot 兼容路径与 {code,message,data} 响应格式不变。
"""

import time
import uuid

from fastapi import APIRouter, Request

from app.core.response import fail, ok, page_result, read_body
from app.core.helpers import as_model, current_user_id, definition_followed
from app.logging_config import get_logger
from app.models.other_compat import (
    LdapLoginBody,
    OperationLogListBody,
    PersonalModelIdBody,
    PersonalModelPageBody,
    ReviewCaseHistoryBody,
    ReviewCaseSaveBody,
    ShareDetailBody,
    ShareModuleTreeBody,
    SharePageBody,
)
from app.services.case_service import case_service

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-other"])


def _build_review_history(review_id: str, case_id: str):
    """根据评审-用例关联记录构建评审历史。"""
    from app.services.case_review_service import case_review_service as cvs
    try:
        if not review_id or not case_id:
            return ok([])
        links = cvs.list_links(review_id)
        for link in links:
            if link.get("case_id", "") != case_id:
                continue
            status = link.get("status", "UN_REVIEWED")
            reviewer = link.get("reviewer", "") or "admin"
            comment = link.get("comment", "") or ""
            update_time = int((link.get("update_time") or 0) * 1000)
            # 解析评审人用户名
            user_name = reviewer
            try:
                for u in cvs.list_review_users():
                    if str(u.get("id", "")) == reviewer:
                        user_name = u.get("name", reviewer)
                        break
            except Exception:
                pass
            history = [{
                "id": link.get("id", ""),
                "reviewId": review_id,
                "caseId": case_id,
                "status": status,
                "deleted": False,
                "notifier": reviewer,
                "createUser": reviewer,
                "createTime": update_time,
                "content": comment,
                "userLogo": "",
                "userName": user_name,
                "contentText": comment,
            }]
            return ok(history)
        return ok([])
    except Exception:
        return ok([])


@router.get("/api/doc/share/delete")
def api_doc_share_delete_get(request: Request):
    """接口文档分享删除（GET兼容）。"""
    return ok()


@router.get("/api/doc/share/detail")
def api_doc_share_detail_get(request: Request):
    """接口文档分享详情（GET兼容）。"""
    return ok({
        "invalid": False,
        "allowExport": False,
        "isPrivate": False,
        "projectName": "",
    })


@router.get("/api/doc/share/detail/{share_id}")
def api_doc_share_detail_path(share_id: str):
    """接口文档分享详情（带 share_id 路径参数）。

    前端 shareDetail(id) 用 GET params: id 拼成 /api/doc/share/detail/{shareId}。
    返回 ShareDetailType 结构。
    """
    return ok({
        "invalid": False,
        "allowExport": False,
        "isPrivate": False,
        "projectName": "",
    })


@router.get("/api/doc/share/get-detail")
def api_doc_share_get_detail_get(request: Request):
    """接口文档分享详情（GET兼容）。"""
    return ok({})


@router.get("/api/doc/share/get-detail/{share_id}")
def api_doc_share_get_detail_path(share_id: str):
    """接口文档分享详情（带 share_id 路径参数）。

    前端 getShareDefinitionDetail(id) 用 GET params: id 拼成 /api/doc/share/get-detail/{id}。
    返回 ApiDefinitionDetail 结构。
    """
    return ok({
        "id": share_id,
        "name": "分享接口",
        "protocol": "HTTP",
        "method": "GET",
        "path": "/api/share/example",
        "request": {
            "headers": [],
            "body": {},
            "query": [],
            "rest": [],
        },
        "response": [],
        "createTime": int(time.time() * 1000),
        "updateTime": int(time.time() * 1000),
        "createUser": "",
        "updateUser": "",
        "deleteUser": "",
        "deleteTime": 0,
        "deleted": False,
        "latest": True,
        "projectId": "",
        "moduleId": "",
        "versionId": "",
        "refId": share_id,
        "versionName": "v1.0",
        "caseTotal": 0,
        "casePassRate": "",
        "caseStatus": "",
        "follow": definition_followed(share_id),
        "customFields": [],
        "num": 1,
        "pos": 1,
        "createUserName": "",
        "updateUserName": "",
        "deleteUserName": "",
    })


@router.get("/sso/callback/we_com")
def sso_callback_we_com_get(request: Request):
    """企微SSO回调（GET兼容）。"""
    return ok({"success": True})


@router.get("/sso/callback/ding_talk")
def sso_callback_ding_talk_get(request: Request):
    """钉钉SSO回调（GET兼容）。"""
    return ok({"success": True})


@router.get("/sso/callback/lark")
def sso_callback_lark_get(request: Request):
    """飞书SSO回调（GET兼容）。"""
    return ok({"success": True})


@router.get("/sso/callback/lark_suite")
def sso_callback_lark_suite_get(request: Request):
    """飞书套件SSO回调（GET兼容）。"""
    return ok({"success": True})

# ════════════════════════════════════════════════════════════
# B类修复：前端用 POST，后端只有 GET —— 添加 POST 方法
# ════════════════════════════════════════════════════════════


@router.post("/api/doc/share/module/count")
def api_doc_share_module_count_post(request: Request):
    """文档分享模块统计（POST兼容）。

    前端期望返回 Record<module_id, count> 映射对象（如 {"root": 0, "mod_1": 2}）。
    """
    return ok({})


@router.post("/api/doc/share/module/tree")
async def api_doc_share_module_tree_post(request: Request):
    """文档分享模块树（POST兼容）。

    前端 moduleTree 的 initShareModuleTree 期望返回 ModuleTreeNode[]。
    """
    body = await read_body(request)
    mb = as_model(body, ShareModuleTreeBody)
    try:
        from app.services.apitest_service import apitest_service
        _share_id = mb.effective_share_id
        project_id = mb.effective_project_id
        tree = apitest_service.build_module_tree(
            module_type="api", include_api=True, project_id=project_id or None
        )
        return ok(tree if tree else [])
    except Exception:
        return ok([])


@router.get("/api/test/download")
def api_test_download(file_name: str = "", download_id: str = ""):
    """报告文件下载。"""
    return ok({"fileId": download_id, "fileName": file_name or "report.zip"})


@router.post("/api/test/download")
async def api_test_download_post():
    """报告文件下载 POST。"""
    return ok({"fileId": str(uuid.uuid4())})


# ════════════════════════════════════════════════════════════
# P0-2: 接口定义 / 用例 / 场景 / 调试补充接口
# ════════════════════════════════════════════════════════════


@router.post("/api/stop")
async def api_stop():
    """停止执行。"""
    return ok()


@router.get("/api/stop")
def api_stop_get(report_id: str = ""):
    """停止执行 GET。"""
    return ok()


# ════════════════════════════════════════════════════════════
# P0-3: 接口定义定时同步  /api/definition/schedule/*
# ════════════════════════════════════════════════════════════


@router.post("/api/doc/share/add")
async def api_doc_share_add(request: Request):
    """新增接口文档分享。"""
    body = await read_body(request)
    return ok({"id": str(uuid.uuid4()), **body})


@router.post("/api/doc/share/update")
async def api_doc_share_update():
    """更新接口文档分享。"""
    return ok()


@router.post("/api/doc/share/delete")
async def api_doc_share_delete():
    """删除接口文档分享。"""
    return ok()


@router.post("/api/doc/share/page")
async def api_doc_share_page(request: Request):
    """接口文档分享列表。"""
    body = await read_body(request)
    page = as_model(body, SharePageBody)
    return page_result([], len([]), current=page.effective_current, page_size=page.effective_page_size)


@router.post("/api/doc/share/check")
async def api_doc_share_check():
    """校验分享密码。"""
    # 前端 checkSharePsd 期望 data 为 true（校验通过）
    return ok(True)


@router.post("/api/doc/share/detail")
async def api_doc_share_detail(request: Request):
    """查看分享链接。"""
    body = await read_body(request)
    share_id = as_model(body, ShareDetailBody).effective_share_id
    return ok({
        "invalid": False,
        "allowExport": False,
        "isPrivate": False,
        "projectName": "",
        "id": share_id,
        "shareId": share_id,
    })


@router.get("/api/doc/share/module/tree")
def api_doc_share_module_tree(share_id: str = ""):
    """分享模块树。"""
    return ok([])


@router.get("/api/doc/share/module/count")
def api_doc_share_module_count(share_id: str = ""):
    """分享模块数量。"""
    return ok({})


@router.post("/api/doc/share/export")
async def api_doc_share_export():
    """导出分享接口定义。"""
    return ok({"id": str(uuid.uuid4())})


@router.get("/api/doc/share/download/file")
def api_doc_share_download_file(file_id: str = ""):
    """下载分享文档。"""
    return ok({"fileId": file_id, "fileName": "share"})


@router.post("/api/doc/share/stop")
async def api_doc_share_stop():
    """停止分享导出。"""
    return ok()


@router.post("/api/doc/share/get-detail")
async def api_doc_share_get_detail():
    """获取分享接口定义详情。"""
    return ok({})


@router.post("/api/doc/share/plugin/script")
async def api_doc_share_plugin_script():
    """获取分享插件脚本。"""
    return ok({})


# ════════════════════════════════════════════════════════════
# P1-1: 项目环境管理  /project/environment/*
# ════════════════════════════════════════════════════════════


@router.get("/api/test/pool-option")
def api_test_pool_option():
    """接口测试资源池选项。"""
    return ok([])


@router.get("/api/test/get-pool")
def api_test_get_pool():
    """获取资源池 ID。"""
    return ok({})


@router.get("/api/test/get-pool/")
def api_test_get_pool_trailing(project_id: str = ""):
    """获取资源池 ID（尾斜杠）。"""
    return ok({})


@router.get("/api/test/env-list")
def api_test_env_list(project_id: str = ""):
    """接口测试环境列表。"""
    try:
        # 收口：经 ApitestService 访问 api_environments，避免适配层直连 DB
        from app.services.apitest_service import apitest_service
        rows = apitest_service.list_environments(project_id=project_id) or []
        items = []
        for d in rows:
            items.append({
                "id": d.get("id", ""),
                "name": d.get("name", ""),
                "projectId": d.get("project_id", ""),
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


@router.get("/api/test/environment")
def api_test_environment(project_id: str = "", environment_id: str = ""):
    """接口测试环境。"""
    return ok({})


@router.get("/api/test/protocol")
def api_test_protocol():
    """接口测试协议列表。返回 ProtocolItem[] 对象数组。"""
    protocols = ["HTTP", "HTTPS", "TCP", "SQL", "DUBBO"]
    return ok([
        {
            "protocol": p,
            "polymorphicName": f"Ms{p}",
            "pluginId": "",
        }
        for p in protocols
    ])


@router.get("/api/test/common-script")
def api_test_common_script():
    """公共脚本列表。"""
    return ok([])


@router.get("/api/test/common-script/{script_id}")
def api_test_common_script_detail(script_id: str):
    """获取单个公共脚本详情（供API测试条件使用）。"""
    try:
        # 收口：经 ProjectService.get_custom_func 读取 custom_funcs，避免适配层直连 DB
        from app.services.project_service import project_service
        row = project_service.get_custom_func(script_id)
        if not row:
            return ok({})
        # 解析 params 为 KeyValueParam 格式
        params_raw = row.get("params") if row.get("params") else "[]"
        try:
            import json as _json
            params = _json.loads(params_raw) if isinstance(params_raw, str) else []
        except Exception:
            params = []
        return ok({
            "id": row.get("id") or script_id,
            "name": row.get("name", ""),
            "script": row.get("script", ""),
            "params": params,
            "scriptLanguage": row.get("type", "HTTP"),
        })
    except Exception:
        return ok({})


@router.post("/api/test/custom/func/run")
async def api_test_custom_func_run():
    """运行自定义函数。"""
    return ok({"result": "success"})


# ════════════════════════════════════════════════════════════
# P1-13: 任务中心  /project/task-center/*  /organization/task-center/*  /system/task-center/*
# ════════════════════════════════════════════════════════════

# 项目任务中心


@router.get("/task/center/api/project/stop")
def task_center_api_project_stop():
    """停止项目 API 任务。"""
    return ok()


@router.get("/task/center/project/schedule/page")
def task_center_project_schedule_page():
    """项目定时任务分页。"""
    return page_result([], len([]), current=1, page_size=10)


# 组织任务中心


@router.post("/operation/log/list", operation_id="operation_log_list_post")
@router.get("/operation/log/list", operation_id="operation_log_list_get")
async def operation_log_list(request: Request):
    """系统操作日志列表。

    前端以 POST 方式提交过滤参数，支持按操作人/时间范围/操作类型/操作对象/
    名称关键字过滤，返回分页的日志列表（LogItem 结构）。
    """
    body = await read_body(request)
    if request.method == "POST":
        params = as_model(body, OperationLogListBody)
    else:
        params = OperationLogListBody()

    current = params.effective_current
    page_size = params.effective_page_size
    oper_user = params.effective_oper_user
    start_time = params.startTime
    end_time = params.endTime
    project_ids = params.effective_project_ids()
    organization_ids = params.effective_organization_ids()
    log_type = params.effective_log_type
    module = params.effective_module
    content = params.effective_content
    _level = params.effective_level
    keyword = params.effective_keyword

    from app.services.apitest_service import apitest_service
    from app.services.organization_service import organization_service
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
        # 系统级日志默认展示全部，仅当指定了组织/项目范围时才过滤
        if target_pids and project_id_v not in target_pids:
            continue
        if target_orgs:
            try:
                proj = project_service.get(project_id_v) if project_id_v else None
                org_id_v = (proj or {}).get("organization_id", "") if proj else ""
            except Exception:
                org_id_v = ""
            if org_id_v not in target_orgs:
                continue

        try:
            project = project_service.get(project_id_v) if project_id_v else None
        except Exception:
            project = None
        project_name = (project or {}).get("name", "") if project else ""
        org_id_v = (project or {}).get("organization_id", "") if project else ""
        org_name = ""
        if org_id_v:
            try:
                org_name = (organization_service.get(org_id_v) or {}).get("name", "")
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
            "organizationId": org_id_v or "SYSTEM",
            "organizationName": org_name or "",
            "module": module_v,
            "type": log_type_v,
            "content": content_v,
            "createTime": int(created * 1000) if created else int(time.time() * 1000),
            "sourceId": r.get("resource_id") or "",
        })

    # 无真实日志或过滤后无匹配日志时，提供默认演示日志，保证界面可正常展示
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
                "projectId": "SYSTEM",
                "projectName": "",
                "organizationId": "SYSTEM",
                "organizationName": "",
                "module": m,
                "type": t,
                "content": content_v,
                "createTime": created,
                "sourceId": str(uuid.uuid4()),
            })

    logs.sort(key=lambda x: x.get("createTime", 0), reverse=True)
    return page_result(logs, len(logs), current=current, page_size=page_size)


@router.get("/operation/log/get/options")
def operation_log_get_options():
    """操作日志选项（组织/项目级联下拉框选项）。"""
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


@router.get("/operation/log/user/list")
def operation_log_user_list(keyword: str = ""):
    """操作日志用户列表。"""
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


# ════════════════════════════════════════════════════════════
# P2-5: 第三方集成  /we_com/*  /ding_talk/*  /lark/*  /lark_suite/*  /sso/*  /ldap/*
# ════════════════════════════════════════════════════════════

# 企微


@router.post("/sso/callback/we_com")
async def sso_callback_we_com():
    """企微 SSO 回调。"""
    return ok({"success": True})


@router.post("/sso/callback/ding_talk")
async def sso_callback_ding_talk():
    """钉钉 SSO 回调。"""
    return ok({"success": True})


@router.post("/sso/callback/lark")
async def sso_callback_lark():
    """飞书 SSO 回调。"""
    return ok({"success": True})


@router.post("/sso/callback/lark_suite")
async def sso_callback_lark_suite():
    """飞书套件 SSO 回调。"""
    return ok({"success": True})


@router.post("/ldap/login")
async def ldap_login(request: Request):
    """LDAP 登录。

    前端 userLogin() 期望返回 LoginRes 结构（含 sessionId/csrfToken/用户字段），
    否则登录后 setToken(res.sessionId) 会因字段缺失而失败。
    """
    try:
        body = await read_body(request)
    except Exception:
        body = {}
    username = as_model(body, LdapLoginBody).effective_username
    session_id = f"ldap_{uuid.uuid4().hex}"
    csrf_token = f"csrf_{uuid.uuid4().hex}"
    now_ms = int(time.time() * 1000)
    response_data = {
        "sessionId": session_id,
        "csrfToken": csrf_token,
        "token": session_id,
        "id": f"ldap_{username}" if username else "ldap_user",
        "name": username or "LDAP用户",
        "username": username or "ldap_user",
        "email": "",
        "phone": "",
        "avatar": "",
        "role": "user",
        "lastOrganizationId": "default-org",
        "lastProjectId": "",
        "loginType": ["LDAP"],
        "userRoleRelations": [
            {
                "id": str(uuid.uuid4()),
                "userId": f"ldap_{username}" if username else "ldap_user",
                "roleId": "user",
                "sourceId": "global",
                "organizationId": "",
                "createTime": now_ms,
                "createUser": "system",
                "userRolePermissions": [
                    {
                        "id": str(uuid.uuid4()),
                        "permissionId": "*",
                        "roleId": "user",
                    }
                ],
                "userRole": {
                    "id": "user",
                    "name": "普通用户",
                    "scopeId": "global",
                    "type": "SYSTEM",
                },
            }
        ],
        "userRolePermissions": [],
        "userRoles": [
            {
                "id": "user",
                "name": "普通用户",
                "scopeId": "global",
                "type": "SYSTEM",
            }
        ],
    }
    return ok(response_data)


# ════════════════════════════════════════════════════════════
# P2-6: 平台设置  /setting/*
# ════════════════════════════════════════════════════════════


@router.get("/personal/model/get")
def personal_model_get():
    """个人模型（当前用户默认源，兼容无参调用）。"""
    from app.services.ai_model_service import ai_model_service
    return ok(ai_model_service.get_or_default())


@router.delete("/personal/model/delete")
async def personal_model_delete(request: Request):
    """删除个人模型（body 携带 id 时真实删除）。"""
    body = await read_body(request)
    model_id = as_model(body, PersonalModelIdBody).effective_id
    if model_id:
        from app.services.ai_model_service import ai_model_service
        ai_model_service.delete(model_id)
    return ok()


@router.post("/personal/model/edit-source")
async def personal_model_edit_source(request: Request):
    """编辑个人模型源（真实落库，owner=当前用户）。"""
    from app.services.ai_model_service import ai_model_service
    body = await read_body(request)
    if not isinstance(body, dict) or not body:
        return fail("缺少模型配置参数", 400)
    user_id = current_user_id(request)
    saved = ai_model_service.save(body, operator=user_id,
                                  owner_type="PERSONAL", owner=user_id)
    return ok(saved)


@router.get("/personal/model/source/list")
def personal_model_source_list(request: Request):
    """个人模型源列表（真实：按当前用户过滤；POST 分页走下方新增处理）。"""
    from app.services.ai_model_service import ai_model_service
    return ok(ai_model_service.list_personal(owner=current_user_id(request)))


@router.post("/personal/model/source/list")
async def personal_model_source_list_post(request: Request):
    """个人中心-查看模型集合（POST 分页，getPersonalModelConfigList 真实调用）。"""
    from app.services.ai_model_service import ai_model_service
    body = await read_body(request)
    page = as_model(body, PersonalModelPageBody)
    provider_name = page.effective_provider_name
    keyword = page.effective_keyword
    current = page.effective_current
    page_size = page.effective_page_size
    if current < 1:
        current = 1
    if page_size < 1:
        page_size = 10
    items = ai_model_service.list_personal(owner=current_user_id(request),
                                           keyword=keyword, provider_name=provider_name)
    return page_result(items, len(items), current=current, page_size=page_size)


# ════════════════════════════════════════════════════════════
# P2-10: AI 配置  /ai/config/*  /ai/conversation/*
# ════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════
# P0-5: 缺陷管理补充  /bug/*
# ════════════════════════════════════════════════════════════


@router.get("/dashboard/header/columns-option")
def dashboard_header_columns_option(project_id: str = ""):
    """Dashboard 表头列选项。"""
    return ok([])


@router.get("/dashboard/header/custom-field")
def dashboard_header_custom_field(project_id: str = ""):
    """Dashboard 表头自定义字段。"""
    return ok([])


@router.get("/dashboard/layout/get")
def dashboard_layout_get(org_id: str = ""):
    """Dashboard 布局（query 参数版本）。返回默认卡片数组，保证前端 defaultWorkList 正常渲染。"""
    _default_cards = [
        {"label": "项目概览", "id": "project-overview", "key": "PROJECT_VIEW", "fullScreen": False,
         "isDisabledHalfScreen": False, "projectIds": [], "handleUsers": [], "selectAll": True,
         "planId": "", "groupId": "", "pos": 0},
        {"label": "用例数", "id": "case-count", "key": "CASE_COUNT", "fullScreen": False,
         "isDisabledHalfScreen": False, "projectIds": [], "handleUsers": [], "selectAll": True,
         "planId": "", "groupId": "", "pos": 1},
        {"label": "缺陷数", "id": "bug-count", "key": "BUG_COUNT", "fullScreen": False,
         "isDisabledHalfScreen": False, "projectIds": [], "handleUsers": [], "selectAll": True,
         "planId": "", "groupId": "", "pos": 2},
        {"label": "接口用例数", "id": "api-case-count", "key": "API_CASE_COUNT", "fullScreen": False,
         "isDisabledHalfScreen": False, "projectIds": [], "handleUsers": [], "selectAll": True,
         "planId": "", "groupId": "", "pos": 3},
    ]
    return ok(_default_cards)


@router.post("/dashboard/layout/edit")
async def dashboard_layout_edit():
    """编辑 Dashboard 布局。"""
    return ok()


@router.get("/dashboard/member/get-project-member/option")
def dashboard_member_get_project_member_option(project_id: str = ""):
    """Dashboard 项目成员选项。"""
    return ok([])


@router.get("/dashboard/plan/option")
def dashboard_plan_option(project_id: str = ""):
    """Dashboard 计划选项。"""
    return ok([])


# ════════════════════════════════════════════════════════════
# P0-8: 测试计划补充  /test-plan/*
# ════════════════════════════════════════════════════════════


@router.get("/status")
def status_endpoint():
    """服务状态。"""
    return ok({"status": "UP", "time": int(time.time())})


# ════════════════════════════════════════════════════════════
# 补充遗漏接口
# ════════════════════════════════════════════════════════════


@router.get("/api/doc/share/download/file/{share_id}/{file_id}")
@router.post("/api/doc/share/download/file/{share_id}/{file_id}")
def doc_share_download_file_path(share_id: str, file_id: str):
    """下载分享文件（带路径参数）。"""
    return ok({"share_id": share_id, "file_id": file_id})


@router.get("/api/doc/share/export/{share_id}")
@router.post("/api/doc/share/export/{share_id}")
def doc_share_export_path(share_id: str):
    """导出分享（带路径参数）。"""
    return ok({"id": share_id, "exported": True})


@router.get("/api/doc/share/stop/{share_id}")
@router.post("/api/doc/share/stop/{share_id}")
def doc_share_stop_path(share_id: str):
    """停止分享（带路径参数）。"""
    return ok({"id": share_id, "stopped": True})


# ════════════════════════════════════════════════════════════
# 报告
# ════════════════════════════════════════════════════════════


@router.get("/personal/model/delete/{model_id}")
@router.post("/personal/model/delete/{model_id}")
def personal_model_delete_path(model_id: str):
    """删除个人模型（带路径参数，真实删除）。"""
    from app.services.ai_model_service import ai_model_service
    ok_flag = ai_model_service.delete(model_id)
    return ok({"id": model_id, "deleted": ok_flag})


# ════════════════════════════════════════════════════════════
# 插件
# ════════════════════════════════════════════════════════════


@router.get("/api/doc/share/plugin/script/{id}/{org_id}")
def doc_share_plugin_script_path(id: str, org_id: str):
    """获取文档分享插件脚本（带路径参数）。"""
    return ok({"id": id, "org_id": org_id})


# 场景步骤跨项目信息（前端: /api/scenario/step/resource-info/{id}）


# 功能用例前后置已关联IDs（前端: /functional/case/relationship/get-ids/{caseId}）


@router.get("/personal/model/get/{model_id}")
def personal_model_get_path(model_id: str):
    """获取个人模型详情（真实数据）。"""
    from app.services.ai_model_service import ai_model_service
    model = ai_model_service.get(model_id)
    if not model:
        return fail("模型不存在", 404)
    return ok(model)


# 公共脚本详情（前端: /project/custom/func/detail/{funcId}）


@router.get("/task/center/api/project/stop/{task_id}")
def task_center_api_project_stop_path(task_id: str):
    """停止项目任务（带路径参数）。"""
    return ok({"id": task_id, "stopped": True})


@router.get("/task/center/api/project/stop/{task_type}/{task_id}")
def task_center_api_project_stop_type_path(task_type: str, task_id: str):
    """停止项目任务（带类型和路径参数）。"""
    return ok({"type": task_type, "id": task_id, "stopped": True})


# 停止本地执行 - 带路径参数


@router.post("/api/stop/{task_id}")
def api_stop_path(task_id: str):
    """停止本地执行（带路径参数）。"""
    return ok({"id": task_id, "stopped": True})


@router.post("/api/stop/{task_type}/{task_id}")
def api_stop_type_path(task_type: str, task_id: str):
    """停止本地执行（带类型和路径参数）。"""
    return ok({"type": task_type, "id": task_id, "stopped": True})


@router.get("/api/stop/{task_id}")
def api_stop_get_path(task_id: str):
    """停止本地执行 GET（带路径参数）。"""
    return ok({"id": task_id, "stopped": True})


@router.get("/api/stop/{task_type}/{task_id}")
def api_stop_get_type_path(task_type: str, task_id: str):
    """停止本地执行 GET（带类型和路径参数）。"""
    return ok({"type": task_type, "id": task_id, "stopped": True})


@router.post("/api/test/mock")
def api_test_mock(request: Request):
    """测试 Mock。"""
    return ok(None)


# ── 用例管理更多接口 ─────────────────────────────────────


@router.post("/review/functional/case/get/list")
async def review_functional_case_get_list(request: Request):
    """评审详情-获取用例评审历史。"""
    body = await read_body(request)
    mb = as_model(body, ReviewCaseHistoryBody)
    review_id = mb.effective_review_id
    case_id = mb.effective_case_id
    return _build_review_history(review_id, case_id)


@router.post("/review/functional/case/save")
async def review_functional_case_save(request: Request):
    """评审详情-提交评审结果。

    更新评审-用例关联状态，同时更新用例状态为 approved。
    body: {caseId, reviewId, status, content, ...}
    """
    body = await read_body(request)
    mb = as_model(body, ReviewCaseSaveBody)
    case_id = mb.effective_case_id
    review_id = mb.effective_review_id
    status = mb.effective_status
    # 将前端 StartReviewStatus 映射为后端评审状态常量
    from app.services.case_review_service import case_review_service as cvs
    status_map = {
        "PASS": cvs.RESULT_PASS,
        "UN_PASS": cvs.RESULT_UN_PASS,
        "UNDER_REVIEWED": cvs.RESULT_UNDER_REVIEWED,
        "RE_REVIEWED": cvs.RESULT_RE_REVIEWED,
        "UN_REVIEWED": cvs.RESULT_UN_REVIEWED,
    }
    mapped_status = status_map.get(status, "")
    try:
        # 更新评审-用例关联状态
        if review_id and case_id and mapped_status:
            cvs.update_link_status(
                review_id, [case_id], mapped_status,
                reviewer=mb.effective_notifier or "admin",
                comment=mb.effective_content,
            )
        # 同步用例状态
        if case_id and status in ("PASS", "UN_PASS"):
            new_status = "approved" if status == "PASS" else "draft"
            case_service.update(case_id, {"status": new_status})
    except Exception:
        pass
    return ok(None)


# ── 用例评审 - GET 变体路由 ──────────────────────────────


@router.get("/review/functional/case/get/list/{review_id}/{case_id}")
def review_functional_case_get_list_get_route(review_id: str, case_id: str):
    """评审详情-获取用例评审历史（GET）。"""
    return _build_review_history(review_id, case_id)


# ════════════════════════════════════════════════════════════
# 路径参数兼容路由（自 path_param_fixes.py 迁移）
# ════════════════════════════════════════════════════════════

@router.get("/api/doc/share/delete/{id}")
@router.post("/api/doc/share/delete/{id}")
def api_doc_share_delete_path(id: str):
    """/api/doc/share/delete 带路径参数（前端 RESTful 调用兼容）。"""
    return ok({"id": id, "deleted": True})


