"""
TestPilot 前端产物服务回归测试（tests/test_ms_frontend_serving.py）
====================================================================
这个文件的存在理由只有一个：**防止 /ms/ 前端入口再次被别的路由抢走**。

背景（真实踩过的坑）：
    `app/routers/system.py` 里曾注册了占位的 `GET /ms` 和 `GET /ms/{full_path:path}`，
    而 system_router 在 `app/main.py` 的业务路由阶段就已 include —— 于是
    system.py 的 catch-all 先于 main.py 末尾的 SPA 回退路由命中，
    所有 /ms/xxx 请求都返回：

        Content-Type: application/json
        {"code":200,"message":"success","data":{"code":200,...,"data":null}}

    浏览器把 JSON 当 HTML 渲染 → **整个 TestPilot 前端打不开**。
    更隐蔽的是：它返回 200，所以任何只看状态码的测试都会「通过」。

本文件的断言因此不看状态码，而是看**返回体是不是真的 index.html**。

产物缺失时的行为：
    `frontend/dist/` 是构建产物（已被 .gitignore 忽略），CI 里可能不存在。
    此时全部用例 skip —— 因为要验证的是「有产物时能不能正确提供」，
    而不是「没有产物时是否报错」。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest
from fastapi.testclient import TestClient

from app.main import MS_FRONTEND_DIST, app

DIST_EXISTS = os.path.isdir(MS_FRONTEND_DIST)
needs_dist = pytest.mark.skipif(
    not DIST_EXISTS,
    reason="frontend/dist 未构建（构建产物，已 gitignore），跳过前端产物服务校验",
)

# 前端 hash 路由真实存在的页面路径（与 frontend/src/router 对应）
SPA_PATHS = [
    "/ms",
    "/ms/",
    "/ms/login",
    "/ms/workbench",
    "/ms/workbench/homePage",
    "/ms/case-management/case",
    "/ms/case-management/caseReview",
    "/ms/api-test/api",
    "/ms/api-test/apiCase",
    "/ms/api-test/scenario",
    "/ms/bug-management/bug",
    "/ms/test-plan/testPlan",
    "/ms/project-management/project",
    "/ms/project-management/environment",
    "/ms/setting/system",
    "/ms/setting/organization",
    "/ms/ai-case-gen",
]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@needs_dist
class TestMsSpaServing:
    """/ms/ 下所有前端路由都必须回退到 index.html。"""

    @pytest.mark.parametrize("path", SPA_PATHS)
    def test_spa_route_returns_html(self, client, path):
        """核心断言：状态码是 200，且 Content-Type 是 html。

        只看状态码会漏掉「占位 JSON 路由抢先命中」这个历史 Bug ——
        那种情况同样返回 200，所以必须连 content-type 和内容一起验。
        """
        r = client.get(path)
        assert r.status_code == 200, f"{path} 返回 {r.status_code}: {r.text[:120]}"
        ctype = r.headers.get("content-type", "")
        assert "html" in ctype, (
            f"{path} 返回了非 HTML（content-type={ctype}），说明 /ms/ 被其它路由抢先命中。"
            f"响应体前 120 字符：{r.text[:120]}"
        )
        assert "<!DOCTYPE html>" in r.text or "<html" in r.text.lower()
        assert '<div id="app">' in r.text, "回退到的不是前端 index.html 骨架"

    def test_no_ph_json_on_spa_paths(self, client):
        """任何 SPA 路径都不能再返回占位透传 JSON。"""
        for path in ("/ms", "/ms/workbench", "/ms/api-test/api"):
            body = client.get(path).text.strip()
            assert not body.startswith("{"), (
                f"{path} 返回了 JSON 而非 HTML —— /ms/ 被占位路由劫持，前端会白屏。"
                f"响应：{body[:120]}"
            )

    def test_html_asset_paths_rewritten(self, client):
        """index.html 里的 /assets/ 引用要被重写成 /ms/assets/。

        前端产物默认按站点根部署，走 /ms/ 前缀时必须改写，
        否则 JS/CSS 全部 404，页面只有光秃秃的骨架。
        """
        html = client.get("/ms/workbench").text
        assert "/ms/assets/" in html, "index.html 的 assets 引用未被重写为 /ms/assets/"
        assert 'src="/assets/' not in html, "仍存在未重写的绝对路径 /assets/ 引用"


@needs_dist
class TestMsStaticAssets:
    """/ms/ 前缀下的静态资源必须能真正取到文件。"""

    def _first_asset(self, ext):
        assets_dir = os.path.join(MS_FRONTEND_DIST, "assets")
        names = sorted(
            n for n in os.listdir(assets_dir)
            if n.endswith(ext) and "legacy" not in n
        )
        return names[0] if names else None

    def test_js_asset_served(self, client):
        """JS chunk 必须返回 javascript，而不是被 SPA 回退成 HTML。"""
        name = self._first_asset(".js")
        if not name:
            pytest.skip("dist/assets 下没有 js 产物")
        r = client.get(f"/ms/assets/{name}")
        assert r.status_code == 200
        assert "javascript" in r.headers.get("content-type", ""), (
            f"/ms/assets/{name} 未返回 js（content-type={r.headers.get('content-type')}），"
            "说明该路径被 SPA catch-all 吞掉了"
        )

    def test_css_asset_served(self, client):
        """CSS chunk 必须返回 text/css。"""
        name = self._first_asset(".css")
        if not name:
            pytest.skip("dist/assets 下没有 css 产物")
        r = client.get(f"/ms/assets/{name}")
        assert r.status_code == 200
        assert "css" in r.headers.get("content-type", ""), (
            f"/ms/assets/{name} 未返回 css"
        )

    def test_images_served(self, client):
        """登录页 banner/avatar 等图片属于前端资源，必须可取。"""
        images_dir = os.path.join(MS_FRONTEND_DIST, "images")
        if not os.path.isdir(images_dir):
            pytest.skip("dist/images 不存在")
        files = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
        if not files:
            pytest.skip("dist/images 为空")
        r = client.get(f"/ms/images/{files[0]}")
        assert r.status_code == 200, f"/ms/images/{files[0]} 返回 {r.status_code}"

    def test_favicon_not_html(self, client):
        """favicon 不能返回 HTML（浏览器会把 HTML 当图标解析，控制台报错）。"""
        r = client.get("/ms/favicon.ico")
        assert r.status_code in (200, 204), f"/ms/favicon.ico 返回 {r.status_code}"
        if r.status_code == 200:
            assert "html" not in r.headers.get("content-type", ""), (
                "favicon 被 SPA 回退成了 HTML，浏览器图标解析会失败"
            )


class TestMsRouteConflictGuard:
    """路由层的防回潮检查，不依赖 dist 是否构建。"""

    def test_no_duplicate_ms_catchall_registration(self):
        """/ms 的 catch-all 在全项目只能注册一处。

        两处注册 = 先注册的那个静默生效 = 前端白屏。
        """
        import re
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        pattern = re.compile(
            r"@\w+\.get\s*\(\s*[\"']/ms(?:/\{[^'\"]+\})?[\"']"
        )
        hits = []
        for py in sorted((root / "app").rglob("*.py")):
            if py.name == "__init__.py":
                continue
            found = pattern.findall(py.read_text(encoding="utf-8", errors="ignore"))
            if found:
                hits.append((str(py.relative_to(root)), found))
        assert len(hits) == 1, (
            f"GET /ms 的路由应在 app/main.py 中唯一注册，实际命中 {len(hits)} 处：{hits}。"
            "多处注册会导致先注册者劫持 SPA 回退，前端打不开。"
        )
        assert hits[0][0] == "app/main.py"

    def test_ms_spa_route_registered_last(self):
        """SPA 回退必须是 /ms 前缀下的最后一个路由。

        它在 main.py 末尾注册，因此应晚于所有业务路由；
        若有人把它挪到业务路由之前，前端资源会被业务路由抢走。
        """
        flat = []

        def collect(routes):
            for r in routes:
                path = getattr(r, "path", None)
                if path is None:
                    inner = getattr(r, "original_router", None)
                    if inner is not None:
                        collect(inner.routes)
                    continue
                flat.append((path, getattr(r, "name", None), getattr(r, "endpoint", None)))

        collect(app.routes)

        spa_idx = None
        for i, (path, _name, _ep) in enumerate(flat):
            if path == "/ms/{full_path:path}":
                spa_idx = i
                break
        assert spa_idx is not None, "未找到 /ms/{full_path:path} SPA 回退路由"

        # 之后只允许剩下的 /ms SPA 家族路由（/ms 本身），
        # 不允许任何业务路由 —— 业务路由若排在后面，也说明有人把 SPA 提前了。
        later = [
            (p, n) for (p, n, _e) in flat[spa_idx + 1:]
            if p and not p.startswith(("/openapi", "/docs", "/redoc", "/ms"))
        ]
        assert not later, (
            f"SPA 回退路由之后不应再注册任何业务路由，实际还有：{later[:10]}"
        )

    def test_endpoint_is_ms_frontend(self):
        """/ms 的 catch-all 处理函数必须是 main.py 的 ms_frontend。"""
        target = None

        def collect(routes):
            nonlocal target
            for r in routes:
                path = getattr(r, "path", None)
                if path is None:
                    inner = getattr(r, "original_router", None)
                    if inner is not None:
                        collect(inner.routes)
                    continue
                if path == "/ms/{full_path:path}":
                    target = getattr(r, "endpoint", None)

        collect(app.routes)
        assert target is not None
        assert target.__name__ == "ms_frontend", (
            f"/ms catch-all 的处理函数是 {target.__name__}，应为 app.main.ms_frontend"
        )
        assert target.__module__ == "app.main"
