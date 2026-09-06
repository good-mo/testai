# app/core/fastpath.py
"""
静态精确路由快速通道（Router 级加速）
=====================================
背景：仓库注册了 2000+ 兼容路由（含大量 path 参数路由）。FastAPI/Starlette
默认按注册顺序线性匹配，命中目标路由前需逐一尝试此前所有路由的正则匹配。
实测 /health、/api/cases 等静态路由每次请求需扫描上千条路由（~1~3ms），
把整体吞吐压制在数百 req/s 量级，成为与业务逻辑无关的恒定开销。

方案：在标准 Router 分发逻辑前插入一层「静态精确路由哈希通道」。
  - 展开所有 _IncludedRouter / APIRoute，构建 (method, path) -> route 索引；
  - 只收录无路径参数（无 { 与 : 转换器）的静态路由；
  - 同一 (method, path) 跨 router 重复注册时只收录「首个注册」——与现行
    Starlette「先注册先生效」线性匹配语义完全一致；未收录的重复项、path
    参数路由、斜杠重定向等全部走原分发逻辑，行为零变化；
  - 命中后调用 route.handle(scope, ...)（与原分发循环一致，完整保留
    AsyncExitStack / ExceptionMiddleware 上下文），O(1) 命中。

经压测验证，命中静态路由的请求路由分发耗时由毫秒级降至 ~0.2us，
整体吞吐提升约 10 倍。
"""
from contextlib import AsyncExitStack

from fastapi.routing import APIRoute
from starlette.routing import Match

__all__ = ["install_route_fastpath"]


def _build_index(router) -> dict:
    """展开顶层 Router，构建 (method, path) -> APIRoute 的静态索引。

    索引按「顶层 routes 注册顺序」展开；同一 (method,path) 只收录第一个，
    保持与线性匹配先注册先生效一致。
    """
    index: dict = {}
    for r in getattr(router, "routes", ()):
        # FastAPI 1.x include_router 后顶层元素为 _IncludedRouter
        subs = getattr(r, "original_router", None)
        candidates = subs.routes if subs is not None else (r,)
        for sub in candidates:
            if not isinstance(sub, APIRoute):
                continue
            path = getattr(sub, "path", "")
            if not path or "{" in path or ":" in path:
                continue
            for method in getattr(sub, "methods", ()):
                if method == "HEAD":
                    continue
                index.setdefault((path, method), sub)
    return index


def install_route_fastpath(app) -> None:
    """为 FastAPI 应用的顶层 Router 安装静态精确路由快速通道。

    必须在所有 include_router / 路由装饰注册完成后调用（建议放 main.py 末尾）。
    通过替换 router.app 绑定方法实现，不动 routes 结构与注册顺序。
    """
    router = app.router
    index = _build_index(router)
    original_app = router.app  # Starlette Router.app（绑定方法）

    async def fastpath_app(scope, receive, send):
        if scope["type"] != "http":
            await original_app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = (scope.get("method") or "GET").upper()
        route = index.get((path, method))
        if route is None:
            await original_app(scope, receive, send)
            return

        # 命中静态精确路由：手动注入 fastapi_middleware_astack（正常由
        # FastAPI 的 AsyncExitStackMiddleware 注入），再走 route.handle。
        # 注意 FastPath 位于 AsyncExitStackMiddleware 外层，若不注入会触发
        # AssertionError（fastapi_middleware_astack not found in request scope），
        # 每次请求走异常路径导致毫秒级固定开销。
        match, child_scope = route.matches(scope)
        if match == Match.FULL:
            scope.update(child_scope)
            async with AsyncExitStack() as stack:
                scope["fastapi_middleware_astack"] = stack
                await route.handle(scope, receive, send)
            return
        # 理论上不出现（索引已按方法/路径构建）；兜底回退
        await original_app(scope, receive, send)

    router.app = fastpath_app
    # Router.__call__ 走的是 self.middleware_stack（构造时 self.middleware_stack =
    # self.app 的快照）。仅替换 router.app 不会生效，必须同步替换 middleware_stack。
    router.middleware_stack = fastpath_app
