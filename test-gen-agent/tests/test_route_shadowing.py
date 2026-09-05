"""
路由遮蔽回归测试（tests/test_route_shadowing.py）
================================================
支路 E「路由装配硬化」的回归护栏。

背景
----
`extra_router.py` 注册了 `POST /project/application/{suffix}`、
`POST /project/application/update/{project_id}` 等**泛化参数路由**，
而 project_compat_application 等模块则注册了 `/project/application/update/workstation`
等**具体字面路由**。Starlette 按 include 先后线性匹配、先注册先生效 ——
若泛化 router（extra_router）被提前 include，`{suffix}` / `{project_id}`
就会抢先命中本应走字面路由的请求，字面路由永远不可达（历史多次出现）。

main.py 已改用集中式路由注册表（app/routers/registry.py）装配，把
extra_router 固定放入 `catchall` 分组并置于最后；装配后由遮蔽检测器
`detect_shadow_conflicts` 把关。本文件将「`{suffix}` 不遮蔽字面路由」
固化为回归测试。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routers.registry import can_shadow


class TestCanShadow:
    """`{param}` 泛化路由能否遮蔽同前缀字面路由 —— 算法判定。"""

    def test_suffix_can_shadow_literal(self):
        # /project/application/{suffix} 能吸收任意单段字面值
        assert can_shadow("/project/application/{suffix}", "/project/application/api") is True
        assert can_shadow("/project/application/{suffix}", "/project/application/update") is True

    def test_deeper_param_can_shadow_literal(self):
        # /project/application/update/{project_id} 遮蔽 /project/application/update/workstation
        assert can_shadow(
            "/project/application/update/{project_id}",
            "/project/application/update/workstation",
        ) is True

    def test_different_segment_count_no_shadow(self):
        # 段数不同不会遮蔽
        assert can_shadow(
            "/project/application/{suffix}",
            "/project/application/bug/platform",
        ) is False

    def test_different_literal_segment_no_shadow(self):
        # 字面段不一致不会遮蔽
        assert can_shadow(
            "/api/environments/{env_id}/launch",
            "/api/environments/trash/{x}",
        ) is False

    def test_same_segments_identical_no_shadow(self):
        # 全参数段之间不构成「参数遮蔽字面」
        assert can_shadow("/a/{x}", "/a/{y}") is False

    def test_param_not_absorb_param_literal(self):
        # 段形状不一致不构成遮蔽
        assert can_shadow("/a/foo/{x}", "/a/{y}/bar") is False


# ── 装配守卫（依赖完整 app，仅在可导入 app 的环境运行）────────────
try:
    from app.main import app
    from app.routers.registry import collect_flat_routes
    _APP = app
except Exception:  # pragma: no cover - 依赖缺失时跳过
    _APP = None


if _APP is not None:

    class TestExtraRouterDoesNotShadowLiteral:
        """extra_router 的 {suffix}/{project_id} 不得遮蔽任何业务字面路由。

        main.py 的装配期遮蔽检测把 extra_router 归入 catchall 分组放在最后；
        本测试从 `app.state.route_shadow_conflicts` 与真实注册顺序两方面兜底。
        """

        def test_no_extra_router_shadow_conflict(self):
            conflicts = getattr(_APP.state, "route_shadow_conflicts", [])
            extra_shadowing = [
                c for c in conflicts
                if "extra_router" in c["param_source"]
            ]
            assert extra_shadowing == [], (
                "extra_router 的泛化路由遮蔽了业务字面路由，装配顺序错误：\n"
                + "\n".join(
                    f"[{c['method']}] {c['param_path']} 遮蔽 {c['literal_path']}"
                    for c in extra_shadowing
                )
            )

        def test_project_application_literal_registered_before_param(self):
            """project_compat 的 project/application 字面路由须先于 extra_router 参数路由。"""
            flat = collect_flat_routes(_APP)
            indexed = []
            for i, fr in enumerate(flat):
                for m in fr["methods"]:
                    if m == "HEAD":
                        continue
                    indexed.append({**fr, "index": i, "method": m})

            def idx(method, path):
                for f in indexed:
                    if f["method"] == method and f["path"] == path:
                        return f["index"]
                return None

            # project_compat 字面路由
            literal_keys = [
                ("POST", "/project/application/update/workstation"),
                ("POST", "/project/application/update/bug"),
            ]
            # extra_router 泛化路由（必须晚于上面字面路由注册）
            param_keys = [
                ("POST", "/project/application/update/{project_id}"),
                ("POST", "/project/application/{suffix}"),
            ]
            for (lm, lp) in literal_keys:
                lit_idx = idx(lm, lp)
                assert lit_idx is not None, f"未找到字面路由 {lm} {lp}"
                for (pm, pp) in param_keys:
                    par_idx = idx(pm, pp)
                    if par_idx is None or not can_shadow(pp, lp):
                        continue
                    assert lit_idx < par_idx, (
                        f"字面路由 {lm} {lp} (idx {lit_idx}) 晚于泛化路由 "
                        f"{pm} {pp} (idx {par_idx}) 注册，会被遮蔽！"
                    )

        def test_detector_reports_known_historical_conflicts(self):
            """遮蔽检测器应能发现仓库既有的历史遮蔽（作为有效性自检）。"""
            conflicts = getattr(_APP.state, "route_shadow_conflicts", [])
            assert conflicts, (
                "遮蔽检测器未报告任何冲突；若仓库已清理历史遮蔽可移除本断言。"
            )
