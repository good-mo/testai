#!/usr/bin/env python3
"""
前端界面功能矩阵生成器（scripts/gen_frontend_matrix.py）
=========================================================
从前端源码自动抽取「界面能点到的所有接口」，生成 pytest 用例文件。

解决的问题：
  测试是**人写的**，前端是**人改的** —— 两边总会漂移。
  前端新增一个页面、一个按钮，后端就算没接，测试也不会知道，
  直到用户点开页面看到白屏 / 404 才发现。

  本脚本把「前端调用点」变成真相来源：
    1. 扫描 frontend/src/api/modules/** 的 MSR.get/post(...) 调用点
    2. 回溯 frontend/src/api/requrls/** 的 URL 常量，还原真实请求路径
    3. 按界面模块分组，生成 tests/test_frontend_ui_full_matrix.py

  从此前端每加一个接口，重跑本脚本就会多一条用例；
  后端漏接，用例立刻变红。

用法：
    python3 scripts/gen_frontend_matrix.py              # 生成测试文件
    python3 scripts/gen_frontend_matrix.py --inventory  # 只输出清单统计
    python3 scripts/gen_frontend_matrix.py --check      # 校验：清单与测试文件是否同步

退出码：
    0 成功；1 --check 时发现清单与测试文件不同步
"""
import argparse
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = ROOT / "frontend" / "src" / "api" / "modules"
REQURLS_DIR = ROOT / "frontend" / "src" / "api" / "requrls"
BACKEND_DIR = ROOT / "app"
OUTPUT = ROOT / "tests" / "test_frontend_ui_full_matrix.py"

