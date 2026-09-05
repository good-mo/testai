#!/usr/bin/env python3
"""增量 lint：只检查本次变更涉及的 Python 文件。

背景：项目历史代码存在大量 lint 存量问题（未使用导入、裸 except 等），
一次性全量开启 lint 会直接淹没 PR、无法落地。因此这里采用增量策略：
只把「本次变更的文件」作为门禁，保证新代码合规，存量问题逐步治理。

用法:
    python3 scripts/lint_diff.py                # 对比 origin/main（CI 用）
    python3 scripts/lint_diff.py --base HEAD~1  # 指定基线
    python3 scripts/lint_diff.py --all          # 全量（仅体检用，不作为门禁）
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

# 允许作为门禁的最高告警数（新代码应为 0）
MAX_VIOLATIONS = 0


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def resolve_base(base: str) -> str:
    """确认基线 ref 可用，不可用时回落到默认分支。

    CI 里传入的可能是 origin/<目标分支>，浅克隆或跨仓场景下该 ref 未必存在，
    直接 diff 会报错导致门禁误判。
    """
    code, _ = _run(["git", "rev-parse", "--verify", "--quiet", base])
    if code == 0:
        return base
    for fallback in ("origin/main", "origin/master", "HEAD~1"):
        code, _ = _run(["git", "rev-parse", "--verify", "--quiet", fallback])
        if code == 0:
            print(f"⚠️  基线 {base} 不可用，回落到 {fallback}")
            return fallback
    return base


def changed_py_files(base: str) -> list[str]:
    """列出相对基线变更过的 .py 文件（含未提交改动）。

    仅返回当前工作区仍存在的文件——被删除的文件已无法 lint，
    若直接传给 ruff 会报 E902 No such file or directory。
    """
    files: list[str] = []
    # 已提交但相对 base 有差异的文件
    code, out = _run(["git", "diff", "--name-only", f"{base}...HEAD"])
    if code == 0:
        files += out.split()
    # 工作区未提交的改动（本地自检用）
    code, out = _run(["git", "diff", "--name-only"])
    if code == 0:
        files += out.split()
    # 未跟踪的新文件
    code, out = _run(["git", "ls-files", "--others", "--exclude-standard"])
    if code == 0:
        files += out.split()

    seen, result = set(), []
    for f in files:
        f = f.strip()
        if f.endswith(".py") and f not in seen:
            seen.add(f)
            # 已删除的文件跳过（不再存在，无法对其执行 ruff）
            if not os.path.exists(f):
                print(f"⚠️  跳过已删除的文件（不参与 lint）：{f}")
                continue
            result.append(f)
    return result




def new_compat_files(base: str) -> list[str]:
    """检测相对基线【新增】的 *_compat.py 文件（位于 app/routers/ 下）。

    兼容层（*_compat.py）已冻结：禁止新增，新功能只进正规路由层。
    允许修改存量 compat 文件（用于逐步收敛/迁移），但不得新增。
    """
    added: list[str] = []
    code, out = _run(["git", "diff", "--name-only", "--diff-filter=A", f"{base}...HEAD"])
    if code == 0:
        added += out.split()
    code, out = _run(["git", "ls-files", "--others", "--exclude-standard"])
    if code == 0:
        added += out.split()
    result = []
    for f in added:
        f = f.strip()
        if f.startswith("app/routers/") and f.endswith("_compat.py"):
            result.append(f)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="增量 lint 门禁")
    parser.add_argument(
        "--base", default="origin/main",
        help="对比基线，默认 origin/main；PR 流水线传 origin/$CNB_BRANCH",
    )
    parser.add_argument("--all", action="store_true", help="全量检查（体检用，忽略门禁阈值）")
    args = parser.parse_args()

    if args.all:
        targets = ["app", "scripts", "tests"]
    else:
        targets = changed_py_files(resolve_base(args.base))
        if not targets:
            print("✅ 本次变更未涉及 Python 文件，跳过 lint")
            return 0
        print(f"🔍 增量 lint：{len(targets)} 个变更文件")

    # 兼容层冻结门禁：禁止新增 *_compat.py（仅增量模式生效）
    if not args.all:
        compat_added = new_compat_files(resolve_base(args.base))
        if compat_added:
            print("❌ 兼容层已冻结，禁止新增 *_compat.py：")
            for f in compat_added:
                print(f"   - {f}")
            print("   新功能请写入正规路由层（app/routers/ 下非 *_compat.py 文件）。")
            return 1

    code, out = _run(["python3", "-m", "ruff", "check", "--no-fix", *targets])
    print(out)

    # 提取告警总数
    total = 0
    for line in out.splitlines():
        if line.startswith("Found ") and " error" in line:
            try:
                total = int(line.split()[1])
            except (IndexError, ValueError):
                pass

    if code == 0 or total == 0:
        print("✅ lint 通过")
        return 0

    if args.all:
        print(f"ℹ️  全量体检发现 {total} 处存量问题（非门禁，仅作治理参考）")
        return 0

    print(f"❌ lint 未通过：变更文件存在 {total} 处问题（门禁上限 {MAX_VIOLATIONS}）")
    print("   请修复后再提交；存量文件的历史问题不计入门禁。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
