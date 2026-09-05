"""全局认证中间件。

为所有业务接口提供统一鉴权保护，仅放行白名单路径（登录、公钥获取等）。
"""
import re
import secrets

from fastapi.responses import JSONResponse

# 认证模块自身的公开接口
AUTH_PUBLIC_PATHS = {
    "/login": {"POST"},
    "/get-key": {"GET"},
    "/is-login": {"GET"},
    "/signout": {"POST", "GET"},
    "/authentication/get-list": {"GET"},
    "/authentication/get/by/type": {"GET"},
    "/ldap/login": {"POST"},
    # 登录页初始加载时获取平台组织参数（无需登录）
    "/setting/get/platform/param": {"GET"},
    "/api/user/menu": {"POST"},
    "/health": {"GET", "HEAD"},
    # FastAPI 内置 API 文档
    "/docs": {"GET"},
    "/docs/oauth2-redirect": {"GET"},
    "/redoc": {"GET"},
    "/openapi.json": {"GET"},
    # 前端应用启动时获取默认语言（无需登录）
    "/user/local/config/default-locale": {"GET"},
}

# 前端资源/WebSocket 路径不鉴权
# 注：精简控制台（/static/*）已删除，前端统一由 /ms/ 前缀的 TestPilot 工程承载；
#     /assets/、/images/ 为其静态资源，无需登录即可访问。
#     WebSocket 在握手阶段难以携带自定义 Header，故暂放行；
#     具体业务 WebSocket 可自行校验 query/cookie 中的 token。
STATIC_PREFIXES = [
    "/assets/",
    "/images/",
    "/ms/",
    "/front/",
    "/ws/",
    "/favicon.ico",
    # 平台展示资源（Logo/图标等），无需登录即可访问
    "/base-display/",
]

# 分享页面（/share/ 免登录白名单）所需的公开 API 路径前缀。
# 这些路径允许持有分享链接的用户无登录访问被分享的资源：
#   - 测试计划报告分享（shareReportTestPlan 页面）
#   - 接口文档分享 / API 定义分享（shareDefinitionApi 页面）
#   - 场景/用例报告分享（shareReportScenario / shareReportCase 页面）
# 创建分享（如 /test-plan/report/share/gen）仍需登录，不在此白名单内。
SHARE_PUBLIC_PREFIXES = [
    # ── 测试计划报告分享（查看分享报告详情/分页/布局）──
    "/test-plan/report/share/get",
    "/test-plan/report/share/detail",
    "/test-plan/report/share/get-layout",
    "/test-plan/report/share/get-share-time",
    # ── 接口文档分享（查看分享详情/校验密码/模块树/模块数）──
    "/api/doc/share/detail",
    "/api/doc/share/get-detail",
    "/api/doc/share/check",
    "/api/doc/share/module/tree",
    "/api/doc/share/module/count",
    "/api/doc/share/export",
    "/api/doc/share/download/file",
    "/api/doc/share/plugin/script",
]

# 邀请注册页（/invite 免登录）所需公开 API 前缀。
# /#/invite 供【尚未注册的新用户】打开邮件邀请链接后完成注册，
# 因此 check-invite（校验邀请有效性）与 register-by-invite（注册）
# 必须在未登录状态下可访问，否则邀请注册流程 401 直接断裂。
INVITE_PUBLIC_PREFIXES = [
    "/system/user/check-invite",
    "/system/user/register-by-invite",
]

def _is_invite_public(path: str) -> bool:
    """判断路径是否为邀请注册页免登录公开 API。"""
    return any(path.startswith(p) or path == p.rstrip("/") for p in INVITE_PUBLIC_PREFIXES)


def _is_share_public(path: str) -> bool:
    """判断路径是否为分享页面免登录公开 API。"""
    return any(path.startswith(p) or path == p.rstrip("/") for p in SHARE_PUBLIC_PREFIXES)