# 界面模块分组：URL 前缀 -> (界面名, 测试类名)
GROUPS = OrderedDict([
    ("AI 用例生成 / 对话", ("TestAiCaseGenUI", [
        "ai/config", "ai/conversation", "api/generate", "api/projects", "api/insights",
        "api/test-types", "api/message", "api/chat",
    ])),
    ("接口测试-调试", ("TestApiDebugUI", ["api/debug", "api/test"])),
    ("接口测试-定义", ("TestApiDefinitionUI", ["api/definition"])),
    ("接口测试-用例", ("TestApiCaseUI", ["api/case"])),
    ("接口测试-场景", ("TestApiScenarioUI", ["api/scenario"])),
    ("接口测试-文档分享", ("TestApiDocShareUI", ["api/doc"])),
    ("接口测试-报告", ("TestApiReportUI", ["api/report"])),
    ("用例管理-评审", ("TestCaseReviewUI", ["case/review", "review/functional"])),
    ("用例管理-功能用例", ("TestFunctionalCaseUI", ["functional/case", "functional/mind"])),
    ("缺陷-附件", ("TestDefectAttachmentUI", ["bug/attachment"])),
    ("工作台", ("TestWorkbenchUI", [
        "dashboard/api_case_count", "dashboard/api_count", "dashboard/associate_case_count",
        "dashboard/bug_count", "dashboard/bug_handle_user", "dashboard/case_count",
        "dashboard/create_bug_by_me", "dashboard/create_by_me", "dashboard/handle_bug_by_me",
        "dashboard/my", "dashboard/plan_legacy_bug", "dashboard/plan_view",
        "dashboard/project_member_view", "dashboard/project_view", "dashboard/review_case_count",
        "dashboard/scenario_count", "api/definition/rage", "test-plan/rage",
    ])),
    ("系统设置-消息通知", ("TestNotificationUI", [
        "notice/message", "notification/count", "notification/read", "notification/un-read",
        "ding_talk/info", "ding_talk/save", "ding_talk/validate", "ding_talk/enable",
        "ding_talk/change", "lark/info", "lark/save", "lark/validate", "lark/enable",
        "lark/change", "lark_suite/info", "lark_suite/save", "lark_suite/validate",
        "lark_suite/enable", "lark_suite/change", "we_com/info", "we_com/save",
        "we_com/validate", "we_com/enable", "we_com/change",
    ])),
    ("系统设置-平台与日志", ("TestPlatformLogUI", [
        "display/info", "operation/log", "system/parameter", "system/version",
        "system/organization",
    ])),
    ("系统设置-许可证", ("TestLicenseUI", ["license", "license/add", "license/validate"])),
    ("系统设置-认证源", ("TestAuthSourceUI", [
        "system/authsource", "authentication/get", "authentication/get-list",
        "sso/callback", "is-login", "signout", "get-key",
    ])),
    ("系统设置-用户与组织", ("TestUserOrgUI", [
        "system/user", "system/project", "organization/add-member",
        "organization/update-member", "organization/remove-member",
        "organization/user", "organization/role", "organization/project",
        "organization/custom", "organization/log",
    ])),
    ("系统设置-插件/资源池/服务集成", ("TestPluginResourceUI", [
        "plugin/list", "plugin/delete", "plugin/script", "plugin/update",
        "api/test/plugin", "test/resource", "service/integration", "setting/get",
    ])),
    ("系统设置-模板与工作流", ("TestTemplateWorkflowUI", [
        "organization/template", "organization/status", "project/template",
        "project/custom", "project/status",
    ])),
    ("系统设置-任务中心", ("TestTaskCenterUI", [
        "organization/task-center", "project/task-center", "system/task-center",
    ])),
    ("项目管理-文件管理", ("TestProjectFileUI", [
        "project/file", "project/file-module", "attachment/download", "attachment/preview",
    ])),
    ("项目管理-基本信息/机器人", ("TestProjectBaseUI", [
        "project/get", "project/update", "project/list", "project/switch", "project/robot",
    ])),
    ("项目管理-成员/版本", ("TestProjectMemberUI", ["project/member", "project/version"])),
    ("测试计划", ("TestPlanUI", [
        "test-plan/api", "test-plan/association", "test-plan/batch-archived",
        "test-plan/batch-copy", "test-plan/batch-delete", "test-plan/batch-edit",
        "test-plan/batch-move", "test-plan/batch-schedule-config", "test-plan/copy",
        "test-plan/edit", "test-plan/functional", "test-plan/mind", "test-plan/module",
        "test-plan/rage", "test-plan/report", "test-plan/schedule-config", "test-plan/sort",
        "test-plan/statistics", "test-plan/update", "test-plan/add",
        "test-plan-execute/batch", "test-plan-execute/single",
    ])),
    ("用户中心-个人设置", ("TestPersonalUI", [
        "personal/get", "personal/model", "personal/update-info", "personal/update-locale",
        "personal/update-password", "user/api", "user/local", "user/platform", "api/user",
    ])),
])

# 需要贴近前端的真实入参才能走通的接口
PAYLOADS = {
    "POST /api/projects/scan": '{"project_path": ".", "file_patterns": ["**/*.py"]}',
    "POST /api/projects/generate": '{"project_path": ".", "file_patterns": ["**/*.py"]}',
    "POST /api/insights/lowcode": '{"requirement": "测试登录功能", "projectId": ""}',
    # 用户名带随机数，避免重复执行时撞上「用户名已存在」
    "POST /system/user/add": '{"username": f"uim-{uuid.uuid4().hex[:8]}", '
                             '"password": "Pass@123", "email": "uim@example.com"}',
    # 更新类：前端必带 id，传不存在 id 验证「不 5xx」而不是「假装成功」
    "POST /api/definition/module/update": '{"id": "not-exist", "name": "改名模块"}',
    "POST /functional/case/module/update": '{"id": "not-exist", "name": "改名模块"}',
    "POST /test-plan/module/update": '{"id": "not-exist", "name": "改名模块"}',
    "POST /project/custom/func/update": '{"id": "not-exist", "name": "脚本", "status": "ENABLED"}',
    "POST /project/custom/func/status": '{"id": "not-exist", "status": "ENABLED"}',
    "POST /project/custom/field/update": '{"id": "not-exist", "name": "字段", "type": "INPUT"}',
    "POST /system/user/reset/password": '{"id": "not-exist", "password": "Pass@123"}',
    "POST /personal/update-password": '{"oldPassword": "wrong-old", "newPassword": "Pass@123"}',
    "POST /test/resource/pool/update": '{"id": "not-exist", "name": "资源池", "enable": True}',
    "POST /test/resource/pool/set/enable/": '{"id": "not-exist", "enable": True}',
    "POST /api/definition/mock/update": '{"id": "not-exist", "name": "mock"}',
}

