# app/routers/project_compat_application.py
"""project_compat 拆分：项目应用设置 /project/application/*（P4 超大文件拆分）。

自 app/routers/project_compat.py 按业务域搬移，纯路由搬移、行为不变，
响应沿用统一 ok()/fail()/_paginate() 与 read_body() 辅助函数。
数据访问统一经 app.services.project_app_config_service，不再直接触碰
旧 app.projects.application_config 模块。
"""

from fastapi import APIRouter, Body

from app.core.response import ok
from app.logging_config import get_logger
from app.models.app_config import (
    ProjectAppConfigGetBody,
    ProjectAppConfigUpdateBody,
    ProjectAppPlatformSyncBody,
)
from app.services.project_app_config_service import project_app_config_service

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-project-application"])


@router.get("/project/application/{suffix}/resource/pool/{project_id}")
def project_application_resource_pool_get(suffix: str, project_id: str):
    """项目应用资源池选项（返回 PoolOption[]）。"""
    return ok([
        {"id": "local", "name": "本地资源池"},
        {"id": "default", "name": "默认资源池"},
    ])

@router.get("/project/application/{suffix}/user/{project_id}")
def project_application_user_get(suffix: str, project_id: str):
    """项目应用用户选项（脚本审核人/成员）。"""
    try:
        from app.services.auth_service import auth_service
        users = auth_service.list_users(limit=10000)
        return ok([
            {"id": u["id"], "name": u.get("name", u.get("username", u["id"]))}
            for u in users
        ])
    except Exception:
        return ok([])

@router.get("/project/application/")
def project_application(project_id: str = ""):
    """项目应用设置。"""
    return ok([])

@router.get("/project/application/bug/platform/")
@router.get("/project/application/bug/platform/{org_id}")
def project_application_bug_platform(org_id: str = "", project_id: str = ""):
    """缺陷平台下拉选项。"""
    return ok([
        {"id": "jira", "name": "JIRA"},
        {"id": "tapd", "name": "TAPD"},
        {"id": "zentao", "name": "禅道"},
    ])

@router.get("/project/application/bug/platform/info/")
@router.get("/project/application/bug/platform/info/{plugin_id}")
def project_application_bug_platform_info(plugin_id: str = "", project_id: str = ""):
    """缺陷平台插件表单字段。"""
    return ok({"formItems": []})

@router.get("/project/application/bug/sync/info/")
@router.get("/project/application/bug/sync/info/{project_id}")
def project_application_bug_sync_info(project_id: str = ""):
    """缺陷同步信息。读取已持久化的同步配置。"""
    if project_id:
        cfg = project_app_config_service.get_module_config(project_id, "bugManagement")
        return ok({
            "platform_key": cfg.get("BUG_PLATFORM_KEY", ""),
            "bug_platform_config": cfg.get("BUG_PLATFORM_CONFIG", "{}"),
            "sync_enable": cfg.get("BUG_SYNC_SYNC_ENABLE", False),
            "cron_expression": cfg.get("BUG_SYNC_CRON_EXPRESSION", ""),
        })
    return ok({
        "platform_key": "",
        "bug_platform_config": "{}",
        "sync_enable": False,
        "cron_expression": "",
    })

@router.get("/project/application/case/platform/")
@router.get("/project/application/case/platform/{org_id}")
def project_application_case_platform(org_id: str = "", project_id: str = ""):
    """用例平台下拉选项。"""
    return ok([
        {"id": "tapd", "name": "TAPD"},
        {"id": "jira", "name": "JIRA"},
    ])

@router.get("/project/application/case/platform/info/")
@router.get("/project/application/case/platform/info/{plugin_id}")
def project_application_case_platform_info(plugin_id: str = "", project_id: str = ""):
    """用例平台插件表单字段。"""
    return ok({"formItems": []})

@router.get("/project/application/case/related/info/")
@router.get("/project/application/case/related/info/{project_id}")
def project_application_case_related_info(project_id: str = ""):
    """用例关联需求信息。读取已持久化的关联配置。"""
    if project_id:
        cfg = project_app_config_service.get_module_config(project_id, "caseManagement")
        return ok({
            "demand_platform_config": cfg.get("CASE_PLATFORM_CONFIG", ""),
            "platform_key": cfg.get("CASE_PLATFORM_KEY", ""),
            "case_enable": cfg.get("CASE_PUBLIC", "false"),
            "sync_enable": cfg.get("CASE_RELATED_CASE_ENABLE", "false"),
            "cron_expression": cfg.get("CASE_RELATED_CRON_EXPRESSION", ""),
        })
    return ok({
        "demand_platform_config": "",
        "platform_key": "",
        "case_enable": "false",
        "sync_enable": "false",
        "cron_expression": "",
    })

