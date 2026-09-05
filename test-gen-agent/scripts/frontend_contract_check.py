#!/usr/bin/env python3
"""
前端-后端契约校验工具
=====================
核心目的：从源头防止"前端界面看功能有问题"反复出现。

背景：
  本项目前端为原版 TestPilot Vue 前端，后端为 FastAPI 重写实现。
  两者之间存在大量契约差异（URL 路径、HTTP method、入参、返回值结构、
  数据持久化真实性等）。此前依赖逐次"打补丁"修复，导致每次从前端
  访问新功能都会暴露新的契约问题。

本脚本建立"前端 URL → 后端路由"的自动比对机制：
  1. 扫描 frontend/src/api/requrls/ 下全部前端 URL 常量
  2. 扫描后端 app/ 下全部路由定义（path + method）
  3. 校验三类契约：
     a. URL 缺失：前端调用路径后端未注册
     b. 路径参数不兼容：前端模板 `url/{id}` 后端未注册路径参数版本
  4. 输出差距清单，供人工修复或 CI 阻塞

用法：
    python3 scripts/frontend_contract_check.py --check    # 检查并输出差距（缺失即退出码1）
    python3 scripts/frontend_contract_check.py --report   # 生成契约差距报告到 docs/
    python3 scripts/frontend_contract_check.py            # 默认输出摘要
"""
import argparse
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_REQURLS = ROOT / "frontend" / "src" / "api" / "requrls"
BACKEND_DIR = ROOT / "app"

# 前端 URL 常量: export const XxxUrl = '/path';
FRONT_URL_RE = re.compile(r"['\"](\/[^'\"\s]+)['\"]")
# 后端路由装饰器: @router.get("/path") / @xxx.post(...)
BACK_ROUTE_RE = re.compile(
    r"@\w+\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]"
)

# 已知合理的例外（websocket 端点等，后端以 WebSocket 注册，不走 REST 装饰器）
KNOWN_EXCEPTIONS = {
    "/ws/api", "/ws", "/websocket",
}


def normalize(path: str) -> str:
    """将 {id} 路径参数统一为 :param，便于比对。"""
    return re.sub(r"\{[^}]*\}", ":param", path)


def is_path_compatible(front: str, back: str) -> bool:
    """前端路径与后端路径是否兼容（支持路径参数通配）。"""
    fp = normalize(front).split("/")
    bp = normalize(back).split("/")
    if len(fp) != len(bp):
        return False
    for a, b in zip(fp, bp, strict=True):
        if b.startswith(":"):  # 后端路径参数可匹配任意段
            continue
        if a != b:
            return False
    return True


def collect_frontend_urls():
    urls = set()
    for f in FRONTEND_REQURLS.rglob("*.ts"):
        content = f.read_text()
        for m in FRONT_URL_RE.finditer(content):
            p = m.group(1)
            if not p.startswith("/"):
                continue
            if p.startswith("//"):  # 协议相对 URL，跳过
                continue
            urls.add(p)
    return urls


def collect_backend_routes():
    """返回 {path: {method}}，同时区分 REST 路由与 WebSocket 路由。"""
    routes = defaultdict(set)
    ws_paths = set()
    for f in BACKEND_DIR.rglob("*.py"):
        content = f.read_text()
        for m in BACK_ROUTE_RE.finditer(content):
            routes[m.group(2)].add(m.group(1).upper())
        # 收集 WebSocket 端点
        for m in re.finditer(r"@\w+\.websocket\s*\(\s*['\"]([^'\"]+)['\"]", content):
            ws_paths.add(m.group(1))
    return routes, ws_paths


def analyze():
    front_urls = collect_frontend_urls()
    back_routes, ws_paths = collect_backend_routes()

    # 路径参数版本的后端路由（用于判断前端模板 {id} 是否有对应注册）
    all_back_paths = set(back_routes.keys()) | ws_paths

    missing_url = []       # 前端路径后端完全未注册
    for f in sorted(front_urls):
        if f in KNOWN_EXCEPTIONS:
            continue
        matched = [b for b in all_back_paths if is_path_compatible(f, b)]
        if not matched:
            missing_url.append(f)

    return front_urls, back_routes, missing_url


def main():
    parser = argparse.ArgumentParser(description="前端-后端契约校验")
    parser.add_argument("--check", action="store_true", help="检查并输出差距，存在缺失则退出码1")
    parser.add_argument("--report", action="store_true", help="生成契约差距报告到 docs/")
    args = parser.parse_args()

    front_urls, back_routes, missing_url = analyze()

    print(f"前端 URL 数: {len(front_urls)}")
    print(f"后端 REST 路由数: {len(back_routes)}")
    print(f"前端定义但后端未注册的路由: {len(missing_url)}")

    if missing_url:
        print("\n以下前端调用路径后端未注册：")
        for p in missing_url:
            print(f"  ❌ {p}")

    if args.report:
        out = ROOT / "docs" / "contract_gap_report.md"
        lines = ["# 前端-后端契约差距报告（自动生成）", ""]
        lines.append("> 由 `scripts/frontend_contract_check.py --report` 生成，用于追踪前端调用路径与后端实现的对应关系。")
        lines.append("")
        lines.append(f"- 前端 URL 数: {len(front_urls)}")
        lines.append(f"- 后端 REST 路由数: {len(back_routes)}")
        lines.append(f"- 前端定义但后端未注册的路由: {len(missing_url)}")
        lines.append("")
        if missing_url:
            lines.append("## 待补齐的路径")
            lines.append("")
            lines.append("| 前端路径 | 状态 |")
            lines.append("|---------|------|")
            for p in missing_url:
                lines.append(f"| `{p}` | ❌ 后端未注册 |")
        else:
            lines.append("✅ 前端定义的所有 URL 路径在后端均有对应路由。")
        lines.append("")
        out.write_text("\n".join(lines))
        print(f"\n✅ 已生成报告: {out}")

    if missing_url and args.check:
        print("\n❌ 存在前端调用路径后端未注册，契约校验未通过")
        raise SystemExit(1)

    if not missing_url:
        print("\n✅ 前端调用路径与后端路由契约已对齐")


if __name__ == "__main__":
    main()
