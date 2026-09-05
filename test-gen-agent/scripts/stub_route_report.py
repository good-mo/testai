#!/usr/bin/env python3
"""
空壳路由（stub / 假成功）报告脚本
=================================
背景：仓库存在大量「占位兼容 shim」路由——函数体几乎没有任何
service/repo/store/DB 访问，只是 `return ok(None)` / 读完请求体就
`return ok()`。前端提示「操作成功」但后端什么都没做，测试断言只看
200 也覆盖不到（"假成功"）。

本脚本用 AST 静态识别这类「空壳」路由并产出报告，用于：
1. 摸清存量空壳规模与按文件分布，支撑后续分域「接真实 Service」或
   「统一标注 stub 返回标识」（见 app/core/response.py 的 stub()）。
2. 通过基线门禁防止空壳继续新增（增量回归保护）。

识别口径（宁缺毋滥，优先准确，避免误伤真业务路由）：
- 路由处理函数体内「不出现」任何 service/repo/store/DB 等业务数据访问
  标识符（副作用） → 无副作用候选；
- 候选再分两类：
    A  假成功占位：函数体很薄（≤8 行）且不转发到本文件自定义 helper
        （读请求体后即 return ok 这类最典型）；
    X  待人工核查：无副作用但转发到本文件自定义 helper（helper 是否真空
        需再追一层），或体量超阈。

用法：
    python3 scripts/stub_route_report.py --report            # 生成 reports/stub_routes.md
    python3 scripts/stub_route_report.py --check             # 对比基线，空壳增加则告警
    python3 scripts/stub_route_report.py --update-baseline   # 以当前扫描结果为基线
"""
import argparse
import ast
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

ROOT = Path(__file__).parent.parent
REPORT_PATH = ROOT / "reports" / "stub_routes.md"

# 业务数据访问层的副作用特征：一旦函数体内命中即「不是空壳」。
# 覆盖 service/repo/store/db/连接/游标/写库/建档模型校验等常见命名，
# 含 apitest/module_store 等简写 store 与 model_validate 落库前校验。
SIDE_EFFECT_PATTERN = re.compile(
    r"(\b\w*(service|repo|store)\w*\b|"
    r"\b(db|conn|session|cursor)\b|"
    r"\.execute|\.executemany|\.commit\(|\.save\(|\.insert\(|"
    r"\.update\(|\.delete\(|\.create\(|\.query\(|\.fetchall\(|\.fetchone\(|"
    r"\.soft_delete\(|\.purge\(|\.archive\(|\.hard_delete\(|"
    r"\.add\(|\.flush\(|model_validate)",
    re.IGNORECASE,
)

# 请求体归一化辅助调用——属于「读入」而非业务副作用。
READ_HELPER = {"read_body", "read_form_or_json", "read_writable_body"}

# 不参与扫描的文件（聚合/静态托管/入口等非业务路由）。
SKIP_FILES = {
    "app/main.py",
}

# 路由装饰器：@<router_var>.(get|post|put|delete|patch)("<path>")
ROUTE_DECORATOR_PATTERN = re.compile(
    r"@(\w+)\.(get|post|put|delete|patch)\s*\(\s*[\"']([^\"']+)[\"']"
)

# 单个函数最大业务行数阈值：超过视为「非薄」，不再判 A。
MAX_THIN_LINES = 8


def _side_effect_refs(node: ast.AST) -> list:
    """收集函数体内所有命中「业务数据访问层命名」的标识符引用。

    覆盖调用与非调用两种形态：
      - 直接调用：`case_service.soft_delete(id)` → Name(case_service)
      - 作为参数 / 中间对象：`asyncio.to_thread(case_service.list_cases)`、
        `db.execute(...)`、`store.save(x)` → 其 Name / Attribute 根同样命中。
    只要函数体内「出现」这类业务对象引用即判有副作用，不局限于被调函数名。
    """
    hits = []
    seen = set()
    for sub in ast.walk(node):
        name = None
        if isinstance(sub, ast.Name):
            name = sub.id
        elif isinstance(sub, ast.Attribute):
            name = sub.attr
        if name and name not in seen:
            seen.add(name)
            if SIDE_EFFECT_PATTERN.search(name):
                hits.append(name)
    return hits


def _read_helper_calls(node: ast.AST) -> list:
    """收集读请求体类辅助调用。"""
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            fn = sub.func
            name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
            if name in READ_HELPER:
                out.append(name)
    return out


