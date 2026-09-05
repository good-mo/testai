"""架构守护（architecture_guard）：纯 AST 静态分析，毫秒级，可 CI 常开。

定位
----
把《docs/ddd-architecture-refactoring-plan.md》里的「依赖铁律」变成可在 CI 里
低成本、低噪音执行的机器检查，防止 DDD 骨架后续继续腐化。

设计原则（不阻断存量、只卡增量）
--------------------------------
- 存量（历史遗留）违规：登记进 :data:`BASELINE`（以 ``rule -> 文件路径集`` 标识），
  守护报告为 ``warnings``（告警），并断言这些规则命中的文件数不增长 —— 存量
  继续腐化会被拦，但存量本身先不动（避免一次性大规模重构、风险外溢）。
- 增量（新增）违规：不在 :data:`BASELINE` 登记文件内的新违规一律 ``blocking``
  （阻断），让合并请求无法带病合入。
- 纯 AST：不改代码、不 import 业务模块、不做任何副作用，扫描 app/domain 整个
  目录树毫秒级完成，适合流水线每次跑都开。

守护规则（RULE）
----------------
1. ``LAYER_DOMAIN_IMPORT``      内层 domain 层禁止 import 框架/上层架构模块
   （fastapi/flask/sqlite3/aiosqlite/pydantic/starlette/uvicorn，以及
   ``app.routers / app.services / app.repositories / app.models / app.main``）。
   领域层只能依赖领域自身，具体实现交给 infrastructure —— 防腐。
2. ``INFRA_REVERSE_SERVICE``    bounded context 的 infrastructure 适配器不得反向
   import 既有四层 ``app.services.*``（domain→services→domain 循环依赖风险源）。
   适配器应面向自身聚合仓储 Port + 既有 ``app.repositories``，而非业务 Service。
3. ``AGGREGATE_TIME_MAGIC``     聚合根实体（``domain/entities/*.py``）的
   ``to_dict``/``from_dict`` 不得裸写 ``* 1000`` 做 秒→毫秒 时间换算 —— 历史
   上这就是「时间单位 round-trip 漂移 / 数据被放大 1000 倍」的根因。

用法
----
.. code-block:: python

    from app.domain.common.architecture_guard import run_guard

    report = run_guard()          # 默认扫描 app/domain
    assert not report.blocking    # 新违规阻断（CI 里直接断言）
    # report.warnings            # 存量告警（登记在 BASELINE，断言文件数不增长）

命令行（可接入 CI，常开）::

    python -m app.domain.common.architecture_guard

退出码：有 ``blocking`` 违规返回 1（阻断），否则返回 0。
"""
from __future__ import annotations

import argparse
import ast
import os
import sys
from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, Tuple

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
# 领域内层禁止 import 的框架（防腐：领域层对框架零依赖）
_FORBIDDEN_FRAMEWORKS = {
    "fastapi", "flask", "sqlite3", "aiosqlite",
    "pydantic", "starlette", "uvicorn",
}

# 领域内层禁止 import 的四层上层架构模块（方向必须向外层依赖、不得反向）
_FORBIDDEN_ARCH_MODULES = {"routers", "repositories", "services", "models", "main"}

# 聚合根时间换算魔数（秒→毫秒）。历史上 to_dict 导出毫秒、from_dict 却当秒回灌，
# 导致「读→改→存」后创建时间被放大 1000 倍。此处守卫它不允许裸写。
_TIME_MAGIC_LITERAL = 1000

# app/domain/common/architecture_guard.py 的上一级目录即 app/domain
_DOMAIN_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)

# 各规则的相对路径在 DDD 目录中的定位段，用于判断某文件属于哪一层
_SEG_DOMAIN = "domain"
_SEG_INFRA = "infrastructure"
_SEG_ENTITIES = "entities"