# 精简控制台（根路径 / 的 static/js/app.js）已删除；TestPilot 前端（/ms/）
# 通过 /front/ 前缀经部署层重写调用 /api/*。以下对 /api/ 前缀【只读】请求
# （GET/HEAD/OPTIONS）放行，仍为 TestPilot 兼容层所需。
#
# ⚠️ 安全加固：虽然 GET 通常是只读，但系统为兼容 TestPilot 前端保留了大量
# 「以 GET 实现写操作」的路由（删除/恢复/执行/停止等，见 *_compat.py 中的 GET兼容）。
# 若对 /api/ 下所有 GET 一律放行，将导致【未登录即可删除/执行数据】的越权与 CSRF 风险。
# 因此这里对 /api/ 下这些「写语义 GET 路由」强制要求鉴权，仅对真正的只读 GET 放行。
API_READ_METHODS = {"GET", "HEAD", "OPTIONS"}

# /api/ 下以 GET 实现的「写操作」路由前缀（TestPilot 兼容层）。
# 命中这些路径的 GET 请求仍需登录，不再走只读放行。
_WRITE_GET_PREFIXES = [
    "/api/case/api-change/clear",
    "/api/case/delete", "/api/case/delete-to-gc", "/api/case/recover", "/api/case/run",
    "/api/casedelete", "/api/caserecover",
    "/api/debug/delete", "/api/debug/module/delete",
    "/api/definition/delete", "/api/definition/delete-to-gc",
    "/api/definition/module/delete", "/api/definition/schedule/delete",
    "/api/definition/schedule/switch", "/api/definition/stop",
    "/api/doc/share/delete", "/api/doc/share/stop",
    "/api/report/case/delete", "/api/report/scenario/delete",
    "/api/scenario/delete", "/api/scenario/delete-to-gc",
    "/api/scenario/module/delete", "/api/scenario/recover",
    "/api/scenario/schedule-config-delete", "/api/scenario/stop",
    "/api/stop",
    "/api/case/follow", "/api/case/unfollow",
    "/api/casefollow", "/api/caseunfollow",
    "/api/case/update-priority", "/api/case/update-status",
    "/api/definition/follow", "/api/definition/mock/enable",
    "/api/scenario/update-priority", "/api/scenario/update-status",
    "/api/scenariofollow",
]
# 预编译写路径匹配正则：前缀 + 可选的 /{id} 路径片段
_WRITE_GET_RE = re.compile(
    "^(?:" + "|".join(re.escape(p) for p in sorted(_WRITE_GET_PREFIXES, key=len, reverse=True))
    + r")(?:/.*)?$"
)


def _is_write_get(path: str) -> bool:
    """判断 /api/ 下的某个路径是否是「写语义 GET」路由（命中则需鉴权）。"""
    return bool(_WRITE_GET_RE.match(path))


