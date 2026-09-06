# app/core/exceptions.py
"""
统一异常定义与全局异常处理
==========================
Phase 4 重构目标：替换各路由函数中冗余的 try-except，统一错误响应格式。
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.logging_config import get_logger

logger = get_logger(__name__)


# ── 上游依赖（LLM 等）错误的 HTTP 语义映射 ────────────────────
# 问题背景：LLM 配置错误（API Key 无效 / 额度耗尽 / 端点不可达）会以
# 异常形式冒泡到全局兜底处理器，被打成 500「服务器内部错误」。
# 但这类错误并非本服务故障 —— 它是「上游凭据或配额有问题」，
# 正确的语义是 502（Bad Gateway）或按上游状态码透传（如 401）。
# 前端拿到 500 只能提示「服务器开小差」，无法引导用户去配置页修 Key。
#
# 判定按「异常类型名 + 消息关键字」双重匹配，避免强依赖 openai /
# langchain 的具体导入路径（不同 provider 抛的异常类不同）。
_LLM_AUTH_MARKERS = (
    "AuthenticationError",      # openai.AuthenticationError
    "invalid_api_key",
    "Incorrect API key",
    "invalid x-api-key",
    "unauthorized",
    "PermissionDeniedError",
    "invalid_api_key_provided",
)

_LLM_QUOTA_MARKERS = (
    "RateLimitError",           # openai.RateLimitError
    "FreeUsageLimitError",
    "insufficient_quota",
    "quota exceeded",
    "exceeded your current quota",   # OpenAI 原文措辞
    "exceeded your monthly quota",
    "billing_hard_limit_reached",
    "rate_limit_exceeded",
    "too many requests",
)

_LLM_NOTFOUND_MARKERS = (
    "NotFoundError",
    "model_not_found",
    "The model does not exist",
    "does not have access to model",
)

_LLM_TIMEOUT_MARKERS = (
    "Timeout",
    "APITimeoutError",
    "timed out",
)


def classify_llm_error(exc: Exception) -> tuple:
    """把 LLM/上游异常归类为 (http_status, 人类可读原因)。

    返回 (0, "") 表示不是可识别的 LLM 错误，交由默认 500 处理。
    """
    type_name = type(exc).__name__
    msg = str(exc)
    haystack = f"{type_name} {msg}".lower()

    def _hit(markers):
        return any(m.lower() in haystack for m in markers)

    if _hit(_LLM_AUTH_MARKERS):
        return 401, "LLM 认证失败：API Key 无效或未配置，请在系统设置中配置正确的密钥"
    if _hit(_LLM_QUOTA_MARKERS):
        return 429, "LLM 额度/限流：请求过于频繁或配额已用尽，请稍后重试或更换密钥"
    if _hit(_LLM_NOTFOUND_MARKERS):
        return 404, "LLM 模型不可用：模型名称不存在或当前账号无权访问"
    if _hit(_LLM_TIMEOUT_MARKERS):
        return 504, "LLM 调用超时：上游响应过慢，请稍后重试或调整超时配置"
    return 0, ""


# ── 业务异常类 ──────────────────────────────────────────────

class AppError(Exception):
    """应用业务异常基类。"""

    def __init__(self, message: str = "操作失败", code: int = 400, data=None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message)


class NotFoundError(AppError):
    """资源不存在。"""

    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, code=404)


class AuthError(AppError):
    """未授权。"""

    def __init__(self, message: str = "未授权"):
        super().__init__(message, code=401)


class ForbiddenError(AppError):
    """无权限。"""

    def __init__(self, message: str = "无权限访问"):
        super().__init__(message, code=403)


class ValidationError(AppError):
    """参数验证失败。"""

    def __init__(self, message: str = "参数验证失败"):
        super().__init__(message, code=400)


class ConflictError(AppError):
    """资源冲突。"""

    def __init__(self, message: str = "资源冲突"):
        super().__init__(message, code=409)


# ── 全局异常处理器 ──────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """在 FastAPI 应用上注册全局异常处理器。"""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logger.warning("[%s %s] AppError: %s", request.method, request.url.path, exc.message)
        return JSONResponse(
            {
                "code": exc.code,
                "message": exc.message,
                "data": exc.data,
            },
            status_code=exc.code,
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            {"code": 404, "message": exc.message, "data": None},
            status_code=404,
        )

    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError):
        return JSONResponse(
            {"code": 401, "message": exc.message, "data": None},
            status_code=401,
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            {"code": 400, "message": exc.message, "data": None},
            status_code=400,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        """统一处理 FastAPI 请求参数校验失败（默认返回 422）。"""
        errors = exc.errors()
        # 提取第一个字段错误，生成可读消息
        field_msg = ""
        for err in errors:
            loc = err.get("loc", [])
            if loc:
                field_name = str(loc[-1])
                msg = err.get("msg", "")
                field_msg = f"参数「{field_name}」校验失败: {msg}"
                break
        if not field_msg:
            field_msg = "请求参数校验失败"
        logger.warning(
            "[%s %s] RequestValidationError: %s",
            request.method, request.url.path, field_msg,
        )
        return JSONResponse(
            {"code": 422, "message": field_msg, "data": None},
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # 先尝试按上游（LLM）错误归类，给出准确的状态码与可操作提示，
        # 避免把「Key 填错了」这类配置问题误报成服务器 500。
        status, reason = classify_llm_error(exc)
        if status:
            logger.warning(
                "[%s %s] 上游 LLM 错误 -> %s [reason=%s]",
                request.method, request.url.path, status, reason,
            )
            return JSONResponse(
                {"code": status, "message": reason, "data": None},
                status_code=status,
            )

        logger.error(
            "[%s %s] 未捕获异常: %s",
            request.method, request.url.path, exc, exc_info=True,
        )
        return JSONResponse(
            {"code": 500, "message": f"服务器内部错误: {str(exc)[:200]}", "data": None},
            status_code=500,
        )


__all__ = [
    "classify_llm_error",
    "AppError",
    "NotFoundError",
    "AuthError",
    "ForbiddenError",
    "ValidationError",
    "ConflictError",
    "register_exception_handlers",
]