@router.get("/project/application/module-setting/")
def project_application_module_setting(project_id: str = ""):
    """模块设置（菜单管理列表）。"""
    return ok(project_app_config_service.get_all_modules(project_id))

@router.post("/project/application/workstation")
def project_application_workstation(body: ProjectAppConfigGetBody = Body(default=None)):
    """工作台应用配置。"""
    project_id = body.effective_project_id if body else ""
    return ok(project_app_config_service.get_module_config(project_id, "workstation"))

@router.post("/project/application/test-plan")
def project_application_test_plan(body: ProjectAppConfigGetBody = Body(default=None)):
    """测试计划应用配置。"""
    project_id = body.effective_project_id if body else ""
    return ok(project_app_config_service.get_module_config(project_id, "testPlan"))

@router.post("/project/application/bug")
def project_application_bug(body: ProjectAppConfigGetBody = Body(default=None)):
    """缺陷管理应用配置。"""
    project_id = body.effective_project_id if body else ""
    return ok(project_app_config_service.get_module_config(project_id, "bugManagement"))

@router.post("/project/application/case")
def project_application_case(body: ProjectAppConfigGetBody = Body(default=None)):
    """用例管理应用配置。"""
    project_id = body.effective_project_id if body else ""
    return ok(project_app_config_service.get_module_config(project_id, "caseManagement"))

@router.post("/project/application/api")
def project_application_api(body: ProjectAppConfigGetBody = Body(default=None)):
    """接口测试应用配置。"""
    project_id = body.effective_project_id if body else ""
    config = project_app_config_service.get_module_config(project_id, "apiTest")
    # 误报规则启用数量
    try:
        from app.routers.test_compat import get_enabled_fake_count
        config["ENABLE_FAKE_ERROR_NUM"] = get_enabled_fake_count(project_id)
    except Exception:
        config["ENABLE_FAKE_ERROR_NUM"] = 0
    return ok(config)

@router.post("/project/application/ui")
def project_application_ui(body: ProjectAppConfigGetBody = Body(default=None)):
    """UI测试应用配置。"""
    project_id = body.effective_project_id if body else ""
    return ok(project_app_config_service.get_module_config(project_id, "uiTest"))

@router.post("/project/application/task")
def project_application_task(body: ProjectAppConfigGetBody = Body(default=None)):
    """任务中心应用配置。"""
    project_id = body.effective_project_id if body else ""
    return ok(project_app_config_service.get_module_config(project_id, "taskCenter"))

@router.post("/project/application/performance-test")
def project_application_performance_test(body: ProjectAppConfigGetBody = Body(default=None)):
    """性能测试应用配置。"""
    project_id = body.effective_project_id if body else ""
    return ok(project_app_config_service.get_module_config(project_id, "loadTest"))

@router.post("/project/application/update/")
def project_application_update(project_id: str = ""):
    """更新项目应用设置。"""
    return ok()

@router.post("/project/application/update/workstation")
def project_application_update_workstation(body: ProjectAppConfigUpdateBody = Body(default=None)):
    """更新工作台应用配置。"""
    project_id = body.effective_project_id if body else ""
    cfg_type = body.type if body else ""
    cfg_value = body.typeValue if body else ""
    cfg = {cfg_type: cfg_value} if cfg_type else {}
    project_app_config_service.save_module_config(project_id, "workstation", cfg)
    return ok(project_app_config_service.get_module_config(project_id, "workstation"))

@router.post("/project/application/update/test-plan")
def project_application_update_test_plan(body: ProjectAppConfigUpdateBody = Body(default=None)):
    """更新测试计划应用配置。"""
    project_id = body.effective_project_id if body else ""
    cfg_type = body.type if body else ""
    cfg_value = body.typeValue if body else ""
    cfg = {cfg_type: cfg_value} if cfg_type else {}
    project_app_config_service.save_module_config(project_id, "testPlan", cfg)
    return ok(project_app_config_service.get_module_config(project_id, "testPlan"))

