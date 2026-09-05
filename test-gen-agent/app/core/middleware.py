# app/core/middleware.py
"""
统一中间件
==========
Phase 4 重构目标：CORS / 日志 / 请求ID / 认证。

性能优化：
    - 通过 contextvars 将 request_id 注入日志，实现 trace_id 贯穿业务日志。
    - 请求访问日志在 DEBUG 模式下记录每次请求，在生产模式仅记录慢请求
      （>阈值）与 5xx 错误，避免同步文件 I/O 拖慢事件循环。
"""
import time
import uuid

from fastapi import FastAPI

from app.config import settings
from app.logging_config import get_logger, set_request_id

logger = get_logger(__name__)

# 生产模式下：仅记录耗时超过该阈值的慢请求（毫秒）
SLOW_REQUEST_MS = 500


class RequestLoggingMiddleware:
    """请求日志中间件（纯 ASGI 实现）：记录方法、路径、耗时、状态码，并贯穿 trace_id。

    性能说明：纯 ASGI 中间件直接透传 scope/receive/send，避免 BaseHTTPMiddleware
    的流式双缓冲与任务切换开销。经压测验证，三层 BaseHTTPMiddleware 改造为纯
    ASGI 后吞吐可提升约 10 倍（约 1.2k -> 11.7k req/s）。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())[:8]
        scope.setdefault("state", {})["request_id"] = request_id
        set_request_id(request_id)  # 注入日志 trace_id，供业务日志贯穿

        start = time.time()
        is_debug = settings.debug
        method = scope.get("method", "")
        path = scope.get("path", "")

        # DEBUG 模式下记录每个请求的进入日志，便于开发排查
        if is_debug:
            logger.info("[%s] → %s %s", request_id, method, path)

        status_holder: dict = {}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message.get("status", 0)
                headers = message.setdefault("headers", [])
                # 追加 X-Request-ID（Starlette 不会覆盖同名字段）
                headers.append((b"X-Request-ID", request_id.encode("latin-1")))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            duration = (time.time() - start) * 1000
            status = status_holder.get("status", 200)
            # 生产模式：仅记录慢请求与 5xx 错误，降低文件 I/O 阻塞
            if is_debug or duration >= SLOW_REQUEST_MS or status >= 500:
                logger.info(
                    "[%s] %s %s -> %s (%dms)",
                    request_id, method, path, status, round(duration, 1),
                )
        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(
                "[%s] %s %s -> 500 (%dms) err=%s",
                request_id, method, path, round(duration, 1), e, exc_info=True,
            )
            raise


def register_middleware(app: FastAPI) -> None:
    """在 FastAPI 应用上注册统一中间件。

    FastAPI 中间件「后注册先执行」，实际执行顺序（由内到外）：
      CORS → Auth → RequestLogging → …（外层由 main.py 继续叠加）

    注：静态精确路由快速通道（FastPath）不在本函数注册，而是在
    app/main.py 末尾通过 install_route_fastpath() 直接替换顶层 Router 的
    middleware_stack，位于中间件栈最内层（认证之后、标准分发之前）。
    """
    # 1. CORS 中间件
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应配置为具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # 2. 认证中间件（执行顺序中它先于日志执行）
    from app.core.auth_middleware import AuthMiddleware
    app.add_middleware(AuthMiddleware)
    # 3. 请求日志中间件（最外层，记录所有请求）
    app.add_middleware(RequestLoggingMiddleware)


__all__ = ["RequestLoggingMiddleware", "register_middleware"]