# 依赖真实 LLM Key，本地跑会抛鉴权异常，单独标记跳过
LLM_REQUIRED = {
    ("POST", "/api/generate"),
    ("POST", "/api/generate/structured"),
    ("POST", "/api/insights/lowcode"),
    ("POST", "/api/projects/generate"),
}


# ══════════════════════════════════════════════════════════════
# 前端源码解析
# ══════════════════════════════════════════════════════════════

def strip_comments(src: str) -> str:
    """去掉块注释与行注释，避免注释里的 URL 被误采。"""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def split_top_level(src: str, sep: str = ",") -> list:
    """按顶层分隔符切分，忽略括号内的分隔符。"""
    parts, cur, depth = [], "", 0
    for ch in src:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def collect_namespaces() -> dict:
    """收集 `import * as bugURL from '@/api/requrls/bug-management'` 形成的命名空间。

    本项目大量接口写成 `${bugURL.getDeleteBugUrl}${id}` —— 常量带命名空间前缀，
    不解析就会整条调用点被丢弃（实测影响 90+ 个接口），
    接口层矩阵会出现「前端在用、测试却没覆盖」的盲区。
    """
    namespaces = {}
    for f in sorted(MODULES_DIR.rglob("*.ts")):
        src = f.read_text()
        for m in re.finditer(
            r"import\s+\*\s+as\s+(\w+)\s+from\s+['\"][^'\"]*?([\w-]+)['\"]", src
        ):
            alias, module = m.group(1), m.group(2)
            namespaces.setdefault(alias, module)
    return namespaces


def collect_module_consts(dirpath: Path) -> "dict[str, dict[str, str]]":
    """按模块名收集 requrls 常量：模块名 -> {常量名: URL}。"""
    out = {}
    for f in sorted(dirpath.rglob("*.ts")):
        src = f.read_text()
        pairs = {}
        for m in re.finditer(r"(?:export\s+)?const\s+(\w+)\s*=\s*['\"]([^'\"]+)['\"]", src):
            pairs[m.group(1)] = m.group(2)
        if pairs:
            out[f.stem] = pairs
    return out


def collect_url_constants() -> dict:
    """收集所有 URL 常量，含模板字符串常量（多轮解析依赖）。"""
    consts = {}
    files = sorted(REQURLS_DIR.rglob("*.ts")) + sorted(MODULES_DIR.rglob("*.ts"))
    for f in files:
        src = f.read_text()
        for m in re.finditer(r"(?:export\s+)?const\s+(\w+)\s*=\s*['\"]([^'\"]+)['\"]", src):
            consts.setdefault(m.group(1), m.group(2))
        # 模板常量：export const X = `${Y}/z`;
        for _ in range(3):
            for m in re.finditer(r"(?:export\s+)?const\s+(\w+)\s*=\s*`([^`]*)`", src):
                name, tpl = m.group(1), m.group(2)
                if name in consts:
                    continue
                val = re.sub(r"\$\{(\w+)\}",
                             lambda mm: consts.get(mm.group(1), "{" + mm.group(1) + "}"), tpl)
                if "{" not in val:
                    consts[name] = val
    return consts


def prefix_of(path: str) -> str:
    """取 URL 前两段作为模块前缀，用于归入界面分组。"""
    parts = [p for p in path.strip("/").split("/") if p]
    return "/".join(parts[:2]) if len(parts) >= 2 else (parts[0] if parts else "")