# ---------------------------------------------------------------------------
# 存量基线登记表
# ---------------------------------------------------------------------------
# 每条 = ``rule -> 允许命中该规则的文件相对路径集``（相对 app/domain，正向斜杠）。
# 已登记文件内的违规只作为告警（warnings），并断言文件数不增长；不在登记文件
# 内的新违规一律阻断 —— 清理存量不影响 CI 通过，新增却会被拦下。
BASELINE: "dict[str, set[str]]" = {
    # 现状 0：领域内层干净，新增任意一处直接阻断
    "LAYER_DOMAIN_IMPORT": set(),
    # 现状 0：4 个空壳域 infra 反向依赖 app.services 已全部清理（存量归零），
    # 现无可登记文件；新增任意一处 infrastructure → app.services 反向依赖直接阻断。
    "INFRA_REVERSE_SERVICE": set(),
    # 历史遗留：5 个聚合根实体 to_dict 裸写 * 1000（待迁移到 time_utils）
    "AGGREGATE_TIME_MAGIC": {
        "template/domain/entities/template.py",
        "ai_model/domain/entities/ai_model.py",
        "debug/domain/entities/debug_item.py",
        "project_version/domain/entities/project_version.py",
        "resource_pool/domain/entities/resource_pool.py",
    },
}


# ---------------------------------------------------------------------------
# 模型
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Finding:
    """一条守护发现。

    - ``rel_path``：相对 ``app/domain`` 的路径（正向斜杠）。
    - ``rule``    ：命中的规则编码。
    - ``line``    ：源码行号（AST 行，1 起）。无行概念时为 0。
    - ``detail``  ：人类可读的定位串/摘要。
    """

    rel_path: str
    rule: str
    line: int
    detail: str

    @property
    def blocking(self) -> bool:
        """文件未登记进存量基线 => 新违规，阻断；已登记 => 仅告警。"""
        return self.rel_path not in BASELINE.get(self.rule, set())


