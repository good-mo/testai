#!/usr/bin/env python3
"""读取 coverage.lcov 并输出覆盖率报告。

CNB testing:coverage 内置任务无法解析 coverage.py 生成的 lcov/json/xml 格式，
此脚本从 lcov 文件中直接解析覆盖率数据，输出覆盖率报告并在低于阈值时阻断 CI。

支持两类指标：
  - 行覆盖率（LF / LH）
  - 分支覆盖率（BRF / BRH，需给 pytest 加 --cov-branch）

用法：
    python3 scripts/report_coverage.py coverage.lcov [行阈值] [分支阈值]

示例：
    python3 scripts/report_coverage.py coverage.lcov 40            # 只卡行覆盖率
    python3 scripts/report_coverage.py coverage.lcov 40 20         # 同时卡分支覆盖率
"""
import os
import sys


def parse_lcov(path: str) -> dict:
    """解析 lcov 文件，返回行/分支覆盖率统计信息。

    lcov 单条记录格式（以 end_of_record 结束）：
        SF:<文件路径>
        DA:<行号>,<执行次数>
        LF:<可执行行数>
        LH:<已覆盖行数>
        BRDA:<行号>,<块号>,<分支号>,<执行次数或 '-'>
        BRF:<分支总数>
        BRH:<已覆盖分支数>
        end_of_record
    """
    if not os.path.exists(path):
        print(f"[ERROR] 覆盖率文件不存在: {path}", file=sys.stderr)
        sys.exit(1)

    total_lf = 0
    total_lh = 0
    total_brf = 0
    total_brh = 0
    file_count = 0

    with open(path, "r", encoding="utf-8") as f:
        cur_lf = None
        cur_lh = None
        cur_brf = None
        cur_brh = None
        is_record = False

        for line in f:
            line = line.strip()
            if line.startswith("SF:"):
                file_count += 1
                is_record = True
            elif line.startswith("LF:"):
                cur_lf = int(line[3:])
            elif line.startswith("LH:"):
                cur_lh = int(line[3:])
            elif line.startswith("BRF:"):
                cur_brf = int(line[4:])
            elif line.startswith("BRH:"):
                cur_brh = int(line[4:])
            elif line == "end_of_record" and is_record:
                if cur_lf is not None:
                    total_lf += cur_lf
                    total_lh += cur_lh or 0
                # 未加 --cov-branch 时没有 BRF/BRH，按"未采集"处理，不参与判定
                if cur_brf is not None:
                    total_brf += cur_brf
                    total_brh += cur_brh or 0
                cur_lf = cur_lh = cur_brf = cur_brh = None
                is_record = False

    return {
        "total_lf": total_lf,
        "total_lh": total_lh,
        "total_brf": total_brf,
        "total_brh": total_brh,
        "file_count": file_count,
    }


def _pct(hit: int, total: int):
    """计算百分比，无有效数据时返回 None（区别于 0%）。"""
    if total <= 0:
        return None
    return (hit / total) * 100


def main():
    lcov_path = sys.argv[1] if len(sys.argv) > 1 else "coverage.lcov"
    line_threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 45.0
    branch_threshold = float(sys.argv[3]) if len(sys.argv) > 3 else None

    stats = parse_lcov(lcov_path)
    total_lf = stats["total_lf"]
    total_lh = stats["total_lh"]
    total_brf = stats["total_brf"]
    total_brh = stats["total_brh"]

    line_pct = _pct(total_lh, total_lf)
    branch_pct = _pct(total_brh, total_brf)

    print("=" * 60)
    print("覆盖率报告")
    print("=" * 60)
    if line_pct is None:
        print("代码行覆盖率: N/A (0 行)")
    else:
        print(f"代码行覆盖率: {line_pct:.2f}% ({total_lh}/{total_lf})")

    if branch_pct is None:
        print("分支覆盖率: N/A (未采集，pytest 需加 --cov-branch)")
    else:
        print(f"分支覆盖率: {branch_pct:.2f}% ({total_brh}/{total_brf})")

    print(f"参与统计文件数: {stats['file_count']}")
    print("=" * 60)

    if total_lf == 0:
        print("[WARN] 未获取到有效覆盖率数据，跳过检查")
        return 0

    failed = False
    if line_pct < line_threshold:
        print(f"[ERROR] 行覆盖率 {line_pct:.2f}% 低于红线 {line_threshold}%")
        failed = True
    else:
        print(f"[OK] 行覆盖率 {line_pct:.2f}% 满足红线 {line_threshold}%")

    if branch_threshold is not None:
        if branch_pct is None:
            print("[WARN] 未采集分支覆盖率数据，跳过分支红线检查")
        elif branch_pct < branch_threshold:
            print(f"[ERROR] 分支覆盖率 {branch_pct:.2f}% 低于红线 {branch_threshold}%")
            failed = True
        else:
            print(f"[OK] 分支覆盖率 {branch_pct:.2f}% 满足红线 {branch_threshold}%")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