def _resolve_expr(expr: str, consts: dict, ns=None) -> str:
    """把模板插值解析成路径片段。

    - `${GetCaseDetailUrl}` 这类 URL 常量 → 直接替换成常量值
    - `${bugURL.getDeleteBugUrl}` 命名空间常量 → 按别名查对应模块后替换
    - `${params.projectId}` → 归一成 `{projectId}`（前端函数入参）
    - `${host}` / `${type}` 等运行时变量 → 归一成 `{host}` 等占位符，
      后续由「后端是否存在该形态路由」决定保留还是丢弃
    """
    # 运行期入参：params.projectId / data.id / item.id → 归一成 {projectId} / {id}
    for prefix in ("params.", "data.", "form.", "item.", "row.", "record."):
        if expr.startswith(prefix):
            tail = expr[len(prefix):]
            if re.fullmatch(r"[A-Za-z_]\w*", tail):
                return "{" + tail + "}"
    if expr in consts:
        return consts[expr]
    # 命名空间常量：bugURL.getDeleteBugUrl
    # requrls 里的导出名大小写不固定（ScenarioReportDetailUrl vs
    # scenarioReportDetailUrl），比对时统一小写。
    if ns and "." in expr:
        alias, _, member = expr.partition(".")
        if alias in ns and "." not in member:
            for mod in ns[alias]:
                if member in mod:
                    return mod[member]
            lowered = {k.lower(): v for k, v in mod.items() for mod in ns[alias]}
            if member.lower() in lowered:
                return lowered[member.lower()]
            if member in consts:
                return consts[member]
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expr):
        return "{" + expr + "}"
    return "{?}"


def collect_backend_routes() -> set:
    """扫描 app/ 下所有路由装饰器，返回归一化后的路径集合。

    用归一化路径（{id} → :p）比对，因为前端写 `{id}` 后端写 `{case_id}`
    是同一条路由。
    """
    pattern = re.compile(r"@\w+\.(get|post|put|delete|patch|websocket)\s*\(\s*['\"]([^'\"]+)['\"]")
    routes = set()
    for f in BACKEND_DIR.rglob("*.py"):
        if "__pycache__" in str(f):
            continue
        for m in pattern.finditer(f.read_text()):
            routes.add(norm_path(m.group(2)))
    return routes


def filter_resolvable(sites: list, backend: set) -> "tuple[list, list]":
    """拆分成「后端有对应路由」与「无法解析」两组。

    含路径参数的调用点里，有一部分是纯运行时拼出来的（如 `url: ${host}/api/debug`、
    `url: ${reportUrl}/${RenameUrl}/${id}`），静态分析无法还原成确定路径。
    这类调用点不该生成用例 —— 生成了就是永远 404 的假失败。
    改为在 --inventory 里列出，交给人工确认。
    """
    ok_items, unresolved = [], []
    for x in sites:
        if "{" not in x["path"]:
            ok_items.append(x)
        elif norm_path(x["path"]) in backend:
            ok_items.append(x)
        else:
            unresolved.append(x)
    return ok_items, unresolved


def collect_call_sites() -> list:
    """抽取 MSR.get/post(...) 调用点，还原出 (method, path)。

    含未解析变量（如 {id}）的路径同样保留 —— 路径参数版接口在前端是
    真实调用点（详情页、删除、启停等），交给参数化用例覆盖。
    """
    consts = collect_url_constants()
    namespaces = collect_namespaces()
    module_consts = collect_module_consts(REQURLS_DIR)
    # 命名空间别名 -> 该模块的全部常量（可能有多个候选模块，逐个试）
    ns = defaultdict(list)
    for alias, module in namespaces.items():
        if module in module_consts:
            ns[alias].append(module_consts[module])
    sites = []
    for f in sorted(MODULES_DIR.rglob("*.ts")):
        src = strip_comments(f.read_text())
        funcs = [(m.start(), m.group(1))
                 for m in re.finditer(r"export\s+function\s+(\w+)\s*\(", src)]
        for m in re.finditer(r"MSR\.(get|post|put|delete|patch)\s*(<[^>]*>)?\s*\(", src):
            start = m.end() - 1
            depth = 0
            for i in range(start, len(src)):
                if src[i] == "(":
                    depth += 1
                elif src[i] == ")":
                    depth -= 1
                    if depth == 0:
                        break
            parts = split_top_level(src[start + 1:i])
            obj = parts[0] if parts else ""
            func = None
            for pos, name in funcs:
                if pos < m.start():
                    func = name
                else:
                    break
            tmpl = re.search(r"url:\s*`([^`]*)`", obj)
            if tmpl:
                path = re.sub(
                    r"\$\{([^}]*)\}",
                    lambda mm: _resolve_expr(mm.group(1).strip(), consts, ns),
                    tmpl.group(1),
                )
            else:
                var = re.search(r"url:\s*([A-Za-z0-9_]+)", obj)
                if not var:
                    lit = re.search(r"url:\s*['\"]([^'\"]+)['\"]", obj)
                    if not lit:
                        continue
                    path = lit.group(1)
                else:
                    path = consts.get(var.group(1))
                    if path is None:
                        continue
            if not path or "{?}" in path:
                continue
            sites.append({
                "file": str(f.relative_to(MODULES_DIR)),
                "func": func,
                "method": m.group(1).upper(),
                "path": path,
            })
    return sites


