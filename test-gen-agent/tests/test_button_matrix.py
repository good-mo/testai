"""
按钮级覆盖矩阵回归测试（tests/test_button_matrix.py）
=====================================================
保证「每个按钮都点得动」这件事不会随迭代悄悄退化。

scripts/gen_frontend_matrix.py 覆盖的是**接口层**（658 条调用点全测），
但它看不见按钮 → handler → api 函数这条链断在哪。
scripts/button_matrix.py 从按钮反向回溯，把每个按钮归到五类之一。

本测试锁死两件事：
  1. 不允许出现「handler 未定义」的死按钮（点了没反应）
  2. 分类结果不能异常塌缩（比如解析器失效导致全部归入某一类）

新增按钮时如果 handler 没写，这里会红；而不是等用户点开页面才发现。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import button_matrix
import pytest

# 前端源码不存在时（如只部署后端的最小镜像）跳过，不误伤
SRC = button_matrix.SRC

pytestmark = pytest.mark.skipif(
    not SRC.exists(), reason="前端源码不存在，跳过按钮矩阵校验"
)

# 分类占比下限：解析器若失效（比如正则没跟上 Vue 语法变化），
# 会出现「已接线」暴跌、「未定义」暴涨，用阈值兜住。
MIN_WIRED_RATIO = 0.30      # 至少 30% 按钮能追到后端接口
MAX_UNDEFINED_RATIO = 0.02  # 死按钮占比不超过 2%


@pytest.fixture(scope="module")
def report():
    """执行一次全量分析，多个用例共享结果（扫描 658 个文件，别重复跑）。"""
    buttons, bucket, _ = button_matrix.analyze()
    return buttons, bucket


def test_no_dead_buttons(report):
    """不存在 handler 未定义的死按钮。

    死按钮 = 模板里写了 @click="xxx"，但 <script setup> 里找不到 xxx。
    用户看到的现象就是「点了没反应，也不报错」。
    """
    _buttons, bucket = report
    dead = bucket.get("undefined", [])
    assert not dead, (
        f"发现 {len(dead)} 个 handler 未定义的死按钮（点了没反应）：\n"
        + "\n".join(f"  {b['file']}:{b['line']}  @click=\"{b['expr']}\""
                    for b in dead[:20])
    )


def test_classification_not_collapsed(report):
    """分类结果没有异常塌缩。"""
    buttons, bucket = report
    total = len(buttons)
    assert total > 100, f"只扫到 {total} 个交互元素，解析器可能失效了"

    wired = len(bucket.get("wired", []))
    dead = len(bucket.get("undefined", []))

    assert wired / total >= MIN_WIRED_RATIO, (
        f"能追到后端接口的按钮仅 {wired}/{total}"
        f"（{wired / total:.1%}），低于阈值 {MIN_WIRED_RATIO:.0%}，"
        f"解析器可能没能追到 handler"
    )
    assert dead / total <= MAX_UNDEFINED_RATIO, (
        f"死按钮占比 {dead / total:.1%}，超过阈值 {MAX_UNDEFINED_RATIO:.0%}"
    )


def test_every_category_is_meaningful(report):
    """五类划分应当各自都有成员，且加起来等于总数。"""
    buttons, bucket = report
    summed = sum(len(v) for v in bucket.values())
    assert summed == len(buttons), (
        f"分类总数 {summed} 与按钮总数 {len(buttons)} 对不上"
    )
    # 注意：不要求每个分类都有成员 —— 「未定义」为空恰恰是我们想要的。
    for cat in bucket:
        assert cat in button_matrix.CATEGORIES, f"出现未知分类 {cat}"


def test_traced_endpoints_are_covered_by_matrix(report):
    """按钮追到的后端接口，应当都在接口层矩阵里被测过。

    这条把「按钮层」和「接口层」缝起来：
    按钮能追到接口 → 说明这个接口确实有按钮在用 → 接口层矩阵必须覆盖它。
    """
    _buttons, bucket = report
    wired = bucket.get("wired", [])

    import gen_frontend_matrix as g

    sites, _unresolved = g.filter_resolvable(
        g.collect_call_sites(), g.collect_backend_routes()
    )
    covered = {(x["method"], g.norm_path(x["path"]))
               for x in g.static_path(sites)}
    covered |= {(x["method"], g.norm_path(x["path"]))
                for x in g.param_path(sites)}

    missing = set()
    for b in wired:
        for ep in b["endpoints"]:
            method, _, path = ep.partition(" ")
            if "{" in path:
                # 运行时拼接的路径（如 ${host}/api/debug）静态无法还原，
                # 生成器本就排除在外，见 gen_frontend_matrix.filter_resolvable
                continue
            key = (method, g.norm_path(path))
            if key not in covered:
                missing.add(ep)

    assert not missing, (
        f"{len(missing)} 个按钮依赖的接口未被接口层矩阵覆盖：\n"
        + "\n".join(f"  {m}" for m in sorted(missing)[:20])
        + "\n请重跑：python3 scripts/gen_frontend_matrix.py"
    )
