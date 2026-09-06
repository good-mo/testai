#!/usr/bin/env python3
"""
按钮级覆盖矩阵生成器（scripts/button_matrix.py）
================================================
回答一个问题：**每个按钮点下去，后端接住了吗？**

scripts/gen_frontend_matrix.py 已经把「前端 api/modules 里的调用点」
全部测了一遍（658 条，100% 覆盖）。但那测的是**接口层**，不是**按钮层**。
二者之间隔着三层：

    <a-button @click="saveScenarioConfig">
        └─ handler 定义在 useStepNodeEdit() 里（不在本文件的 <script setup>）
            └─ handler 里调用 api 函数
                └─ api 函数 → MSR.post('/xxx')

中间断任何一层，按钮就是死的 —— 而接口层测试完全看不见。

本脚本反向从按钮出发，逐层回溯，把每个按钮归到五类之一：

    ① 已接线    —— 能追到后端接口（由 gen_frontend_matrix 保证接口可用）
    ② 纯前端态  —— 只切换抽屉/弹窗/输入框，本来就不该发请求
    ③ 本地逻辑  —— handler 存在但只做本地计算（排序/选中/复制）
    ④ 未定义    —— handler 压根没定义，点了没反应（真 Bug）
    ⑤ 跨组件    —— emit 给父组件，父组件未在本仓库接通或需人工确认

用法：
    python3 scripts/button_matrix.py                # 输出分类统计
    python3 scripts/button_matrix.py --report       # 输出完整清单
    python3 scripts/button_matrix.py --check        # 校验：④未定义 数量 <= 阈值（CI 卡口）
    python3 scripts/button_matrix.py --json         # 输出 JSON 供其他工具消费

退出码：
    0 正常；1 --check 时发现新增「未定义 handler」死按钮
"""
import argparse
import json
import re
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"

sys.path.insert(0, str(ROOT / "scripts"))
import gen_frontend_matrix as g  # noqa: E402  复用其前端源码解析与后端路由扫描

# 需要关注的交互式元素（按钮 + 下拉项 + 表格更多操作）
INTERACTIVE = (
    "a-button", "MsButton", "ms-button",
    "a-menu-item", "a-dropdown-option", "MsTableMoreAction",
)
BTN_RE = re.compile(
    r"<(" + "|".join(INTERACTIVE) + r")([^>]*?)(?:/?)>", re.S
)
# 触发动作的属性
TRIGGER_ATTR = re.compile(r'@(?:click|select|ok|confirm)\s*=\s*"([^"]*)"')
# 事件桥：父组件 @some-event="handler"
EVENT_BIND = re.compile(r"@([\w:-]+)\s*=\s*\"([^\"]*)\"")
# 子组件抛事件：emit('some-event') / emits('some-event')
EMIT_CALL = re.compile(r"emits?\s*\(\s*'([^']+)'")
# import { xxx } from '...'
IMPORT_RE = re.compile(
    r"import\s*(?:type\s*)?\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]", re.S
)
# 组合式函数解构：const { a, b } = useXxx(...)
COMPOSABLE_RE = re.compile(r"const\s*\{([^}]+)\}\s*=\s*(use\w+)\s*\(")

CATEGORIES = OrderedDict([
    ("wired", "① 已接线：能追到后端接口"),
    ("ui", "② 纯前端态：开关抽屉/弹窗，不发请求"),
    ("local", "③ 本地逻辑：只做本地计算"),
    ("undefined", "④ 未定义：handler 不存在，点了没反应"),
    ("cross", "⑤ 跨组件：emit 给父组件"),
])