@router.post("/project/application/update/bug")
def project_application_update_bug(body: ProjectAppConfigUpdateBody = Body(default=None)):
    """更新缺陷管理应用配置。"""
    project_id = body.effective_project_id if body else ""
    cfg_type = body.type if body else ""
    cfg_value = body.typeValue if body else ""
    cfg = {cfg_type: cfg_value} if cfg_type else {}
    project_app_config_service.save_module_config(project_id, "bugManagement", cfg)
    return ok(project_app_config_service.get_module_config(project_id, "bugManagement"))

@router.post("/project/application/update/case")
def project_application_update_case(body: ProjectAppConfigUpdateBody = Body(default=None)):
    """更新用例管理应用配置。"""
    project_id = body.effective_project_id if body else ""
    cfg_type = body.type if body else ""
    cfg_value = body.typeValue if body else ""
    cfg = {cfg_type: cfg_value} if cfg_type else {}
    project_app_config_service.save_module_config(project_id, "caseManagement", cfg)
    return ok(project_app_config_service.get_module_config(project_id, "caseManagement"))

@router.post("/project/application/update/api")
def project_application_update_api(body: ProjectAppConfigUpdateBody = Body(default=None)):
    """更新接口测试应用配置。"""
    project_id = body.effective_project_id if body else ""
    cfg_type = body.type if body else ""
    cfg_value = body.typeValue if body else ""
    cfg = {cfg_type: cfg_value} if cfg_type else {}
    project_app_config_service.save_module_config(project_id, "apiTest", cfg)
    return ok(project_app_config_service.get_module_config(project_id, "apiTest"))

@router.post("/project/application/update/ui")
def project_application_update_ui(body: ProjectAppConfigUpdateBody = Body(default=None)):
    """更新UI测试应用配置。"""
    project_id = body.effective_project_id if body else ""
    cfg_type = body.type if body else ""
    cfg_value = body.typeValue if body else ""
    cfg = {cfg_type: cfg_value} if cfg_type else {}
    project_app_config_service.save_module_config(project_id, "uiTest", cfg)
    return ok(project_app_config_service.get_module_config(project_id, "uiTest"))

@router.post("/project/application/update/task")
def project_application_update_task(body: ProjectAppConfigUpdateBody = Body(default=None)):
    """更新任务中心应用配置。"""
    project_id = body.effective_project_id if body else ""
    cfg_type = body.type if body else ""
    cfg_value = body.typeValue if body else ""
    cfg = {cfg_type: cfg_value} if cfg_type else {}
    project_app_config_service.save_module_config(project_id, "taskCenter", cfg)
    return ok(project_app_config_service.get_module_config(project_id, "taskCenter"))

@router.post("/project/application/update/performance-test")
def project_application_update_performance_test(body: ProjectAppConfigUpdateBody = Body(default=None)):
    """更新性能测试应用配置。"""
    project_id = body.effective_project_id if body else ""
    cfg_type = body.type if body else ""
    cfg_value = body.typeValue if body else ""
    cfg = {cfg_type: cfg_value} if cfg_type else {}
    project_app_config_service.save_module_config(project_id, "loadTest", cfg)
    return ok(project_app_config_service.get_module_config(project_id, "loadTest"))

@router.post("/project/application/update/bug/sync/{project_id}")
@router.post("/project/application/update/bug/sync/")
async def project_application_update_bug_sync(
    body: ProjectAppPlatformSyncBody = Body(default=None), project_id: str = ""):
    """更新缺陷同步设置。"""
    if project_id and body:
        cfg = {
            "BUG_PLATFORM_KEY": body.PLATFORM_KEY,
            "BUG_PLATFORM_CONFIG": body.BUG_PLATFORM_CONFIG,
        }
        project_app_config_service.save_module_config(project_id, "bugManagement", cfg)
    return ok(body.model_dump() if body else {})

@router.post("/project/application/update/case/related/{project_id}")
@router.post("/project/application/update/case/related/")
async def project_application_update_case_related(
    body: ProjectAppPlatformSyncBody = Body(default=None), project_id: str = ""):
    """更新用例关联设置。"""
    if project_id and body:
        cfg = {
            "CASE_PLATFORM_KEY": body.PLATFORM_KEY,
            "CASE_PLATFORM_CONFIG": body.CASE_PLATFORM_CONFIG,
        }
        project_app_config_service.save_module_config(project_id, "caseManagement", cfg)
    return ok(body.model_dump() if body else {})

@router.post("/project/application/validate/")
def project_application_validate(project_id: str = ""):
    """校验应用设置。"""
    return ok()