@dataclass
class GuardReport:
    """一次守护扫描的结果汇总。"""

    findings: List[Finding] = field(default_factory=list)

    @property
    def blocking(self) -> List[Finding]:
        """新增违规（阻断合并）。"""
        return [f for f in self.findings if f.blocking]

    @property
    def warnings(self) -> List[Finding]:
        """存量告警（历史遗留，断言文件数不增长）。"""
        return [f for f in self.findings if not f.blocking]

    def affected_files(self, rule: str) -> set:
        """某规则当前命中的文件集合（供存量断言）。"""
        return {f.rel_path for f in self.findings if f.rule == rule}

    def summary(self) -> str:
        lines = [
            f"[architecture_guard] 扫描完成：共 {len(self.findings)} 处发现，"
            f"其中 阻断 {len(self.blocking)} 处 / 告警 {len(self.warnings)} 处",
        ]
        for f in self.blocking:
            lines.append(f"  ✗ [阻断] {f.rule} {f.rel_path}:{f.line}  {f.detail}")
        for f in self.warnings:
            lines.append(f"  ! [告警] {f.rule} {f.rel_path}:{f.line}  {f.detail}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 内部：AST 提取 import
# ---------------------------------------------------------------------------
def _module_imports(tree: ast.AST) -> Iterable[str]:
    """逐个 yield 模块被 import 的完整模块名（相对 import 带前导点）。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:  # 跳过 ``from . import x``（相对根导入，无需筛查）
                yield node.module


def _first_segment(module: str) -> str:
    """取模块名首个顶层段（保留相对导入的前导点）。"""
    module = module.strip()
    if not module:
        return ""
    leading = ""
    i = 0
    while i < len(module) and module[i] == ".":
        leading += "."
        i += 1
    rest = module[i:]
    return leading + (rest.split(".")[0] if rest else "")


def _is_app_top_import(module: str) -> bool:
    """是否为对应用内顶层包 ``app.<seg>`` 的 import。"""
    return module.startswith("app.") or module == "app"


# ---------------------------------------------------------------------------
# 内部：规则实现（纯遍历，不改代码）
# ---------------------------------------------------------------------------
def _scan_domain_layer(root: str, findings: List[Finding]) -> None:
    """规则 LAYER_DOMAIN_IMPORT：内层 domain 不得 import 框架/上层架构模块。"""
    for rel, file_tree in _walk_py(root):
        seg = rel.split("/")
        # 仅限 bounded-context 的内层 domain：<ctx>/domain/**
        if len(seg) >= 3 and seg[1] == _SEG_DOMAIN:
            for mod in _module_imports(file_tree):
                first = _first_segment(mod)
                if first in _FORBIDDEN_FRAMEWORKS:
                    findings.append(
                        Finding(rel, "LAYER_DOMAIN_IMPORT", 0,
                                f"领域层 import 框架模块 {mod}")
                    )
                if _is_app_top_import(mod) and mod.split(".")[1] in _FORBIDDEN_ARCH_MODULES:
                    findings.append(
                        Finding(rel, "LAYER_DOMAIN_IMPORT", 0,
                                f"领域层反向依赖上层架构模块 {mod}")
                    )


def _scan_infra_service(root: str, findings: List[Finding]) -> None:
    """规则 INFRA_REVERSE_SERVICE：context 的 infrastructure 不得反向 import
    既有四层 ``app.services.*``。"""
    for rel, file_tree in _walk_py(root):
        seg = rel.split("/")
        if len(seg) >= 3 and seg[1] == _SEG_INFRA:
            for mod in _module_imports(file_tree):
                if mod.startswith("app.services"):
                    findings.append(
                        Finding(rel, "INFRA_REVERSE_SERVICE", 0,
                                f"infrastructure 反向依赖四层服务 {mod}")
                    )


def _scan_time_magic(root: str, findings: List[Finding]) -> None:
    """规则 AGGREGATE_TIME_MAGIC：聚合根实体裸写 ``* 1000`` 做秒→毫秒换算。"""
    for rel, file_tree in _walk_py(root):
        seg = rel.split("/")
        if (len(seg) >= 3 and seg[1] == _SEG_DOMAIN
                and _SEG_ENTITIES in seg):
            for node in ast.walk(file_tree):
                if (isinstance(node, ast.BinOp)
                        and isinstance(node.op, ast.Mult)
                        and isinstance(node.right, ast.Constant)
                        and node.right.value == _TIME_MAGIC_LITERAL):
                    findings.append(
                        Finding(rel, "AGGREGATE_TIME_MAGIC", node.lineno, "* 1000")
                    )


_RULES = (
    _scan_domain_layer,
    _scan_infra_service,
    _scan_time_magic,
)


# ---------------------------------------------------------------------------
# 内部：目录遍历
# ---------------------------------------------------------------------------
def _walk_py(root: str) -> Iterable[Tuple[str, ast.AST]]:
    """遍历目录下所有 ``.py``，产出 (相对路径, 语法树)。解析失败跳过。"""
    for dirpath, _dirs, files in os.walk(root):
        if "__pycache__" in dirpath:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            try:
                with open(full, "r", encoding="utf-8") as fh:
                    tree = ast.parse(fh.read(), filename=full)
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue
            yield rel, tree


# ---------------------------------------------------------------------------
# 对外入口
# ---------------------------------------------------------------------------
def run_guard(root: str = _DOMAIN_ROOT) -> GuardReport:
    """执行一次完整架构守护扫描。

    参数
    ----
    root : 扫描的 DDD 领域根目录，缺省为仓库 ``app/domain``。

    返回
    ----
    GuardReport：见字段注释。``report.blocking`` 非空即应阻断 CI。
    """
    findings: List[Finding] = []
    for rule in _RULES:
        rule(root, findings)
    findings.sort(key=lambda f: (f.rule, f.rel_path, f.line))
    return GuardReport(findings)


def _check_baseline_growth(report: GuardReport) -> bool:
    """断言各规则命中的文件数不超出基线（存量不增长）。返回是否有存量增长。"""
    grown = False
    for rule, baseline_files in BASELINE.items():
        current_files = report.affected_files(rule)
        extra = current_files - baseline_files  # 新增位置（阻断）
        reduced = baseline_files - current_files  # 存量被清理（好事）
        if extra:
            grown = True
            print(f"  [存量增长] 规则 {rule} 新增文件 {len(extra)} 个：{sorted(extra)}")
        if reduced:
            print(f"  [存量清理] 规则 {rule} 减少文件 {len(reduced)} 个，继续加油。")
    return grown


# ---------------------------------------------------------------------------
# 命令行入口（便于 CI 常开）
# ---------------------------------------------------------------------------
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="architecture_guard",
        description="纯 AST 静态 DDD 架构守护（不阻断存量、只卡增量）。",
    )
    parser.add_argument(
        "--root",
        default=_DOMAIN_ROOT,
        help="扫描的 DDD 领域根目录（默认仓库 app/domain）。",
    )
    args = parser.parse_args(argv)

    report = run_guard(root=args.root)
    print(report.summary())

    grown = _check_baseline_growth(report)

    if report.blocking:
        print("[architecture_guard] 存在新增违规，CI 阻断（exit 1）。")
        return 1
    if grown:
        print("[architecture_guard] 存量文件数增长，CI 阻断（exit 1）。")
        return 1
    print("[architecture_guard] 通过：无新增违规、存量未增长。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