def strip_noise(text: str) -> str:
    """去掉注释，避免注释掉的按钮被当成真按钮。

    本项目 conversation.vue 里就有一整块被 <!-- --> 注释掉的发送按钮，
    不剥掉会误报成死按钮。
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def kebab_to_pascal(name: str) -> str:
    """ms-confirm-user-selector -> MsConfirmUserSelector。

    模板里写 <ms-popconfirm>，文件名是 index.vue 但目录名是 ms-popconfirm，
    两边形态不同，统一成 Pascal 才能对上。
    """
    return "".join(w.capitalize() for w in re.split(r"[-_]", name) if w)


def component_names(rel: str) -> "set[str]":
    """一个 .vue 文件在模板里可能被写成哪些组件名，返回归一化的小写候选集。

    例：components/pure/ms-popconfirm/index.vue
        → {index, mspopconfirm, pure, components, msPopconfirm, ms-popconfirm, ...}
    模板里写 <MsPopconfirm>，只有带上目录名（去连字符 + 小写）才能对上。
    """
    parts = Path(rel).parts
    stem = Path(rel).stem            # index.vue -> index
    names = {stem, *(x for x in parts if x and x != rel)}
    names |= {kebab_to_pascal(x) for x in names}
    names |= {x.replace("-", "").replace("_", "") for x in names}
    return {x.lower() for x in names if x}


def kebab_to_camel(name: str) -> str:
    """remote-func -> remoteFunc。Vue 模板用连字符，props 用驼峰。"""
    head, *rest = re.split(r"[-_]", name)
    return head + "".join(w.capitalize() for w in rest)


def _balanced(src: str, start: int) -> str:
    """从 start（指向 '{'）截取到配对 '}' 的内容。"""
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i]
    return src[start:]


def bodies_of(script: str) -> "dict[str, str]":
    """抽取 <script setup> 里的顶层函数体。

    支持三种写法：
        const foo = async (a, b) => { ... }
        const foo = () => expr
        async function foo(a) { ... }
    """
    out = {}
    for m in re.finditer(
        r"(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::[^=]+)?=>", script
    ):
        name = m.group(1)
        # 注意两点：
        # 1. 正则已吃掉这个箭头函数的 `=>`，必须从 m.end() 回退 2 字符定位；
        #    否则会找到函数体内部的嵌套箭头（如 validate(async (errors) => {...})），
        #    body 只截到第一个 '}'，props.remoteFunc 这类调用就丢了。
        # 2. `=>` 与 `{` 之间可能有空白（`() => {`），要先跳过再判断形态。
        tail = m.end()
        while tail < len(script) and script[tail] in " \t":
            tail += 1
        if script[tail:tail + 1] == "{":
            out[name] = _balanced(script, tail)
        else:
            end = script.find("\n", tail)
            out[name] = script[tail:end if end > 0 else len(script)]
    for m in re.finditer(r"(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{", script):
        out[m.group(1)] = _balanced(script, m.end() - 1)
    return out


def collect_units() -> "dict[str, dict]":
    """收集所有「分析单元」：.vue 组件 + 组合式函数文件。

    组合式函数（useXxx.ts）散落在组件同级目录，不是集中在 hooks/，
    所以这里全量扫描 src 下所有 use*.ts。
    """
    units = {}
    # 组合式函数（useXxx.ts）与辅助模块（如 views/setting/utils.ts）都导出 handler，
    # 全量纳入；api/ 下是接口声明层，不参与 handler 解析。
    files = list(SRC.rglob("*.vue")) + [
        f for f in SRC.rglob("*.ts")
        if "api" not in f.relative_to(SRC).parts[:1]
        and not f.name.endswith(".d.ts")
    ]
    for f in files:
        try:
            raw = f.read_text(errors="ignore")
        except OSError:
            continue
        text = strip_noise(raw)
        if f.suffix == ".vue" and "<script" not in text:
            continue
        script = text.split("<script", 1)[1] if f.suffix == ".vue" else text
        if f.suffix == ".ts" and not bodies_of(script):
            continue
        imported = set()
        for m in IMPORT_RE.finditer(script):
            for name in m.group(1).split(","):
                name = name.strip().split(" as ")[-1].strip()
                if name:
                    imported.add(name)
        units[str(f.relative_to(SRC))] = {
            "text": text,
            "script": script,
            "bodies": bodies_of(script),
            "imported": imported,
        }
    return units


def collect_api_map() -> "dict[str, dict]":
    """复用生成器：api 函数名 -> 该文件中定义的接口（可能多个同名导出）。"""
    fn2ep = defaultdict(set)
    for x in g.collect_call_sites():
        if x["func"]:
            fn2ep[x["func"]].add((x["method"], x["path"]))
    return fn2ep


def build_closure(units: "dict[str, dict]", fn2ep: "dict[str, dict]"):
    """构建 handler -> 最终触达的后端接口（含传递闭包 + 跨组件 + 组合式函数）。"""
    bodies_by_unit = {rel: d["bodies"] for rel, d in units.items()}

    # 1) 直接调用：handler 体内调用了 import 进来的 api 函数
    #    按「文件」打作用域：cancel / handleClose 这类通用名在不同组件里是
    #    不同函数，用全局闭包会把 A 组件的接口算到 B 组件头上（过度归属）。
    scoped = defaultdict(set)   # (file, handler) -> endpoints
    direct = defaultdict(set)   # handler -> endpoints（仅用于跨文件兜底）
    for rel, d in units.items():
        api_names = {n for n in d["imported"] if n in fn2ep}
        for handler, body in d["bodies"].items():
            for name in api_names:
                if re.search(r"\b" + re.escape(name) + r"\s*\(", body):
                    scoped[(rel, handler)] |= fn2ep[name]
                    direct[handler] |= fn2ep[name]

    # 2) 同文件内 handler 调 handler，做传递闭包（严格限定在本文件内）
    for _ in range(4):
        for rel, unit_bodies in bodies_by_unit.items():
            for handler, body in unit_bodies.items():
                for callee in re.findall(r"\b(\w+)\s*\(", body):
                    if callee in unit_bodies:
                        scoped[(rel, handler)] |= scoped[(rel, callee)]

    # 3) 全局视图 = 各文件作用域的并集。
    #    用于无法定位所属文件的场景（如跨组件 emit 桥），精度略低但不漏报。
    closure = defaultdict(set)
    for (_rel, handler), eps in scoped.items():
        closure[handler] |= eps

    # 4) 组合式函数桥：const { saveX } = useXxx() → useXxx 内部同名函数
    #    stepTree.vue 的 saveScenarioConfig 就藏在 useStepNodeEdit() 里，
    #    不搭这座桥会被误判成死按钮。
    for rel, d in units.items():
        for m in COMPOSABLE_RE.finditer(d["script"]):
            for raw in m.group(1).split(","):
                name = raw.strip().split(":")[-1].strip()
                if not name:
                    continue
                for other_rel, other in units.items():
                    if name in other["bodies"]:
                        for handler, body in d["bodies"].items():
                            if re.search(r"\b" + re.escape(name) + r"\b", body):
                                scoped[(rel, handler)] |= scoped[(other_rel, name)]
    for (_rel, handler), eps in scoped.items():
        closure[handler] |= eps

    # 5) 跨组件桥：父组件 <MsDialog @confirm="ok"> → 子组件 emit('confirm')
    #
    #    必须按「子组件名」限定，否则 handleConfirm 这种通用名会把全仓库
    #    所有 @confirm 的接口都吸过来（实测单个按钮能串到 87 个接口）。
    #    解析不出子组件名的，退化到全局兜底（宁可多报，不可漏报）。
    bridge = defaultdict(set)
    bridge_all = defaultdict(set)
    for _rel, d in units.items():
        for m in EVENT_BIND.finditer(d["text"]):
            event, expr = m.group(1).split(":")[0], m.group(2)
            seg = d["text"][:m.start()]
            cmps = re.findall(r"<([A-Z][\w]*|[a-z]+-[\w-]+)", seg)
            child = cmps[-1] if cmps else ""
            for hm in re.finditer(r"\b(\w+)\s*(?:\(|$)", expr):
                eps = closure.get(hm.group(1), set())
                if not eps:
                    continue
                bridge_all[event] |= eps
                if child:
                    bridge[(event, child)] |= eps
                    bridge[(event, child.lower())] |= eps
                    bridge[(event, kebab_to_pascal(child))] |= eps

    # 5b) props 回调桥：子组件 await props.remoteFunc(...) 由父组件传入。
    #
    #    deleteModal.vue 就是这样把删除请求交给外面 —— 不搭桥会漏判成
    #    「本地逻辑」。父组件写法形如 :remote-func="deleteHandler"。
    #    只认名字以 Func / Api / Request 结尾的属性，避免把普通 prop 误当回调。
    #
    #    必须按「子组件名 + 属性名」建索引。只按属性名建的话，
    #    remoteFunc 会把全仓库所有传参都并起来（实测串到 85 个接口）。
    #    模板写法：<DeleteModal :remote-func="deleteSingleBug" />
    prop_bridge = defaultdict(set)   # (子组件名, 属性名) -> endpoints
    # 模板里写 :remote-func="deleteSingleBug"，脚本里用 props.remoteFunc(...)，
    # 所以属性名要允许连字符，并归一成驼峰再比对。
    PROP_ATTR_RE = re.compile(
        r"(?:^|[\s:])([a-zA-Z][\w-]*)\s*=\s*\"([A-Za-z_]\w*)\""
    )
    PROP_CALL_RE = re.compile(r"props\.(\w+)\s*\(")

    for rel, d in units.items():
        for m in PROP_ATTR_RE.finditer(d["text"]):
            attr, val = m.group(1), m.group(2)
            attr = kebab_to_camel(attr)
            if not re.search(r"(?:Func|func|Api|api|Request|request)$", attr):
                continue
            seg = d["text"][:m.start()]
            cmps = re.findall(r"<([A-Z][\w]*|[a-z]+-[\w-]+)", seg)
            if not cmps:
                continue
            child = cmps[-1]
            # 传进来的可能是本地 handler，也可能是**直接 import 的 api 函数**
            # （:remote-func="deleteSingleBug" 就是后者），两种都要认。
            eps = scoped.get((rel, val), set()) or closure.get(val, set())
            if not eps and val in d["imported"] and val in fn2ep:
                eps = fn2ep[val]
            if not eps:
                continue
            # 统一小写比对：DeleteModal(模板) / deleteModal(目录) 视作同一组件
            prop_bridge[(child.lower(), attr)] |= eps

    def prop_targets(rel, attr):
        """子组件 rel 通过 props.<attr>() 能触达哪些接口。

        组件身份统一小写比对：ms-popconfirm/index.vue 在模板里是 <MsPopconfirm>，
        大小写与分隔符形态都不同，只有归一化后能对上。
        """
        out = set()
        for n in component_names(rel):
            out |= prop_bridge.get((n, attr), set())
        return out

    for rel, d in units.items():
        for handler, body in d["bodies"].items():
            for attr in PROP_CALL_RE.findall(body):
                scoped[(rel, handler)] |= prop_targets(rel, attr)

    def emit_targets(rel, event):
        """子组件 rel 抛出的 event 能触达哪些接口。

        组件身份候选要包含**目录名**：ms-popconfirm/index.vue 在模板里是
        <MsPopconfirm>，仅用文件名 index 对不上，会把全仓库 @confirm 的接口
        都吸过来。这里把路径各段（目录名 + 文件名）都作为候选。
        """
        keyed = set()
        for n in component_names(rel):
            keyed |= bridge.get((event, n), set())
        # 无组件限定时才退回全局：宁可多报，不可漏报
        return keyed or bridge_all.get(event, set())

    for rel, d in units.items():
        for handler, body in d["bodies"].items():
            for event in EMIT_CALL.findall(body):
                scoped[(rel, handler)] |= emit_targets(rel, event)

    # 桥接后再收敛一轮，让 emit 链路也能接力
    for _ in range(3):
        for rel, unit_bodies in bodies_by_unit.items():
            for handler, body in unit_bodies.items():
                for callee in re.findall(r"\b(\w+)\s*\(", body):
                    if callee in unit_bodies:
                        scoped[(rel, handler)] |= scoped[(rel, callee)]
                for event in EMIT_CALL.findall(body):
                    scoped[(rel, handler)] |= emit_targets(rel, event)
                for attr in PROP_CALL_RE.findall(body):
                    scoped[(rel, handler)] |= prop_targets(rel, attr)
    closure = defaultdict(set)
    for (_rel, handler), eps in scoped.items():
        closure[handler] |= eps

    return scoped, closure, bodies_by_unit


def handler_names(expr: str) -> list:
    """从 click 表达式里取出可能被调用的标识符。"""
    return [m.group(1) for m in re.finditer(r"\b(\w+)\s*(?:\(|$)", expr)]


# 纯前端态的判定：赋值、取反、路由跳转 —— 这些本来就不该发请求
ASSIGN_RE = re.compile(r"^\s*[\w.]+\s*=\s*[^=]|$|\b\w+\s*=\s*(?:!|true|false|'|\"|\d)")
NAV_RE = re.compile(r"\b(?:router\.push|router\.replace|router\.go|window\.open|location\.href)\b")


def classify(expr: str, resolve, all_handlers: set) -> str:
    """把按钮的点击表达式归到五类之一。

    判定顺序很重要：先认「能追到接口」，再认「跨组件抛事件」，
    最后才是纯前端态 / 本地逻辑 / 未定义。
    """
    names = handler_names(expr)
    for name in names:
        if resolve(name):
            return "wired"
    if EMIT_CALL.search(expr):
        return "cross"
    # 赋值 / 取反 / 路由跳转：不发请求，属正常前端行为
    if "=" in expr and not re.search(r"\w+\s*\(", expr):
        return "ui"
    if NAV_RE.search(expr):
        return "ui"
    if any(n in all_handlers for n in names):
        return "local"
    return "undefined"


def collect_buttons() -> list:
    """扫描全部 .vue，抽取每个交互式元素的触发表达式与标签文案。"""
    items = []
    for f in sorted(SRC.rglob("*.vue")):
        try:
            text = strip_noise(f.read_text(errors="ignore"))
        except OSError:
            continue
        if "<script" not in text:
            continue
        rel = str(f.relative_to(SRC))
        for m in BTN_RE.finditer(text):
            attrs = m.group(2)
            trig = TRIGGER_ATTR.search(attrs)
            if not trig:
                continue
            expr = trig.group(1).strip()
            if not expr:
                continue
            # 按钮文案：同一标签块内找 t('...') 或纯文本
            tail = text[m.end():m.end() + 200]
            label = ""
            lm = re.search(r"\{\{\s*t\(\s*'([^']+)'", tail)
            if lm:
                label = lm.group(1)
            else:
                tm = re.search(r">\s*([^<>{}\n]{1,24}?)\s*<", tail)
                if tm and not tm.group(1).startswith("{{"):
                    label = tm.group(1).strip()
            line = text[:m.start()].count("\n") + 1
            items.append({
                "file": rel, "line": line, "tag": m.group(1),
                "expr": expr, "label": label,
            })
    return items


def analyze():
    units = collect_units()
    fn2ep = collect_api_map()
    scoped, closure, bodies_by_unit = build_closure(units, fn2ep)
    all_handlers = set()
    for b in bodies_by_unit.values():
        all_handlers |= set(b)

    buttons = collect_buttons()
    bucket = defaultdict(list)
    for b in buttons:
        rel, expr = b["file"], b["expr"]
        eps = set()
        for name in handler_names(expr):
            # 优先本文件作用域，避免通用名跨文件串味
            local = scoped.get((rel, name), set())
            eps |= local if local else closure.get(name, set())
        b["endpoints"] = sorted(f"{m} {p}" for m, p in eps)
        # 默认参数绑定当前 rel，避免闭包延迟求值（B023）
        b["category"] = classify(
            expr,
            lambda n, _rel=rel: scoped.get((_rel, n), set()) or closure.get(n, set()),
            all_handlers,
        )
        bucket[b["category"]].append(b)
    return buttons, bucket, closure


def main():
    parser = argparse.ArgumentParser(description="按钮级覆盖矩阵生成器")
    parser.add_argument("--report", action="store_true", help="输出完整分类清单")
    parser.add_argument("--check", action="store_true", help="校验死按钮数量（CI 卡口）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--baseline", type=int, default=0,
                        help="允许的存量死按钮数（默认 0，即一个都不许有）")
    args = parser.parse_args()

    buttons, bucket, _closure = analyze()

    if args.json:
        print(json.dumps(buttons, ensure_ascii=False, indent=2))
        return 0

    print(f"扫描到交互式元素 {len(buttons)} 个（a-button / MsButton / 下拉项 / 更多操作）")
    print()
    for cat, desc in CATEGORIES.items():
        n = len(bucket.get(cat, []))
        print(f"  {desc:44s} {n:5d}")
    print()

    if args.report:
        for cat, desc in CATEGORIES.items():
            items = bucket.get(cat, [])
            if not items:
                continue
            print("─" * 78)
            print(f"{desc}  ({len(items)})")
            print("─" * 78)
            for b in items:
                ep = ("  → " + ", ".join(b["endpoints"][:3])) if b["endpoints"] else ""
                lbl = f"  [{b['label']}]" if b["label"] else ""
                print(f"  {b['file']}:{b['line']}{lbl}")
                print(f"      @click=\"{b['expr']}\"{ep}")
            print()

    if args.check:
        dead = bucket.get("undefined", [])
        if len(dead) > args.baseline:
            print(f"❌ 发现 {len(dead)} 个 handler 未定义的死按钮"
                  f"（基线允许 {args.baseline} 个）")
            for b in dead[:30]:
                print(f"   {b['file']}:{b['line']}  @click=\"{b['expr']}\"")
            return 1
        print(f"✅ 死按钮检查通过：{len(dead)} 个（基线 {args.baseline}）")
        return 0

    # 默认视图：给出结论与各模块死按钮明细
    dead = bucket.get("undefined", [])
    if dead:
        print("⚠️  handler 未定义（点了没反应）：")
        for b in dead[:30]:
            lbl = f"  [{b['label']}]" if b["label"] else ""
            print(f"   {b['file']}:{b['line']}{lbl}")
            print(f"      @click=\"{b['expr']}\"")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