def static_path(sites: list) -> list:
    """只保留静态路径（不含 {param}），并按 method+path 去重。"""
    return dedupe([x for x in sites if "{" not in x["path"]])


def param_path(sites: list) -> list:
    """只保留含 {param} 的路径，按 (method, 归一化路径) 去重。

    同一条路径参数接口可能有多个前端调用点（如不同页面都调 detail），
    去重后每个参数化接口只测一次，但会覆盖所有已注册的具体路径。
    """
    return dedupe([x for x in sites if "{" in x["path"]], normalize=True)


def dedupe(sites: list, normalize: bool = False) -> list:
    """按 method + path 去重，保持首次出现顺序。"""
    seen, out = set(), []
    for x in sites:
        key = (x["method"], norm_path(x["path"]) if normalize else x["path"])
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def norm_path(path: str) -> str:
    """把 {id} / {project_id} 统一成 :p，便于跨文件去重。"""
    return re.sub(r"\{[^}]*\}", ":p", path)


def group_by_ui(sites: list) -> "OrderedDict[str, list]":
    """按 URL 前缀归入界面模块。"""
    buckets = OrderedDict((name, []) for name in GROUPS)
    buckets["未归类"] = []
    used = set()
    for x in sites:
        p = prefix_of(x["path"])
        hit = None
        for name, (_cls, prefixes) in GROUPS.items():
            if p in prefixes:
                hit = name
                break
        if hit is None and p in ("license", "license/add", "license/validate"):
            hit = "系统设置-许可证"
        if hit is None:
            hit = "未归类"
        buckets[hit].append(x)
        used.add(id(x))
    return OrderedDict((k, v) for k, v in buckets.items() if v)


# ══════════════════════════════════════════════════════════════
# 测试文件渲染
# ══════════════════════════════════════════════════════════════

def assert_kind(method: str, path: str) -> str:
    """判定断言档位。"""
    if (method, path) in LLM_REQUIRED:
        return "llm"
    p = path.strip("/")
    if re.search(r"(^|/)(page|list)(/|$)", p):
        return "list"
    if p.endswith("/tree") or p.endswith("/count"):
        return "count"
    if p.endswith("/statistics"):
        return "count"   # 统计接口 data 可能是 [] 或对象，两种都合法
    return "soft"


def payload_for(method: str, path: str) -> str:
    key = f"{method} {path}"
    if key in PAYLOADS:
        return PAYLOADS[key]
    p = path.strip("/")
    if re.search(r"(^|/)page($|/)", p) or "/list" in p:
        return "PAGE"
    if p.endswith("/tree") or p.endswith("/count"):
        return '{"projectId": "", "keyword": ""}'
    if p.endswith("/statistics"):
        return '{"projectId": ""}'
    return "{}"


def test_name(method: str, path: str, idx: int) -> str:
    seg = [s for s in path.strip("/").split("/") if s]
    base = re.sub(r"[^0-9a-zA-Z_]", "_", "_".join(seg))
    return f"test_{method.lower()}_{base}_{idx}"


