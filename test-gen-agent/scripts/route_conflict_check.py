#!/usr/bin/env python3
"""
路由冲突检测脚本
=================
Phase 0 目标：建立路由冲突检测机制，防止重复路径注册。

FastAPI 中，不同 APIRouter 之间允许注册相同 path+method（按注册顺序匹配），
但**同一个路由文件/同一个 APIRouter 内**对相同 path+method 重复注册才是真正的冲突，
会导致前一个处理函数被静默覆盖，属于 bug。

本脚本因此只检测「同一文件内」的重复路由注册，避免把跨文件（跨 Router）的
合法重叠误报为冲突。

此外还检测一类更隐蔽的冲突：**同形不同名的路径参数**。
FastAPI 按「路径骨架」匹配路由，两条骨架相同但参数名不同的路由
（如 `/notification/read/{item_id}` 与 `/notification/read/{notification_id}`）
会互相抢占 —— 谁先注册谁生效，后者永远命中不了。这类问题完全依赖
include 顺序，一旦有人调整 `app/routers/__init__.py` 的导入顺序，线上
就会静默错乱且不报错。因此纳入门禁，新增即阻塞。

用法：
    python3 scripts/route_conflict_check.py --check    # 检查当前路由冲突
    python3 scripts/route_conflict_check.py --generate # 生成 API 映射表
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# 匹配任意变量名的路由装饰器，如 @router.get、@dashboard_router.post、@_extra_router.get 等
ROUTE_DECORATOR_PATTERN = re.compile(
    r"@(\w+)\.(get|post|put|delete|patch)\s*\(\s*[\"']([^\"']+)[\"']"
)

# 不参与冲突检测的文件（已废弃 / 不挂载 / 兼容层）
# 这些文件中的路由由 domains 下对应模块或 main.py 已替代
SKIP_FILES = {
    # 已随 domains 收敛迁移至 routers 层的适配文件（路由正常参与检测，无需跳过）
}

# 已知存在的「同形不同名」路径参数冲突（method, 参数名组合A, 参数名组合B, frozenset(来源)）
# 历史遗留，已列入白名单不阻塞 CI；新增的组合必须修复。
# 2026-09 Phase D 影子路由清理后全部消除（共 11 组），白名单置空：
#   曾含 notifications/read item_id vs notification_id、
#   project_compat 的 {suffix} vs {project_id} 资源池/用户、
#   system_compat 的 user-view role_id vs view_type、user/role/project/delete group_id vs role_id、
#   gap_fixes/debug_compat 的 projectId vs project_id、test_resources/router 的 report_id vs share_id。
KNOWN_PARAM_CONFLICTS = {
}


def scan_routes() -> list:
    """扫描项目中的所有路由定义。"""
    routes = []
    base_dir = Path(__file__).parent.parent
    app_dir = base_dir / "app"

    # 遍历 app 目录下所有 .py 文件
    for py_file in sorted(app_dir.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        rel = py_file.relative_to(base_dir)
        rel_str = str(rel)
        if rel_str in SKIP_FILES:
            continue
        content = py_file.read_text()
        for _decorator_var, method, path in ROUTE_DECORATOR_PATTERN.findall(content):
            routes.append({
                "path": path,
                "method": method.upper(),
                "source": rel_str,
            })

    return routes


def path_shape(path: str) -> tuple:
    """把路径归一化为「骨架 + 参数名」二元组，用于识别同形不同名冲突。

    /notification/read/{item_id}  → (('notification', None), ('read', None), ('{}', 'item_id'))
    /notification/read/{n_id}     → (('notification', None), ('read', None), ('{}', 'n_id'))
    两者骨架相同、参数名不同，即为冲突。
    """
    segments = []
    for seg in path.strip("/").split("/"):
        if seg.startswith("{") and seg.endswith("}"):
            segments.append(("{}", seg[1:-1]))
        else:
            segments.append((seg, None))
    return tuple(segments)


def shape_key(path: str) -> tuple:
    """路径骨架键：段数 + 各段字面量/占位符，忽略参数名。"""
    shape = path_shape(path)
    return (len(shape), tuple(seg for seg, _ in shape))


def check_param_name_conflicts(routes: list) -> list:
    """检测「骨架相同但路径参数名不同」的路由。

    这类路由在 FastAPI 中先注册者生效，后注册者永远不可达，
    且行为随 include 顺序变化，属高危隐患。
    """
    grouped = defaultdict(list)
    for r in routes:
        grouped[(r["method"], shape_key(r["path"]))].append(r)

    conflicts = []
    for (_method, _key), items in grouped.items():
        param_sets = {tuple(name for _, name in path_shape(r["path"])) for r in items}
        if len(param_sets) > 1:
            conflicts.append({
                "paths": sorted({r["path"] for r in items}),
                "sources": sorted({r["source"] for r in items}),
                "method": items[0]["method"],
            })
    return sorted(conflicts, key=lambda c: (c["method"], c["paths"]))


def check_conflicts(routes: list) -> list:
    """检查路由冲突。

    仅检测「同一文件（同一 APIRouter）内」对相同 path+method 的重复注册，
    这类冲突会导致前一个处理函数被静默覆盖，属于真实 bug。
    """
    # 以 (source, path, method) 为粒度统计，仅同文件内重复才判定为冲突
    key_map = defaultdict(list)
    conflicts = []

    for r in routes:
        key = (r["source"], r["path"], r["method"])
        key_map[key].append(r)

    for (source, path, method), items in key_map.items():
        if len(items) > 1:
            conflicts.append({
                "path": path,
                "method": method,
                "source": source,
                "count": len(items),
            })

    return conflicts


def generate_mapping(routes: list) -> str:
    """生成 API 映射文档。"""
    lines = ["# API 映射表（自动生成）", ""]
    lines.append(f"共扫描到 **{len(routes)}** 个路由端点。")
    lines.append("")

    # 按路径前缀分组
    grouped = defaultdict(list)
    for r in routes:
        path = r["path"]
        # 提取一级前缀
        parts = path.strip("/").split("/")
        prefix = parts[0] if parts else "(root)"
        grouped[prefix].append(r)

    for prefix in sorted(grouped.keys()):
        items = grouped[prefix]
        lines.append(f"## `/{prefix}` ({len(items)} 个路由)")
        lines.append("")
        lines.append("| Method | Path | Source |")
        lines.append("|--------|------|--------|")
        for r in sorted(items, key=lambda x: (x["method"], x["path"])):
            lines.append(f"| {r['method']} | `{r['path']}` | `{r['source']}` |")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="路由冲突检测工具")
    parser.add_argument("--check", action="store_true", help="检查路由冲突")
    parser.add_argument("--generate", action="store_true", help="生成 API 映射文档")
    args = parser.parse_args()

    routes = scan_routes()

    if args.check:
        conflicts = check_conflicts(routes)
        if conflicts:
            print(f"❌ 发现 {len(conflicts)} 处路由冲突:")
            for c in conflicts:
                print(f"  [{c['method']}] {c['path']}（{c['source']}，定义 {c['count']} 次）")
            sys.exit(1)
        print(f"✅ 未发现同文件重复路由冲突（共 {len(routes)} 个路由）")

        # 门禁 2：骨架相同但路径参数名不同的路由
        param_conflicts = check_param_name_conflicts(routes)
        new_param_conflicts = []
        for c in param_conflicts:
            names = sorted(
                {tuple(n for _, n in path_shape(p) if n is not None) for p in c["paths"]}
            )
            if len(names) != 2:
                new_param_conflicts.append(c)
                continue
            sig = (c["method"], names[0], names[1], frozenset(c["sources"]))
            if sig not in KNOWN_PARAM_CONFLICTS:
                new_param_conflicts.append(c)

        if new_param_conflicts:
            print(f"❌ 发现 {len(new_param_conflicts)} 处路径参数名冲突（骨架相同、参数名不同，"
                  f"后注册者永远不可达）:")
            for c in new_param_conflicts:
                print(f"  [{c['method']}] {' vs '.join(c['paths'])}  ← {', '.join(c['sources'])}")
            print("  修复方式：统一参数名，或把冲突组合加入 KNOWN_PARAM_CONFLICTS 白名单。")
            sys.exit(1)
        print(f"✅ 未发现新增路径参数名冲突（历史遗留 {len(param_conflicts)} 组已在白名单）")
        return

    if args.generate:
        doc = generate_mapping(routes)
        output = Path(__file__).parent.parent / "docs" / "api_mapping_generated.md"
        output.write_text(doc)
        print(f"✅ 已生成 API 映射文档: {output}")
        return

    # 默认输出摘要
    print(f"共发现 {len(routes)} 个路由端点")
    by_source = defaultdict(int)
    for r in routes:
        by_source[r["source"]] += 1
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {source}: {count} 个路由")


if __name__ == "__main__":
    main()