def _return_shapes(node: ast.AST, content: str) -> list:
    """收集函数体内 return 表达式的源码形态（用于人工判断）。"""
    shapes = []
    for r in ast.walk(node):
        if isinstance(r, ast.Return):
            seg = ast.get_source_segment(content, r.value) if r.value is not None else "<bare>"
            shapes.append((seg or "").strip())
    return shapes


def _file_top_defs(tree: ast.AST) -> set:
    """收集一个文件顶层定义的函数名（用于识别「转发到 helper」）。"""
    defs = set()
    for n in ast.iter_child_nodes(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.add(n.name)
    return defs


def scan_routes():
    """扫描全库路由函数，返回带 AST 分析结果的路由记录。"""
    records = []
    app_dir = ROOT / "app"
    for py_file in sorted(app_dir.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        rel = str(py_file.relative_to(ROOT))
        if rel in SKIP_FILES:
            continue
        try:
            content = py_file.read_text()
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            continue

        file_defs = _file_top_defs(tree)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            routes = []
            for dec in node.decorator_list:
                seg = ast.get_source_segment(content, dec)
                m = re.match(r"\w+\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']", seg or "")
                if m:
                    routes.append((m.group(1).upper(), m.group(2)))
            if not routes:
                continue

            side = _side_effect_refs(node)
            reads = _read_helper_calls(node)
            shapes = _return_shapes(node, content)
            body_src = ast.get_source_segment(content, node) or ""
            records.append({
                "file": rel,
                "line": node.lineno,
                "name": node.name,
                "routes": routes,
                "side": sorted(set(side)),
                "reads": reads,
                "shapes": shapes,
                "nlines": body_src.count("\n") + 1,
                "_node": node,
                "_file_defs": file_defs,
            })
    return records


def _call_targets(node: ast.AST) -> set:
    """收集函数体内出现的所有调用目标名（用于识别转发）。"""
    if node is None:
        return set()
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            fn = sub.func
            if isinstance(fn, ast.Name):
                out.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                out.add(fn.attr)
    return out


def classify(rec: dict) -> str:
    """判定路由是否为空壳假成功占位。

      ''  — 有副作用，非空壳
      'A' — 假成功占位：无副作用 + 函数体很薄 + 不转发自定义 helper
      'X' — 无副作用但转发到本文件自定义 helper / 体量超阈（需人工核查）
    """
    if rec["side"]:
        return ""
    # 转发判定：调用本文件顶层自定义 helper → 归 X 人工核查
    calls = _call_targets(rec.get("_node"))
    if calls & rec.get("_file_defs", set()):
        return "X"
    # 体量超阈或返回明显较复杂结构 → 不判典型占位（但仍无副作用，记 X 供核查）
    if rec["nlines"] > MAX_THIN_LINES:
        return "X"
    return "A"


def load_frontend_urls() -> set:
    """预扫前端 requrls 中的全部 URL 字面量，用于标注「前端是否引用」。"""
    urls = set()
    fe_dir = ROOT / "frontend" / "src" / "api"
    if not fe_dir.exists():
        return urls
    for ts in fe_dir.rglob("*.ts"):
        try:
            content = ts.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        for m in re.findall(r"['\"](/[^'\"]*)['\"]", content):
            urls.add(m)
    return urls


def frontend_linked(path: str, urls: set) -> bool:
    """后端路由 path 是否在前端 URL 清单中被直接引用（或其子路径）。"""
    if path in urls:
        return True
    return any(path in u or u in path for u in urls)


def build_report() -> str:
    records = scan_routes()
    urls = load_frontend_urls()
    by_cat = {"A": [], "X": []}
    for rec in records:
        cat = classify(rec)
        if not cat:
            continue
        fe = any(frontend_linked(p, urls) for _m, p in rec["routes"])
        rec["frontend"] = fe
        by_cat[cat].append(rec)

    a, x = len(by_cat["A"]), len(by_cat["X"])
    total = a + x
    by_file = defaultdict(int)
    for rec in by_cat["A"] + by_cat["X"]:
        by_file[rec["file"]] += 1

    lines = []
    lines.append("# 空壳路由（stub / 假成功）报告")
    lines.append("")
    lines.append("> 由 `scripts/stub_route_report.py` 自动生成。识别口径：路由处理函数体内")
    lines.append("> 不存在对 service/repo/store/DB 等业务数据访问层的副作用调用。")
    lines.append("")
    lines.append(f"- 扫描路由函数总数：**{len(records)}**")
    lines.append(f"- 疑似空壳路由：**{total}**（A 假成功占位 {a} · X 待人工核查 {x}）")
    lines.append("")
    lines.append("## 按文件分布（疑似空壳）")
    lines.append("")
    lines.append("| 路由文件 | 疑似空壳数 |")
    lines.append("|----------|------------|")
    for f in sorted(by_file, key=lambda k: -by_file[k]):
        lines.append(f"| `{f}` | {by_file[f]} |")
    lines.append("")
    lines.append("## A 类：假成功占位（最需修复——接真实 Service，或确认纯兼容后返回显式 stub()）")
    lines.append("")
    if not by_cat["A"]:
        lines.append("_无_")
    else:
        lines.append("| 文件 | 行 | 函数 | 方法 | 路径 | 前端引用 | 返回形态 |")
        lines.append("|------|----|------|------|------|----------|----------|")
        for rec in sorted(by_cat["A"], key=lambda r: (r["file"], r["line"])):
            for _m, p in rec["routes"]:
                fe = "✅" if rec["frontend"] else "—"
                shape = "; ".join(rec["shapes"][:2]) or "—"
                if len(shape) > 70:
                    shape = shape[:70] + "…"
                lines.append(
                    f"| `{rec['file']}` | {rec['line']} | {rec['name']} | "
                    f"{_m} | `{p}` | {fe} | `{shape}` |"
                )
    lines.append("")
    lines.append("## X 类：无副作用但转发 helper / 体量超阈（需人工核查是否真空壳）")
    lines.append("")
    if not by_cat["X"]:
        lines.append("_无_")
    else:
        lines.append("| 文件 | 行 | 函数 | 方法 | 路径 | 前端引用 | 行数 |")
        lines.append("|------|----|------|------|------|----------|------|")
        for rec in sorted(by_cat["X"], key=lambda r: (r["file"], r["line"])):
            for _m, p in rec["routes"]:
                fe = "✅" if rec["frontend"] else "—"
                lines.append(
                    f"| `{rec['file']}` | {rec['line']} | {rec['name']} | "
                    f"{_m} | `{p}` | {fe} | {rec['nlines']} |"
                )
    lines.append("")
    lines.append(f"_自动生成于 {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    return "\n".join(lines)


def _stub_count() -> tuple:
    """返回 (A 数, X 数, A+X 数)。"""
    records = scan_routes()
    a = x = 0
    for rec in records:
        c = classify(rec)
        if c == "A":
            a += 1
        elif c == "X":
            x += 1
    return a, x, a + x


def main():
    parser = argparse.ArgumentParser(description="空壳路由报告工具")
    parser.add_argument("--report", action="store_true", help="生成 reports/stub_routes.md")
    parser.add_argument("--check", action="store_true", help="对比基线，空壳增加则告警")
    parser.add_argument("--update-baseline", action="store_true", help="以当前扫描结果为基线")
    args = parser.parse_args()

    if args.report or args.update_baseline:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(build_report())
        a, x, t = _stub_count()
        print(f"✅ 已生成 {REPORT_PATH}（A 假成功占位 {a} · X 待核查 {x} · 合计 {t}）")

    if args.check:
        a, x, t = _stub_count()
        baseline_path = REPORT_PATH
        if baseline_path.exists():
            txt = baseline_path.read_text()
            m = re.search(r"疑似空壳路由：\*\*(\d+)\*\*", txt)
            baseline = int(m.group(1)) if m else -1
        else:
            baseline = -1
        print(f"当前疑似空壳 {t}；基线 {baseline if baseline >= 0 else '(未生成基线)'}")
        if baseline >= 0 and t > baseline:
            print(f"❌ 疑似空壳较基线增加 {t - baseline} 个，请勿新增占位路由；确需占位请返回显式 stub() 标识。")
            sys.exit(1)
        print("✅ 疑似空壳未超基线（无新增占位）")
        records = scan_routes()
        by_file = defaultdict(int)
        for rec in records:
            if classify(rec):
                by_file[rec["file"]] += 1
        print("疑似空壳分布 TOP 10：")
        for f, n in sorted(by_file.items(), key=lambda kv: -kv[1])[:10]:
            print(f"  {n:>4}  {f}")


if __name__ == "__main__":
    main()