class AuthMiddleware:
    """全局认证中间件（纯 ASGI 实现）。

    所有业务路由需携带有效会话令牌，仅放行白名单路径（登录、公钥获取等）。

    性能说明：相比 BaseHTTPMiddleware，纯 ASGI 中间件直接透传 scope/receive/send，
    不经过 Starlette 的流式双缓冲与任务编排，单层吞吐可提升约 5~10 倍，
    是高并发下避免事件循环阻塞的关键。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = (scope.get("method") or "GET").upper()

        # 1. 静态资源和前端入口放行
        for prefix in STATIC_PREFIXES:
            if path.startswith(prefix) or path == prefix.rstrip("/"):
                await self.app(scope, receive, send)
                return

        # 2. 认证公开接口放行
        if path in AUTH_PUBLIC_PATHS and method in AUTH_PUBLIC_PATHS[path]:
            await self.app(scope, receive, send)
            return

        # 2.3 分享页面免登录公开 API 放行
        #     分享页 /share/* 中的资源通过分享链接直接访问，无需登录。
        if _is_share_public(path):
            await self.app(scope, receive, send)
            return

        # 2.4 邀请注册页（/invite）公开 API 放行
        #     新用户打开邀请链接后无需登录即可校验邀请并注册。
        if _is_invite_public(path):
            await self.app(scope, receive, send)
            return

        # 2.5 legacy 控制台 /api/ 只读请求放行（GET/HEAD/OPTIONS）
        #     但【写语义 GET 路由】除外，须强制鉴权。
        if path.startswith("/api/") and method in API_READ_METHODS:
            if not _is_write_get(path):
                await self.app(scope, receive, send)
                return

        # 3. 检查会话令牌
        token = self._extract_token(scope)
        if not token:
            response = self._unauthorized()
            await response(scope, receive, send)
            return

        from app.auth.store import auth_store
        user = auth_store.get_session_user(token)
        if not user:
            response = self._unauthorized()
            await response(scope, receive, send)
            return

        # 3.5 CSRF 校验：仅针对「可能改变状态」的请求
        #     - 非安全方法（POST/PUT/PATCH/DELETE）一律校验；
        #     - /api/ 下以 GET 实现的「写语义」兼容路由也校验
        #       （未携带 CSRF 头会破坏一次点击即可删除的 CSRF 攻击面）。
        #     只读 GET/HEAD/OPTIONS 无需 CSRF（无副作用）。
        #     白名单路径已在步骤 2 提前放行，不进入此处。
        is_mutating = method not in API_READ_METHODS or (
            path.startswith("/api/") and _is_write_get(path)
        )
        if is_mutating:
            expected_csrf = user.get("_csrf_token", "")
            actual_csrf = self._extract_csrf(scope)
            if not expected_csrf or not actual_csrf or not self._safe_equal(expected_csrf, actual_csrf):
                response = self._csrf_forbidden()
                await response(scope, receive, send)
                return

        # 将用户信息注入 scope.state，供各路由经 request.state 读取
        state = scope.setdefault("state", {})
        state["user"] = user
        await self.app(scope, receive, send)

    @staticmethod
    def _headers_map(scope) -> dict:
        """将 scope 中的原始 HTTP 头解析为 {小写名: 值} 字典。"""
        return {k.decode("latin-1").lower(): v.decode("latin-1")
                for k, v in scope.get("headers", [])}

    @staticmethod
    def _cookies_map(scope) -> dict:
        """将 scope 中的 Cookie 头解析为 cookie 字典。"""
        headers = AuthMiddleware._headers_map(scope)
        cookie = headers.get("cookie", "")
        return {k.strip(): v.strip()
                for k, v in (kv.split("=", 1) for kv in cookie.split(";") if "=" in kv)}

    @staticmethod
    def _extract_token(scope) -> str:
        """从请求头或 Cookie 中提取会话令牌。"""
        headers = AuthMiddleware._headers_map(scope)
        token = headers.get("x-auth-token", "") or ""
        if not token:
            cookie = headers.get("cookie", "")
            m = re.search(r"(?:^|;)\s*sessionId=([^;]+)", cookie)
            if m:
                token = m.group(1).strip()
        return token

    @staticmethod
    def _extract_csrf(scope) -> str:
        """从请求头或 Cookie 中提取 CSRF Token。"""
        headers = AuthMiddleware._headers_map(scope)
        return (
            headers.get("csrf-token", "")
            or headers.get("x-csrf-token", "")
            or AuthMiddleware._cookies_map(scope).get("csrfToken", "")
        )

    @staticmethod
    def _safe_equal(a: str, b: str) -> bool:
        """常量时间比较，避免时序侧信道。"""
        return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))

    @staticmethod
    def _csrf_forbidden() -> JSONResponse:
        return JSONResponse(
            {"code": 403, "message": "CSRF 校验失败或请求缺少 CSRF Token", "data": None},
            status_code=403,
        )

    @staticmethod
    def _unauthorized() -> JSONResponse:
        return JSONResponse(
            {"code": 401, "message": "未登录或会话已过期", "data": None},
            status_code=401,
        )


__all__ = ["AuthMiddleware"]