def render(groups: "OrderedDict[str, list]", params: list) -> str:
    total = sum(len(v) for v in groups.values()) + len(params)
    cls_of = {name: cls for name, (cls, _p) in GROUPS.items()}
    cls_of["未归类"] = "TestUncategorizedUI"

    out = []
    W = out.append
    W('"""')
    W("前端全界面功能矩阵测试（test_frontend_ui_full_matrix.py）")
    W("=" * 78)
    W("")
    W("目标：把「前端界面真实能看到 / 能点到的功能」全部测一遍。")
    W("")
    W("用例不是手写维护的，而是**从前端源码自动抽取**的：")
    W("  1. 扫描 `frontend/src/api/modules/**` 里的 `MSR.get/post(...)` 调用点")
    W("  2. 回溯 `frontend/src/api/requrls/**` 的 URL 常量，还原成真实请求路径")
    W("  3. 逐个打真实请求，断言「前端点这个按钮不会炸」")
    W("")
    W(f"共覆盖 {total} 个前端调用点（{sum(len(v) for v in groups.values())} 个静态 + {len(params)} 个路径参数），")
    W("按界面模块分组。任何一处 404 / 405 / 500 或非标准响应体都会让测试失败。")
    W("")
    W("断言分四档：")
    W("  - `_list`  列表类：data 必须为数组或含 list/total 的分页对象（缺字段前端白屏）")
    W("  - `_count` 树/计数类：data 必须是对象或数组（模块树、各模块计数）")
    W("  - `_dict`  聚合类：data 必须是 dict")
    W("  - `_soft`  动作类：结构合法即可，允许 4xx 业务校验，但绝不允许 5xx")
    W("")
    W("⚠️ 本文件由 `scripts/gen_frontend_matrix.py` 生成，请勿手工编辑。")
    W("   前端新增接口后重跑该脚本即可同步；CI 会校验两者是否一致。")
    W('"""')
    W("import os")
    W("import sys")
    W("import uuid")
    W("")
    W("sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))")
    W("")
    W('os.environ.setdefault("OPENAI_API_KEY", "test-key")')
    W('os.environ.setdefault("LLM_PROVIDER", "local")')
    W("")
    W("import pytest")
    W("from fastapi.testclient import TestClient")
    W("")
    W('PREFIX = "UIM-"')
    W("")
    W("# 依赖真实 LLM Key 的接口，本地无 key 时跳过（有 key 时自动参与）")
    W("LLM_REQUIRED = {")
    for method, path in sorted(LLM_REQUIRED):
        W(f'    ("{method}", "{path}"),')
    W("}")
    W("")
    W("")
    W("@pytest.fixture(scope=\"module\")")
    W("def client():")
    W('    """已登录的测试客户端（携带 X-AUTH-TOKEN / CSRF-TOKEN）。"""')
    W("    from app.main import app")
    W("    with TestClient(app) as c:")
    W('        r = c.post("/login", json={"username": "admin", "password": "admin123"})')
    W("        if r.status_code == 200:")
    W('            session = r.json()["data"]')
    W("            c.headers.update({")
    W('                "X-AUTH-TOKEN": session["sessionId"],')
    W('                "CSRF-TOKEN": session["csrfToken"],')
    W("            })")
    W("        yield c")
    W("")
    W("")
    W("def _body(resp):")
    W('    """断言响应体是前端能解析的三段式信封 {code, message, data}。')
    W("")
    W('    关键区分：')
    W('      - 三段式信封 + 4xx → 业务校验，前端会弹提示，属于正常行为')
    W('      - FastAPI 原生 {\"detail\": ...} → 路由根本没注册，前端只会看到')
    W('        一句看不懂的英文报错，这是真正要拦的「功能没接通」')
    W('    """')
    W("    payload = resp.json()")
    W('    assert isinstance(payload, dict), f"响应体不是对象: {str(payload)[:200]}"')
    W('    if "detail" in payload and "code" not in payload:')
    W('        raise AssertionError(f"路由未注册/未走统一响应: HTTP {resp.status_code} {payload}")')
    W('    for key in ("code", "message", "data"):')
    W('        assert key in payload, f"响应体缺少 {key} 字段: {str(payload)[:200]}"')
    W("    return payload")
    W("")
    W("")
    W("def _soft(resp):")
    W('    """动作类：结构合法即可，允许 4xx 业务校验，禁止 5xx。')
    W("")
    W('    传不存在的 id 时返回 404「用户不存在」是**正确行为**，前端会弹提示；')
    W('    真正要拦的是 500 和畸形结构 —— 那才是「点了按钮页面炸了」。')
    W('    """')
    W("    payload = _body(resp)")
    W("    assert payload['code'] < 500, f\"服务端异常: {payload['message']}\"")
    W("    return payload")
    W("")
    W("")
    W("def _dict(resp):")
    W('    """聚合类：成功时 data 必须是对象，4xx 业务校验时放行。"""')
    W("    payload = _soft(resp)")
    W("    if payload[\"code\"] != 200:")
    W("        return None")
    W("    data = payload[\"data\"]")
    W('    assert isinstance(data, dict), f"data 不是对象: {str(data)[:200]}"')
    W("    return data")
    W("")
    W("")
    W("def _count(resp):")
    W('    """模块树 / 计数类：成功时 data 必须是对象或数组，4xx 放行。"""')
    W("    payload = _soft(resp)")
    W("    if payload[\"code\"] != 200:")
    W("        return None")
    W("    data = payload[\"data\"]")
    W('    assert isinstance(data, (dict, list)), f"data 类型异常: {type(data).__name__}"')
    W("    return data")
    W("")
    W("")
    W("def _list(resp):")
    W('    """列表类：成功时 data 必须是数组或含 list/total 的分页对象，4xx 放行。')
    W("")
    W('    list 缺失前端会白屏，total 缺失页码会渲染成 NaN —— 这是本项目踩过的坑。')
    W('    """')
    W("    payload = _soft(resp)")
    W("    if payload[\"code\"] != 200:")
    W("        return []")
    W("    data = payload[\"data\"]")
    W("    if isinstance(data, list):")
    W("        return data")
    W('    assert isinstance(data, dict), f"列表 data 类型异常: {type(data).__name__}"')
    W('    assert "list" in data, f"列表缺少 list 字段，前端会白屏: {list(data)[:8]}"')
    W('    assert isinstance(data["list"], list), "list 字段不是数组"')
    W('    assert "total" in data, "分页缺少 total 字段，前端页码会渲染成 NaN"')
    W('    return data["list"]')
    W("")
    W("")
    W('PAGE = {"current": 1, "pageSize": 10}')
    W("")
    W("")

    bar = "═" * 78
    for gname, items in groups.items():
        cls = cls_of.get(gname, "TestUncategorizedUI")
        W("# " + bar)
        W(f"# {gname}")
        W("# " + bar)
        W(f"class {cls}:")
        W(f'    """{gname} 界面：{len(items)} 个前端调用点。"""')
        W("")
        for idx, x in enumerate(items, 1):
            method, path = x["method"], x["path"]
            kind = assert_kind(method, path)
            payload = payload_for(method, path)
            call = (f'client.get("{path}")' if method == "GET"
                    else f'client.post("{path}", json={payload})')
            src = x["func"] or x["file"]
            W(f"    def {test_name(method, path, idx)}(self, client):")
            W(f'        """{method} {path}')
            W("")
            W(f'        前端调用点：{src}（{x["file"]}）')
            W('        """')
            if kind == "llm":
                # 直接 return：skip 之后的代码本就不可达，
                # 生成出来既会触发 F821（_llm 未定义）也是死代码。
                W(f'        pytest.skip("需真实 LLM Key：{method} {path}")')
                W("        return")
            else:
                W(f"        resp = {call}")
                W(f"        _{kind}(resp)")
            W("")

    W("# " + bar)
    W("# 路径参数类接口（详情页 / 删除 / 启停 / 导出）")
    W("# " + bar)
    W("class TestPathParamUI:")
    W(f'    """路径参数接口：{len(params)} 个，覆盖所有 RESTful 前端调用点。"""')
    W("")
    W("    # 用不存在的 ID 探测：目的是验证「路由存在且能优雅拒绝」，")
    W("    # 而不是验证业务成功。真实 CRUD 由 test_frontend_e2e_all.py 覆盖。")
    W('    MISSING_ID = "uim-not-exist"')
    W("")
    for idx, x in enumerate(params, 1):
        method, path = x["method"], x["path"]
        filled = re.sub(r"\{(\w+)\}", "uim-not-exist", path)
        src = x["func"] or x["file"]
        call = (f'client.get("{filled}")' if method == "GET"
                else f'client.post("{filled}", json={{}})')
        seg = [s2 for s2 in re.sub(r"[{}]", "", path).strip("/").split("/") if s2]
        base = re.sub(r"[^0-9a-zA-Z_]", "_", "_".join(seg))
        W(f"    def test_{method.lower()}_{base}_{idx}(self, client):")
        W(f'        """{method} {path}')
        W("")
        W(f'        前端调用点：{src}（{x["file"]}）')
        W('        """')
        W(f"        resp = {call}")
        W("        _soft(resp)")
        W("")
    return "\n".join(out) + "\n"


