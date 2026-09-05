# app/routers/extra_router.py
"""前端缺失的额外 API 路由补充（Phase D 从 main.py 拆出）。

保留未被 project_compat 等真实实现覆盖的补充路由，作为「具体模块后缀实现」的
通用兜底。⚠️ 该 router 必须由 main.py 在**所有业务 router 之后** include，
否则其中 `{suffix}` / `{project_id}` 参数路由会抢先遮蔽 project_compat 中
具体的模块字面路由（Starlette 先注册先生效）。
"""

from fastapi import APIRouter

from app.core.response import ok
from app.models.app_config import (
    ProjectAppConfigGetBody,
    ProjectAppConfigUpdateBody,
)
from app.services.project_app_config_service import project_app_config_service

router = APIRouter(tags=["extra-frontend-apis"])


# ── 项目应用配置 - 各模块默认配置与菜单后缀映射 ─────────────────
_MODULE_CONFIG_DEFAULTS = {
    "workstation": {
        "WORKSTATION_SYNC_RULE": True,
    },
    "test-plan": {
        "TEST_PLAN_CLEAN_REPORT": "3M",
        "TEST_PLAN_SHARE_REPORT": "1D",
    },
    "bug": {
        "BUG_SYNC_SYNC_ENABLE": False,
    },
    "case": {
        "CASE_PUBLIC": True,
        "CASE_RE_REVIEW": True,
        "CASE_RELATED_CASE_ENABLE": False,
        "CASE_RELATED": True,
    },
    "api": {
        "API_CLEAN_REPORT": "3M",
        "API_SHARE_REPORT": "1D",
        "API_RESOURCE_POOL_ID": "",
        "API_SCRIPT_REVIEWER_ID": "",
        "API_URL_REPEATABLE": True,
        "API_SYNC_CASE": True,
    },
    "ui": {
        "UI_CLEAN_REPORT": "3M",
        "UI_SHARE_REPORT": "1D",
        "UI_RESOURCE_POOL_ID": "",
    },
    "task": {
        "TASK_CLEAN_REPORT": "3M",
        "TASK_RECORD": "3M",
    },
    "performance-test": {
        "PERFORMANCE_TEST_CLEAN_REPORT": "3M",
        "PERFORMANCE_TEST_SHARE_REPORT": "1D",
        "PERFORMANCE_TEST_SCRIPT_REVIEWER_ENABLE": True,
        "PERFORMANCE_TEST_SCRIPT_REVIEWER_ID": "",
    },
}

# 前端菜单类型后缀 -> project_app_configs 模块名映射
_MENU_SUFFIX_TO_MODULE = {
    "workstation": "workstation",
    "test-plan": "testPlan",
    "testPlan": "testPlan",
    "bug": "bugManagement",
    "bugManagement": "bugManagement",
    "case": "caseManagement",
    "caseManagement": "caseManagement",
    "api": "apiTest",
    "apiTest": "apiTest",
    "ui": "uiTest",
    "uiTest": "uiTest",
    "task": "taskCenter",
    "taskCenter": "taskCenter",
    "performance-test": "loadTest",
    "loadTest": "loadTest",
}


def _merge_module_config(project_id: str, suffix: str) -> dict:
    """合并真实存储配置与默认配置，返回前端所需配置项。"""
    module = _MENU_SUFFIX_TO_MODULE.get(suffix, suffix)
    # 真实存储配置（含默认值）
    stored = {}
    try:
        stored = project_app_config_service.get_module_config(project_id, module) if project_id else {}
    except Exception:
        stored = {}
    # 合并 _MODULE_CONFIG_DEFAULTS 中存储未覆盖的额外 key，保证前端不丢字段
    merged = dict(stored)
    for k, v in _MODULE_CONFIG_DEFAULTS.get(suffix, {}).items():
        merged.setdefault(k, v)
    return merged


@router.get("/project/application/module-setting/{project_id}")
def extra_module_setting(project_id: str):
    """模块设置。返回项目管理-菜单管理所需的模块列表。"""
    menu_modules = [
        {"module": "workstation", "moduleEnable": True},
        {"module": "testPlan", "moduleEnable": True},
        {"module": "bugManagement", "moduleEnable": True},
        {"module": "caseManagement", "moduleEnable": True},
        {"module": "apiTest", "moduleEnable": True},
        {"module": "uiTest", "moduleEnable": True},
        {"module": "taskCenter", "moduleEnable": True},
        {"module": "loadTest", "moduleEnable": True},
    ]
    return ok(menu_modules)


@router.get("/project/application/{project_id}")
def extra_project_application(project_id: str):
    """项目应用配置。"""
    return ok({})


@router.post("/project/application/{suffix}")
async def extra_project_application_by_suffix(suffix: str, body: ProjectAppConfigGetBody):
    """按菜单类型获取项目应用配置。前端 menuManagement 展开某模块时调用。"""
    project_id = body.effective_project_id
    data = _merge_module_config(project_id, suffix)
    return ok(data)


@router.post("/project/application/update/{project_id}")
async def extra_project_application_update(project_id: str, body: ProjectAppConfigUpdateBody):
    """更新项目应用配置。

    注意：前端路径为 /project/application/update/{suffix}，故路径参数实际是菜单类型后缀；
    projectId 通过请求体传递。将配置真实持久化到 project_app_configs 存储。
    """
    suffix = project_id  # 路径参数实际为菜单类型后缀
    module = _MENU_SUFFIX_TO_MODULE.get(suffix, suffix)
    pid = body.effective_project_id
    cfg_type = body.type
    cfg_value = body.typeValue
    if pid and cfg_type:
        project_app_config_service.save_module_config(pid, module, {cfg_type: cfg_value})
    # 返回更新后的配置（合并默认）
    data = _merge_module_config(pid, suffix)
    return ok(data)


@router.post("/project/application/validate/{project_id}")
def extra_project_application_validate(project_id: str):
    """验证项目应用（占位接口，不消费请求体字段）。"""
    return ok({})


__all__ = ["router"]
