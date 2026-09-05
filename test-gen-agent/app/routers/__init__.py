# app/routers/__init__.py
"""路由层：按业务域拆分的 FastAPI 路由（Phase 3 目标架构）。

每个路由文件对应一个业务域，替代 main.py 中的内联路由。
迁移完成前，main.py 中的内联路由仍然有效（向后兼容）。

兼容/历史路由（由 app/adapters/domains/ 对应模块迁移而来）：
  * _compat 文件承载历史 RESTful 调用与旧格式兼容路由。
"""
from app.routers.ai_config import router as ai_config_router
from app.routers.apitest import router as apitest_router
from app.routers.apitest_compat import router as apitest_compat_router
from app.routers.apitest_trash import router as apitest_trash_router
from app.routers.attachment import router as attachment_router
from app.routers.auth_compat import router as auth_compat_router
from app.routers.case_review import router as case_review_router
from app.routers.cases import router as cases_router
from app.routers.datafactory import router as datafactory_router
from app.routers.debug_compat import router as debug_compat_router
from app.routers.defects import router as defects_router
from app.routers.defects_compat import router as defects_compat_router
from app.routers.defects_compat_extra import router as defects_compat_extra_router
from app.routers.environments import router as environments_router
from app.routers.environments_extra import router as environments_extra_router
from app.routers.frontend import router as frontend_router
from app.routers.functional_cases import router as functional_cases_router
from app.routers.functional_cases_extra import router as functional_cases_extra_router
from app.routers.gap_fixes import router as gap_fixes_router
from app.routers.generation import router as generation_router
from app.routers.insights import router as insights_router
from app.routers.integrations import router as integrations_router
from app.routers.method_compat import router as method_compat_router
from app.routers.notifications import router as notifications_router
from app.routers.organizations import router as organizations_router
from app.routers.other_compat import router as other_compat_router
from app.routers.platform import router as platform_router
from app.routers.plugins import router as plugins_router
from app.routers.project_compat import router as project_compat_router
from app.routers.projects import router as projects_router
from app.routers.projects_scan import router as projects_scan_router
from app.routers.reports import router as reports_router
from app.routers.reports_compat import router as reports_compat_router
from app.routers.runs import router as runs_router
from app.routers.scripts import router as scripts_router
from app.routers.system import router as system_router
from app.routers.system_compat import router as system_compat_router
from app.routers.system_compat_extra import router as system_compat_extra_router
from app.routers.system_compat_userrole import router as system_compat_userrole_router
from app.routers.task_center import router as task_center_router
from app.routers.test_compat import router as test_compat_router
from app.routers.test_resources import router as test_resources_router
from app.routers.websocket import router as websocket_router

__all__ = [
    "ai_config_router",
    "apitest_router",
    "apitest_trash_router",
    "apitest_compat_router",
    "attachment_router",
    "auth_compat_router",
    "cases_router",
    "case_review_router",
    "datafactory_router",
    "debug_compat_router",
    "defects_router",
    "defects_compat_router",
    "defects_compat_extra_router",
    "environments_router",
    "environments_extra_router",
    "frontend_router",
    "functional_cases_router",
    "functional_cases_extra_router",
    "gap_fixes_router",
    "generation_router",
    "insights_router",
    "integrations_router",
    "method_compat_router",
    "notifications_router",
    "organizations_router",
    "other_compat_router",
    "platform_router",
    "plugins_router",
    "project_compat_router",
    "projects_router",
    "projects_scan_router",
    "reports_router",
    "reports_compat_router",
    "runs_router",
    "scripts_router",
    "system_router",
    "system_compat_router",
    "system_compat_userrole_router",
    "system_compat_extra_router",
    "task_center_router",
    "test_compat_router",
    "test_resources_router",
    "websocket_router",
]