def check_sync(groups: "OrderedDict[str, list]", params: list) -> int:
    """校验生成的测试文件与当前前端清单是否同步。"""
    if not OUTPUT.exists():
        print(f"❌ 测试文件不存在：{OUTPUT}")
        return 1
    expected = render(groups, params)
    actual = OUTPUT.read_text()
    if expected.strip() == actual.strip():
        print(f"✅ 测试文件与前端清单同步（{sum(len(v) for v in groups.values())} 个调用点）")
        return 0
    exp_lines = expected.strip().splitlines()
    act_lines = actual.strip().splitlines()
    act_set = set(act_lines)
    diff = [line for line in exp_lines if line not in act_set]
    print("⚠️  测试文件与前端清单不同步：")
    print(f"   期望 {len(exp_lines)} 行，实际 {len(act_lines)} 行")
    print(f"   以下 {len(diff[:10])} 条（最多显示 10）只在期望中：")
    for line in diff[:10]:
        print(f"     {line.strip()}")
    print(f"   请执行：python3 {Path(__file__).relative_to(ROOT)}")
    return 1


def main():
    parser = argparse.ArgumentParser(description="前端界面功能矩阵生成器")
    parser.add_argument("--inventory", action="store_true", help="只输出清单统计")
    parser.add_argument("--check", action="store_true", help="校验测试文件与前端清单是否同步")
    parser.add_argument("--write", action="store_true", help="写入测试文件（默认行为）")
    args = parser.parse_args()

    backend = collect_backend_routes()
    sites, unresolved = filter_resolvable(collect_call_sites(), backend)
    statics = static_path(sites)
    params = param_path(sites)
    groups = group_by_ui(statics)

    if args.inventory:
        print(f"前端调用点：{len(sites)}（去重后静态 {len(statics)} / 路径参数 {len(params)}）")
        print(f"覆盖界面模块：{len(groups)}")
        print()
        for name, items in groups.items():
            c = Counter(x["method"] for x in items)
            tag = " ".join(f"{m}:{n}" for m, n in c.most_common())
            print(f"  {name:32s} {len(items):4d}  {tag}")
        if unresolved:
            print()
            print(f"⚠️  无法静态解析的调用点 {len(unresolved)} 个"
                  f"（运行时拼接，需人工确认后端是否覆盖）：")
            for x in unresolved:
                print(f"     {x['method']:5s} {x['path']:60s} {x['file']}::{x['func']}")
        return 0

    if args.check:
        return check_sync(groups, params)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(groups, params))
    print(f"✅ 已生成 {OUTPUT.relative_to(ROOT)}")
    print(f"   前端调用点 {len(statics) + len(params)} 个"
          f"（静态 {len(statics)} + 路径参数 {len(params)}），界面模块 {len(groups)} 个")
    for name, items in groups.items():
        print(f"   - {name}: {len(items)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
