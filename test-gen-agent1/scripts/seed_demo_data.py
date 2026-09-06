#!/usr/bin/env python3
"""
演示数据种子脚本
=================
为用例库与测试计划模块插入一批初始化的演示数据，
用于 CI 端到端测试的「数据保留」校验（TestDataPreserved）。

功能：
  - 幂等执行：按标题去重，已存在的记录自动跳过（不重复插入）
  - 用例数据覆盖多种状态 / 优先级 / 测试类型
  - 测试计划覆盖不同优先级与描述
  - 接口定义覆盖 GET/POST/PUT/DELETE 等方法
  - 支持 --reset 参数：先清空现有数据再重新插入
  - 支持 --dry-run 参数：仅预览将要插入的数据

用法：
    python3 scripts/seed_demo_data.py            # 插入种子数据（幂等）
    python3 scripts/seed_demo_data.py --reset    # 清空后重新插入
    python3 scripts/seed_demo_data.py --dry-run  # 预览将要插入的数据
"""
import argparse
import os
import sys

# 将项目根目录加入 sys.path，确保可导入 app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.apitest.store import count_definitions, create_definition, list_definitions
from app.repositories.case_repo import (
    PRIORITY_P0,
    PRIORITY_P1,
    PRIORITY_P2,
    PRIORITY_P3,
    STATUS_APPROVED,
    STATUS_DRAFT,
    STATUS_REVIEW,
    CaseRepo,
)
from app.services.test_plan_service import test_plan_service

# 数据访问统一收敛到 4 层 repo（与 routers 保持一致）
create_case = CaseRepo.create
list_cases = CaseRepo.list_cases


def _get_default_project_id() -> str:
    """获取默认项目 ID（用于种子数据关联）。"""
    try:
        from app.repositories.project_repo import ProjectRepo
        projects = ProjectRepo.list(limit=1)
        if projects:
            return projects[0]["id"]
    except Exception:
        pass
    return ""


# ── 种子用例数据 ──────────────────────────────────────────────
# 与 TestDataPreserved.test_cases_data_preserved 阈值(>=100)对齐
SEED_CASE_COUNT = 120

# ── 种子测试计划数据 ──────────────────────────────────────────
# 与 TestDataPreserved.test_test_plans_data_preserved 阈值(>=40)对齐
SEED_PLAN_COUNT = 50

CASE_TITLES = [
    "登录功能验证",
    "用户信息修改",
    "密码重置流程",
    "权限控制检查",
    "角色分配验证",
    "数据导出功能",
    "数据导入功能",
    "文件上传验证",
    "文件下载验证",
    "搜索筛选功能",
    "分页展示验证",
    "排序功能检查",
    "批量操作验证",
    "异常输入处理",
    "并发访问测试",
    "缓存机制验证",
    "定时任务检查",
    "消息通知验证",
    "日志记录检查",
    "审计追踪验证",
]

CASE_PRIORITIES = [PRIORITY_P0, PRIORITY_P1, PRIORITY_P2, PRIORITY_P3]
CASE_STATUSES = [STATUS_DRAFT, STATUS_REVIEW, STATUS_APPROVED]

# ── 种子接口定义数据 ──────────────────────────────────────────
# 与 TestDataPreserved.test_api_definitions_data_preserved 阈值(>=5)对齐
SEED_DEFINITION_COUNT = 8

DEFINITION_SEEDS = [
    ("获取用户列表", "GET", "/api/users"),
    ("创建用户", "POST", "/api/users"),
    ("更新用户信息", "PUT", "/api/users/{id}"),
    ("删除用户", "DELETE", "/api/users/{id}"),
    ("查询项目详情", "GET", "/api/projects/{id}"),
    ("创建项目", "POST", "/api/projects"),
    ("执行测试计划", "POST", "/api/plans/{id}/execute"),
    ("查询测试报告", "GET", "/api/reports/{id}"),
]

PLAN_NAMES = [
    "核心功能回归计划",
    "接口稳定性验证计划",
    "性能压测计划",
    "安全专项测试计划",
    "兼容性测试计划",
    "冒烟测试计划",
    "全量回归计划",
    "上线前验收计划",
    "客户端适配计划",
    "数据一致性计划",
]


def _case_exists(title: str) -> bool:
    """判断是否已存在相同标题的用例（用于幂等）。"""
    for c in list_cases(limit=500):
        if c.get("title") == title:
            return True
    return False


