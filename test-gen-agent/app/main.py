# app/main.py
"""应用装配入口（Phase 3 重构：仅做应用装配，不含路由定义）。

所有业务路由已拆分至 app/routers/ 目录。
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭钩子。"""
    logger.info("🚀 应用启动中…")
    # 初始化基础种子数据（幂等）：确保组织/项目/用户/缺陷等基础数据存在
    from app.core.bootstrap import init_seed_data
    init_seed_data()
    # 预热 RSA 密钥：登录接口首次调用无需现场生成，避免首次登录卡顿
    from app.core.bootstrap import preheat_rsa_keys
    preheat_rsa_keys()
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db) as checkpointer:
        from app.graph.builder import build_graph
        app.state.graph = build_graph(checkpointer=checkpointer)
        # 注入全局应用上下文，供可恢复任务处理器访问
        from app.tasks.manager import set_app_context
        set_app_context("graph", app.state.graph)
        from app.tasks.manager import manager
        manager.start(num_workers=settings.task_workers)
        app.state.task_manager = manager
        logger.info("✅ 应用启动完成")
        yield
        try:
            await manager.stop()
        except Exception as e:
            logger.warning("停止任务队列失败: %s", e)
        logger.info("👋 应用关闭")


def _generate_unique_operation_id(route):
    """生成唯一 operation ID，避免同函数名路由冲突。"""
    path = route.path.replace('/', '_').replace('{', '').replace('}', '')
    method = ','.join(sorted(route.methods or []))
    return f"{method.lower()}_{path}_v1"


app = FastAPI(
    title="Test Generation Agent Toolkit",
    description="基于 FastAPI + LangGraph 的测试用例生成 Agent，开箱即用",
    version="0.2.0",
    lifespan=lifespan,
    generate_unique_id_function=_generate_unique_operation_id,
)

# ── 统一异常处理 / 中间件 ──────────────────────────────────
from app.core.exceptions import register_exception_handlers
from app.core.middleware import register_middleware

register_exception_handlers(app)
register_middleware(app)

