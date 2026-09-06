"""
路由注册表与装配硬化（Phase 5 支路 E）
=======================================
背景
----
`app/main.py` 历史上有几十个手写 `app.include_router(...)`，其相对顺序并非
可随意调整：含 `{suffix}` / `{project_id}` 等泛化参数路由的 router（如
`extra_router`）必须排在**所有具体业务 router 之后** —— 否则其参数段会
抢先命中 project_compat 等模块里的字面路由，使后者永远不可达。Starlette
按注册顺序线性匹配，先注册先生效，这类 Bug 曾多次出现且只靠注释提醒。

本模块提供两样东西替代脆弱的「include 顺序依赖」：

1. 数据驱动的**路由注册表** `RouterRegistry`：把待装配的 router 按
   `core -> business -> catchall` 三个分组声明，由 `install()` 依据
   `priority` 自动排序 include，装配顺序不再依赖代码书写位置。
2. **遮蔽检测器** `detect_shadow_conflicts()`：装配完成后扫描应用全部
   路由，验证不存在「参数化路由遮蔽同前缀字面路由」的注册顺序问题。

用法（在 main.py 内）：:

    from app.routers.registry import RouterRegistry, \
        GROUP_CORE, GROUP_BUSINESS, GROUP_CATCHALL, \
        PRIORITY_CORE, PRIORITY_BUSINESS, PRIORITY_CATCHALL

    reg = RouterRegistry()
    reg.add_group(GROUP_CORE, [("auth", auth_router), ...], priority=PRIORITY_CORE)
    reg.add_group(GROUP_BUSINESS, [("project_compat", project_compat_router), ...],
                  priority=PRIORITY_BUSINESS)
    reg.add_group(GROUP_CATCHALL, [("extra_router", _extra_router)],
                  priority=PRIORITY_CATCHALL,
                  note="含 {suffix} 参数路由，必须最后 include")
    conflicts = reg.install(app)
    if conflicts:
        raise RuntimeError("发现路由遮蔽冲突: %r" % conflicts)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

# ────────────────────────────────────────────────────────────
# 装配分组优先级：数值越大越先 include
#   core(认证/基础模块) → business(业务域) → catchall(兜底泛化路由)
# ────────────────────────────────────────────────────────────
PRIORITY_CORE = 100
PRIORITY_BUSINESS = 50
PRIORITY_CATCHALL = 10

GROUP_CORE = "core"
GROUP_BUSINESS = "business"
GROUP_CATCHALL = "catchall"


@dataclass
class RouteGroup:
    """一个路由装配分组。

    priority 越大越先 include；组内按 ``routers`` 列表顺序 include。
    """

    name: str
    priority: int
    routers: List[Tuple[str, Any]] = field(default_factory=list)
    note: str = ""


# ────────────────────────────────────────────────────────────
# 遮蔽检测（纯工具，不依赖 FastAPI）
# ────────────────────────────────────────────────────────────

def _segment(path: str) -> List[Tuple[bool, str]]:
    """把路径拆为有序段序列，每段标记是否为路径参数。"""
    segs = []
    for s in path.strip("/").split("/"):
        if not s:
            continue
        if s.startswith("{"):
            inner = s[1:-1]
            # {path:path} 这类转换器同样按参数段处理
            if ":" in inner:
                inner = inner.split(":", 1)[0]
            segs.append((True, inner))
        else:
            segs.append((False, s))
    return segs


def has_path_param(path: str) -> bool:
    return "{" in path


def can_shadow(param_path: str, literal_path: str) -> bool:
    """判定参数化路径 param_path 能否遮蔽字面路径 literal_path。

    条件：段数相同，param_path 的所有字面段与 literal_path 完全一致，
    且至少存在一个位置 param 是参数段而 literal 是对应字面值。
    """
    p1 = _segment(param_path)
    p2 = _segment(literal_path)
    if len(p1) != len(p2):
        return False
    matched = False
    for (is_p, pv), (is_l, lv) in zip(p1, p2, strict=True):
        if is_p != is_l:
            # 参数段可吸收任意字面值
            if is_p:  # param=参数, literal=字面
                matched = True
                continue
            # param=字面, literal=参数：param 不能吸收参数段
            return False
        # 同为字面或同为参数段：内容必须一致
        if pv != lv:
            return False
    return matched


def collect_flat_routes(app) -> List[Dict[str, Any]]:
    """展开 FastAPI 应用全部路由，返回按注册先后排序的路由摘要。"""
    flat: List[Dict[str, Any]] = []

    def walk(routes: Any) -> None:
        for r in routes:
            inner = getattr(r, "original_router", None)
            if inner is not None:
                walk(inner.routes)
                continue
            path = getattr(r, "path", None)
            if path is None:
                continue
            methods = getattr(r, "methods", None) or set()
            endpoint = getattr(r, "endpoint", None)
            flat.append({
                "path": path,
                "methods": set(methods),
                "source": getattr(endpoint, "__module__", ""),
                "name": getattr(endpoint, "__name__", ""),
            })

    walk(app.routes)
    return flat


def detect_shadow_conflicts(app) -> List[Dict[str, Any]]:
    """扫描应用全部路由，找出「参数化路由遮蔽同前缀字面路由」的冲突。

    遮蔽成立的条件（同时满足）：
      1. 存在一条带路径参数的路由（如 ``{suffix}``）与一条同 method、
         同段数的纯字面路由，参数段能吸收对应字面值（can_shadow 为真）；
      2. 参数化路由注册在字面路由**之前**（index 更小）—— Starlette 先注册
         先生效，此时字面路由永远不可达。

    正常装配（catch-all 兜底 router 放在最后）下返回空列表；任何打乱
    顺序的改动都会在这里被捕获，从而在 CI 中直接暴露。
    """
    flat = collect_flat_routes(app)
    indexed: List[Dict[str, Any]] = []
    for i, fr in enumerate(flat):
        for m in fr["methods"]:
            if m == "HEAD":
                continue
            indexed.append({**fr, "index": i, "method": m})

    params = [f for f in indexed if has_path_param(f["path"])]
    literals = [f for f in indexed if not has_path_param(f["path"])]

    conflicts: List[Dict[str, Any]] = []
    for pr in params:
        for lr in literals:
            if pr["method"] != lr["method"]:
                continue
            if not can_shadow(pr["path"], lr["path"]):
                continue
            if pr["index"] < lr["index"]:
                conflicts.append({
                    "method": pr["method"],
                    "param_path": pr["path"],
                    "literal_path": lr["path"],
                    "param_source": pr["source"],
                    "literal_source": lr["source"],
                })
                break  # 一个 param 路由只需提示一次

    conflicts.sort(key=lambda c: (c["method"], c["param_path"], c["literal_path"]))
    return conflicts


# ────────────────────────────────────────────────────────────
# 路由注册表
# ────────────────────────────────────────────────────────────

class RouterRegistry:
    """集中式路由注册表。

    router 引用由调用方（main.py）在模块 import 后传入，避免本模块直接
    import 各 router 造成循环依赖；分组 + priority 取代物理 include 顺序。
    """

    def __init__(self) -> None:
        self._groups: Dict[str, RouteGroup] = {}
        self._order: List[str] = []

    def add_group(self, name: str, routers: List[Tuple[str, Any]],
                  priority: int, note: str = "") -> "RouterRegistry":
        """登记或追加一个分组。同 name 已存在时追加 routers。"""
        if name in self._groups:
            self._groups[name].routers.extend(routers)
            self._groups[name].priority = priority
            if note:
                self._groups[name].note = note
        else:
            self._groups[name] = RouteGroup(
                name=name, priority=priority,
                routers=list(routers), note=note,
            )
        if name not in self._order:
            self._order.append(name)
        return self

    def install(self, app, detect_shadow: bool = True) -> List[Dict[str, Any]]:
        """按 priority 降序批量 include 全部分组路由。

        完成后若 ``detect_shadow`` 开启，返回遮蔽冲突列表（正常应为空）。
        """
        ordered = sorted(
            self._order,
            key=lambda n: self._groups[n].priority,
            reverse=True,
        )
        for name in ordered:
            for _label, router in self._groups[name].routers:
                app.include_router(router)

        if not detect_shadow:
            return []
        return detect_shadow_conflicts(app)


__all__ = [
    "PRIORITY_CORE",
    "PRIORITY_BUSINESS",
    "PRIORITY_CATCHALL",
    "GROUP_CORE",
    "GROUP_BUSINESS",
    "GROUP_CATCHALL",
    "RouterRegistry",
    "detect_shadow_conflicts",
    "collect_flat_routes",
    "can_shadow",
    "has_path_param",
]