def seed_cases(count: int = SEED_CASE_COUNT, reset: bool = False, dry_run: bool = False) -> dict:
    """插入种子用例数据。"""
    stats = {"inserted": 0, "skipped": 0, "total": count}

    if reset and not dry_run:
        from app.core.database import Database
        conn = Database.get_conn("testcases.db")
        conn.execute("DELETE FROM test_cases")
        conn.commit()
        print("已清空现有用例数据。")
    elif reset and dry_run:
        print("[DRY-RUN] 将清空现有用例数据。")

    for i in range(count):
        title = f"[Demo]{CASE_TITLES[i % len(CASE_TITLES)]} #{i + 1:03d}"

        if dry_run:
            print(f"[DRY-RUN] 待插入: {title}")
            stats["inserted"] += 1
            continue

        if _case_exists(title):
            stats["skipped"] += 1
            continue

        try:
            create_case({
                "title": title,
                "description": f"演示种子用例 {i + 1}：覆盖 {CASE_TITLES[i % len(CASE_TITLES)]} 场景",
                "priority": CASE_PRIORITIES[i % len(CASE_PRIORITIES)],
                "status": CASE_STATUSES[i % len(CASE_STATUSES)],
                "test_type": "functional",
            })
            stats["inserted"] += 1
        except Exception as e:
            print(f"[ERROR] 插入用例失败: {title} → {e}")

    return stats


def _plan_exists(name: str) -> bool:
    """判断是否已存在相同名称的测试计划（用于幂等）。"""
    for p in test_plan_service.list_plans(limit=1000):
        if p.get("name") == name:
            return True
    return False


def seed_plans(count: int = SEED_PLAN_COUNT, reset: bool = False, dry_run: bool = False) -> dict:
    """插入种子测试计划数据。"""
    stats = {"inserted": 0, "skipped": 0, "total": count}

    if reset and not dry_run:
        from app.core.database import Database
        conn = Database.get_conn("test_plans.db")
        conn.execute("DELETE FROM test_plans")
        conn.commit()
        print("已清空现有测试计划数据。")
    elif reset and dry_run:
        print("[DRY-RUN] 将清空现有测试计划数据。")

    for i in range(count):
        name = f"[Demo]{PLAN_NAMES[i % len(PLAN_NAMES)]} #{i + 1:03d}"

        if dry_run:
            print(f"[DRY-RUN] 待插入: {name}")
            stats["inserted"] += 1
            continue

        if _plan_exists(name):
            stats["skipped"] += 1
            continue

        try:
            test_plan_service.create_plan(
                name=name,
                description=f"演示种子测试计划 {i + 1}",
                priority=CASE_PRIORITIES[i % len(CASE_PRIORITIES)],
                project_id=_get_default_project_id(),
            )
            stats["inserted"] += 1
        except Exception as e:
            print(f"[ERROR] 插入测试计划失败: {name} → {e}")

    return stats


def _definition_exists(name: str) -> bool:
    """判断是否已存在相同名称的接口定义（用于幂等）。"""
    for d in list_definitions(limit=1000):
        if d.get("name") == name:
            return True
    return False


def seed_definitions(count: int = SEED_DEFINITION_COUNT,
                     reset: bool = False, dry_run: bool = False) -> dict:
    """插入种子接口定义数据。"""
    stats = {"inserted": 0, "skipped": 0, "total": count}

    if reset and not dry_run:
        from app.core.database import Database
        conn = Database.get_conn("apitest.db")
        conn.execute("DELETE FROM api_definitions")
        conn.commit()
        print("已清空现有接口定义数据。")
    elif reset and dry_run:
        print("[DRY-RUN] 将清空现有接口定义数据。")

    for i in range(count):
        name, method, path = DEFINITION_SEEDS[i % len(DEFINITION_SEEDS)]
        name = f"[Demo]{name} #{i + 1:03d}"

        if dry_run:
            print(f"[DRY-RUN] 待插入: {name}")
            stats["inserted"] += 1
            continue

        if _definition_exists(name):
            stats["skipped"] += 1
            continue

        try:
            create_definition(
                name=name,
                method=method,
                path=path,
                protocol="HTTP",
                description=f"演示种子接口定义 {i + 1}",
                project_id=_get_default_project_id(),
            )
            stats["inserted"] += 1
        except Exception as e:
            print(f"[ERROR] 插入接口定义失败: {name} → {e}")

    return stats


def print_summary(section: str, stats: dict) -> None:
    """打印执行摘要。"""
    print(f"\n[{section}] 种子数据执行完成：共 {stats['total']} 条")
    print(f"  新插入: {stats['inserted']} 条")
    print(f"  已跳过: {stats['skipped']} 条")


def main():
    parser = argparse.ArgumentParser(
        description="初始化演示种子数据脚本（用例 + 测试计划）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="先清空现有数据再重新插入（慎用！）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅预览将要插入的数据，不实际写入数据库",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY-RUN] 模式：仅预览不写入\n")

    print("开始初始化演示种子数据...")
    case_stats = seed_cases(reset=args.reset, dry_run=args.dry_run)
    print_summary("用例", case_stats)

    plan_stats = seed_plans(reset=args.reset, dry_run=args.dry_run)
    print_summary("测试计划", plan_stats)

    def_stats = seed_definitions(reset=args.reset, dry_run=args.dry_run)
    print_summary("接口定义", def_stats)

    if not args.dry_run:
        cases = list_cases(limit=1000)
        plans = test_plan_service.list_plans(limit=1000)
        defs = count_definitions()
        print(f"\n当前数据量：用例 {len(cases)} 条，测试计划 {len(plans)} 条，接口定义 {defs} 条")


if __name__ == "__main__":
    main()