# ── TestPilot 前端 /front/ 前缀路径重写 ────────────────────
# 纯 ASGI 中间件：在路由匹配前将 /front/ 前缀请求重写为根路径。
# 必须在原 scope 上就地修改 path 才能让后续路由匹配到重写后的路径；
# BaseHTTPMiddleware 中通过 scope.copy() 生成新 scope 的方式不生效，
# 会导致 /front/ 前缀的所有接口返回 404。此处保留就地修改语义。
class FrontPrefixMiddleware:
    """将 /front/ 前缀的请求路径重写为根路径（纯 ASGI 实现）。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path.startswith("/front/"):
            scope["path"] = "/" + path[len("/front/"):]
        elif path == "/front":
            from fastapi.responses import RedirectResponse
            response = RedirectResponse(url="/")
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

app.add_middleware(FrontPrefixMiddleware)


# ── 认证 / 基础模块 / 业务域 / 兜底路由统一装配 ─────────────
# 全部路由通过集中式路由注册表 RouterRegistry 装配，以「分组 + 优先级」
# 替代 main.py 历史上手写 include 的相对顺序依赖。
#
# 顺序约束由注册表分组保证：
#   core(认证/基础模块) -> business(业务域) -> catchall(兜底泛化路由)
# extra_router 含 `{suffix}` / `{project_id}` 等泛化参数路由，必须放在最后
# include —— 否则其参数段会抢先遮蔽 project_compat 等模块里的字面路由
# （Starlette 先注册先生效）。install() 内置遮蔽检测，装配期即可拦截。
# DDD 域路由导入：入口只依赖各限界上下文的 interfaces 层。
from app.domain.auth.interfaces.router import router as auth_router
from app.domain.file.interfaces.router import router as file_router
from app.domain.ai_config.interfaces.ai_config import router as ai_config_router
from app.domain.apitest.interfaces.apitest_router import router as apitest_router
from app.domain.apitest.interfaces.apitest_trash import router as apitest_trash_router
from app.domain.case_review.interfaces.case_review import router as case_review_router
from app.domain.datafactory.interfaces.datafactory import router as datafactory_router
from app.domain.environment.interfaces.environments_extra import router as environments_extra_router
from app.domain.frontend_api.interfaces.frontend_router import router as frontend_router
from app.domain.debug.interfaces.gap_fixes import router as gap_fixes_router
from app.domain.generation.interfaces.generation import router as generation_router
from app.domain.test_insight.interfaces.insights import router as insights_router
from app.domain.integration.interfaces.integrations import router as integrations_router
from app.domain.organization.interfaces.organizations import router as organizations_router
from app.domain.platform.interfaces.platform import router as platform_router
from app.domain.plugins.interfaces.plugins import router as plugins_router
from app.domain.project.interfaces.projects_scan import router as projects_scan_router
from app.domain.runs.interfaces.runs import router as runs_router
from app.domain.script.interfaces.scripts import router as scripts_router
from app.domain.admin_system.interfaces.system_router import router as system_router
from app.domain.task_center.interfaces.task_center import router as task_center_router
from app.domain.resource_pool.interfaces.test_resources import router as test_resources_router
from app.domain.frontend_api.interfaces.websocket_router import router as websocket_router
from app.domain.cases.interfaces.router import router as cases_router
from app.domain.defects.interfaces.router import router as defects_router
from app.domain.environment.interfaces.router import router as environments_router
from app.domain.project.interfaces.router import router as projects_router

from app.domain.identity.interfaces.log_router import router as identity_log_router
from app.domain.message.interfaces.router import router as message_router
from app.domain.template.interfaces.router import router as template_router
from app.domain.workflow.interfaces.router import router as workflow_router

from app.core.registry import (
    GROUP_BUSINESS,
    GROUP_CATCHALL,
    GROUP_CORE,
    PRIORITY_BUSINESS,
    PRIORITY_CATCHALL,
    PRIORITY_CORE,
    RouterRegistry,
)
from app.domain.test_plan.interfaces.router import router as test_plan_router
from app.domain.reports.interfaces.router import router as report_router

_router_registry = RouterRegistry()
_router_registry.add_group(
    GROUP_CORE,
    [
        ("auth", auth_router),
        ("test_plan", test_plan_router),
        ("report", report_router),
        ("file", file_router),
    ],
    priority=PRIORITY_CORE,
    note="认证与基础模块路由",
)
_router_registry.add_group(
    GROUP_BUSINESS,
    [
        ("ai_config", ai_config_router),
        ("apitest", apitest_router),
        ("apitest_trash", apitest_trash_router),
        ("cases", cases_router),
        ("case_review", case_review_router),
        ("datafactory", datafactory_router),
                ("defects", defects_router),
                ("environments", environments_router),
        ("frontend", frontend_router),
                ("gap_fixes", gap_fixes_router),
        ("generation", generation_router),
        ("insights", insights_router),
        ("integrations", integrations_router),
        # notifications 已拆分为 message 和 identity_log
        # ("notifications", notifications_router),
        # TODO: 注册 DDD 域路由
        ("message", message_router),
        ("identity_log", identity_log_router),
        ("organizations", organizations_router),
        ("platform", platform_router),
        ("plugins", plugins_router),
        ("template", template_router),
        ("workflow", workflow_router),
        ("projects", projects_router),
        ("projects_scan", projects_scan_router),
        ("runs", runs_router),
        ("scripts", scripts_router),
                ("system", system_router),
        ("task_center", task_center_router),
        ("test_resources", test_resources_router),
        ("websocket", websocket_router),
    ],
    priority=PRIORITY_BUSINESS,
    note="业务域路由（原生 + compat）",
)
_shadow_conflicts = _router_registry.install(app)
# 装配期遮蔽检测：把「参数化路由遮蔽同前缀字面路由」的注册顺序问题从
# 「靠人记注释」变成可自动验证、可在 CI 中断言的结构事实。检测结果挂到
# app.state.route_shadow_conflicts 供回归测试（tests/test_route_shadowing.py）
# 查询；其中由 extra_router / catch-all 泛化路由引起的遮蔽属本次装配硬化
# 的核心目标，绝不能出现 —— 一旦出现即视为启动异常。
#
# KNOWN_ROUTE_SHADOWING：仓库**既有**的少量历史遮蔽（与本次装配无关，待后续
# 收敛兼容层时一并清理）。它们仅打 warning 提示、不阻断启动；凡不在该集合内
# 的遮蔽（含未来新增、由 extra_router 顺序错乱引入的）一律 raise。
app.state.route_shadow_conflicts = _shadow_conflicts
if _shadow_conflicts:
    logger.warning(
        "检测到 %d 处路由遮蔽冲突（参数化路由遮蔽同前缀字面路由）：%s",
        len(_shadow_conflicts),
        "; ".join(
            f"[{c['method']}] {c['param_path']}({c['param_source']}) "
            f"遮蔽 {c['literal_path']}({c['literal_source']})"
            for c in _shadow_conflicts
        ),
    )
    _known = {
        ("GET", "/attachment/download/{file_id}", "/attachment/download/file"),
        ("GET", "/notice/message/task/get/{project_id}", "/notice/message/task/get/user"),
        ("GET", "/project/application/bug/platform/{org_id}", "/project/application/bug/platform/info/"),
        ("GET", "/project/application/case/platform/{org_id}", "/project/application/case/platform/info/"),
        ("GET", "/test-plan/report/share/get/{share_id}", "/test-plan/report/share/get/detail"),
    }
    _new = [c for c in _shadow_conflicts
            if (c["method"], c["param_path"], c["literal_path"]) not in _known]
    if _new:
        raise RuntimeError(
            "路由装配检测到**新增**遮蔽冲突（参数化路由遮蔽同前缀字面路由），"
            "请检查注册分组顺序或加入 KNOWN_ROUTE_SHADOWING。详情: "
            + "; ".join(
                f"[{c['method']}] {c['param_path']} 遮蔽 {c['literal_path']}"
                for c in _new
            )
        )


# ── TestPilot 前端（构建产物）服务 ─────────────────────────
# 当仓库中存在 frontend/dist 构建产物时，通过 /ms/ 前缀对外提供。
#
# ⚠️ 关键约束：SPA 回退路由 `/ms/{full_path:path}` 是 catch-all，
# 必须保证它之前没有其他更宽的路径抢先匹配，且它自己要注册在最后。
# 历史 Bug：`app/routers/system.py` 曾注册同名的 `GET /ms` 与
# `GET /ms/{full_path:path}`（占位透传），而 system_router 在业务路由阶段
# 就已 include，导致 /ms/xxx 全部返回 application/json 的占位响应而不是
# index.html —— 浏览器把 JSON 当页面渲染，前端直接白屏。
# 现已删除 system.py 的重复定义，并由
# tests/test_ms_frontend_serving.py 做回归防护。
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MS_FRONTEND_DIST = os.path.join(BASE_DIR, "..", "frontend", "dist")

if os.path.isdir(MS_FRONTEND_DIST):
    # 同时挂载 /assets 和 /ms/assets，兼容绝对路径与相对路径引用
    app.mount("/ms/assets", StaticFiles(directory=os.path.join(MS_FRONTEND_DIST, "assets")), name="ms_assets")
    app.mount("/assets", StaticFiles(directory=os.path.join(MS_FRONTEND_DIST, "assets")), name="assets")
    app.mount("/ms/images", StaticFiles(directory=os.path.join(MS_FRONTEND_DIST, "images")), name="ms_images")
    app.mount("/images", StaticFiles(directory=os.path.join(MS_FRONTEND_DIST, "images")), name="images")
    app.mount("/ms/templates", StaticFiles(directory=os.path.join(MS_FRONTEND_DIST, "templates")), name="ms_templates")

    # favicon 必须注册在 SPA catch-all 之前，否则会被回退成 index.html，
    # 浏览器拿到 HTML 当图标解析，控制台会刷一条 404/解析错误。
    @app.get("/ms/favicon.ico", include_in_schema=False)
    def ms_favicon():
        """前端 favicon；产物缺失时返回 204，不干扰页面加载。"""
        from fastapi.responses import FileResponse, Response
        ico = os.path.join(MS_FRONTEND_DIST, "favicon.ico")
        if os.path.isfile(ico):
            return FileResponse(ico, media_type="image/x-icon")
        return Response(status_code=204)

# SPA 回退路由必须始终注册（无论 dist 是否存在），
# 否则 CI 环境无构建产物时路由不存在，前端白屏回归检测无法拦截。
@app.get("/ms", response_class=HTMLResponse)
@app.get("/ms/{full_path:path}", response_class=HTMLResponse)
def ms_frontend(full_path: str = ""):
    """服务 TestPilot 前端（SPA，路由回退到 index.html）。

    前端以 /front/ 前缀发起的 API 请求由部署层（nginx/Vite 代理）
    重写转发到现有后端 /api/，此处仅提供前端页面与静态资源。
    产物缺失时返回 404 JSON。
    """
    index_file = os.path.join(MS_FRONTEND_DIST, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as fh:
            html = fh.read()
            # 将绝对路径 /assets/ 和 /images/ 重写为 /ms/assets/ 和 /ms/images/
            html = html.replace('src="/assets/', 'src="/ms/assets/')
            html = html.replace('href="/assets/', 'href="/ms/assets/')
            html = html.replace('srcset="/assets/', 'srcset="/ms/assets/')
            html = html.replace('"/assets/', '"/ms/assets/')
            # index.html 里 favicon 是 ./favicon.ico 相对引用，
            # 在 /ms/workbench 这类子路径下会解析成 /ms/./favicon.ico，
            # 统一改成绝对路径，避免每个页面控制台刷一条 404。
            html = html.replace('href="./favicon.ico"', 'href="/ms/favicon.ico"')
            html = html.replace('href="./assets/', 'href="/ms/assets/')
            return HTMLResponse(html)
    return JSONResponse({"code": 404, "message": "frontend not built", "data": None}, status_code=404)


# ── 静态精确路由快速通道 ─────────────────────────────────────
# 2000+ 兼容路由线性匹配导致静态路由请求每次需扫描上千条路由（毫秒级）。
# 在全部路由注册完成后安装哈希快速通道：静态精确路由 O(1) 命中，
# path 参数路由 / 重复尾项自动回退标准分发，行为零变化。
from app.core.fastpath import install_route_fastpath

install_route_fastpath(app)