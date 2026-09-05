#!/usr/bin/env python3
"""
缺陷数据种子脚本
=================
为缺陷管理模块插入一批初始化的示例缺陷数据，便于前端页面展示与联调。

功能：
  - 幂等执行：已存在相同 title 的缺陷会自动跳过（不重复插入）
  - 覆盖多种状态（待处理/处理中/已修复/已关闭/不修复）
  - 覆盖多种严重程度（blocker/critical/major/minor）
  - 关联测试用例、文件路径、错误摘要等字段
  - 支持 --reset 参数：先清空现有缺陷再重新插入

用法：
    python3 scripts/seed_defects.py            # 插入种子数据（幂等）
    python3 scripts/seed_defects.py --reset    # 清空后重新插入
    python3 scripts/seed_defects.py --dry-run  # 预览将要插入的数据
"""
import argparse
import os
import sys

# 将项目根目录加入 sys.path，确保可导入 app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.repositories.defect_repo import (
    SEVERITY_BLOCKER,
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    STATUS_CLOSED,
    STATUS_FIXED,
    STATUS_IN_PROGRESS,
    STATUS_OPEN,
    STATUS_WONT_FIX,
    DefectRepo,
)

# ── 种子数据定义 ────────────────────────────────────────────────
# 每个缺陷对象包含 create_defect 支持的字段
SEED_DEFECTS = [
    # ── 严重级缺陷 ──────────────────────────────────────────────
    {
        "title": "登录接口未返回 token，前端无法跳转工作台",
        "description": "调用 POST /api/auth/login 后返回 200，但响应体缺少 token 字段，导致前端登录成功后无法进入工作台。\n\n复现步骤：\n1. 输入正确的用户名密码\n2. 点击登录\n3. 控制台报错 `Cannot read properties of undefined (reading 'token')`",
        "severity": SEVERITY_BLOCKER,
        "status": STATUS_OPEN,
        "file_path": "app/auth/router.py",
        "test_case_id": "auth-login-001",
        "error_snippet": "TypeError: Cannot read properties of undefined (reading 'token')",
        "assignee": "admin",
    },
    {
        "title": "批量执行接口用例时偶发超时，任务卡死无回调",
        "description": "并发执行 50 条接口用例时，约 5% 的请求超时且任务一直显示\"执行中\"，无超时重试机制。\n\n影响：用户无法取消任务，资源被长时间占用。",
        "severity": SEVERITY_BLOCKER,
        "status": STATUS_IN_PROGRESS,
        "file_path": "app/api_testing/services/cases.py",
        "test_case_id": "api-batch-run-023",
        "error_snippet": "TimeoutError: Operation timed out after 30s",
        "assignee": "zhangsan",
    },
    {
        "title": "数据库连接池泄漏导致服务 5 分钟后不可用",
        "description": "高频调用 /bug/page 接口后，SQLite 连接数持续增长，最终达到上限后所有请求均返回 500。\n\n排查发现 `Database.get_conn` 在部分异常路径未释放连接。",
        "severity": SEVERITY_BLOCKER,
        "status": STATUS_FIXED,
        "file_path": "app/core/database.py",
        "test_case_id": "conn-pool-stress-007",
        "error_snippet": "sqlite3.OperationalError: database is locked",
        "assignee": "lisi",
    },

    # ── 严重缺陷 ────────────────────────────────────────────────
    {
        "title": "项目环境配置保存失败，返回 500 错误",
        "description": "在项目管理中新增环境配置并点击保存，接口 POST /project/environment/save 返回 500。\n\n后端日志显示 `KeyError: 'project_id'`。",
        "severity": SEVERITY_CRITICAL,
        "status": STATUS_OPEN,
        "file_path": "app/adapters/domains/project.py",
        "test_case_id": "proj-env-save-012",
        "error_snippet": "KeyError: 'project_id'",
        "assignee": "zhangsan",
    },
    {
        "title": "测试报告导出为 PDF 时中文乱码",
        "description": "导出测试报告 PDF 时，所有中文字符显示为乱码（`����`），仅英文字符正常。\n\n根因可能是 PDF 生成库未加载中文字体。",
        "severity": SEVERITY_CRITICAL,
        "status": STATUS_IN_PROGRESS,
        "file_path": "app/reports/generator.py",
        "test_case_id": "report-export-pdf-034",
        "error_snippet": "",
        "assignee": "wangwu",
    },
    {
        "title": "缺陷列表页搜索关键词无效，接口忽略 keyword 参数",
        "description": "在缺陷列表页输入关键词搜索，请求 POST /bug/page 正确携带了 keyword 参数，但后端 list_defects 方法未实现 keyword 过滤，返回全部数据。",
        "severity": SEVERITY_CRITICAL,
        "status": STATUS_CLOSED,
        "file_path": "app/defects/tracker.py",
        "test_case_id": "bug-search-056",
        "error_snippet": "",
        "assignee": "admin",
    },

    # ── 主要缺陷 ────────────────────────────────────────────────
    {
        "title": "接口测试中 Mock 服务开启后无法关闭",
        "description": "在接口定义中开启 Mock 后，点击关闭按钮无效，Mock 服务仍然响应。\n\n需要手动重启服务才能关闭 Mock。",
        "severity": SEVERITY_MAJOR,
        "status": STATUS_OPEN,
        "file_path": "app/apitest/service.py",
        "test_case_id": "mock-toggle-089",
        "error_snippet": "",
        "assignee": "lisi",
    },
    {
        "title": "定时任务设置 cron 表达式后未按预期时间执行",
        "description": "在任务中心设置 cron 表达式 `0 0 2 * * ?`（每天凌晨2点），但任务从未触发。\n\n检查发现时区配置不正确，数据库存的是 UTC 时间。",
        "severity": SEVERITY_MAJOR,
        "status": STATUS_IN_PROGRESS,
        "file_path": "app/adapters/domains/system.py",
        "test_case_id": "cron-schedule-102",
        "error_snippet": "",
        "assignee": "wangwu",
    },
    {
        "title": "用例评审通过后状态未同步到关联需求",
        "description": "用例评审通过后，关联的 JIRA 需求状态仍停留在\"待处理\"，未自动更新为\"已通过\"。",
        "severity": SEVERITY_MAJOR,
        "status": STATUS_FIXED,
        "file_path": "app/adapters/domains/case_reviews.py",
        "test_case_id": "review-sync-115",
        "error_snippet": "",
        "assignee": "zhangsan",
    },
    {
        "title": "文件仓库拉取大文件时进度条不更新",
        "description": "从 Git 仓库拉取大文件（>50MB）时，前端进度条一直停留在 0%，但实际文件正在下载。",
        "severity": SEVERITY_MAJOR,
        "status": STATUS_WONT_FIX,
        "file_path": "app/adapters/domains/project.py",
        "test_case_id": "file-pull-progress-128",
        "error_snippet": "",
        "assignee": "lisi",
    },
    {
        "title": "环境变量复制后引用关系断裂",
        "description": "复制环境时，复制的环境变量未正确保留原变量的引用关系，导致部分接口用例在复制的环境中执行失败。",
        "severity": SEVERITY_MAJOR,
        "status": STATUS_OPEN,
        "file_path": "app/api_testing/services/environments.py",
        "test_case_id": "env-copy-ref-136",
        "error_snippet": "KeyError: 'ref_env_var_id'",
        "assignee": "admin",
    },

    # ── 次要缺陷 ────────────────────────────────────────────────
    {
        "title": "缺陷详情页更新时间显示为 NaN",
        "description": "在缺陷详情页查看缺陷时，\"更新时间\"字段显示为 `NaN`，应为时间戳格式化后的日期字符串。",
        "severity": SEVERITY_MINOR,
        "status": STATUS_OPEN,
        "file_path": "frontend/src/pages/BugManagement/Detail.vue",
        "test_case_id": "bug-detail-time-142",
        "error_snippet": "",
        "assignee": "wangwu",
    },
    {
        "title": "接口测试历史记录无法清空",
        "description": "接口测试的历史执行记录超过 100 条后，点击\"清空历史\"按钮无响应，接口返回成功但数据未删除。",
        "severity": SEVERITY_MINOR,
        "status": STATUS_CLOSED,
        "file_path": "app/api_testing/services/cases.py",
        "test_case_id": "api-history-clear-157",
        "error_snippet": "",
        "assignee": "zhangsan",
    },
    {
        "title": "通知中心未读数量角标不刷新",
        "description": "打开通知中心后标记全部已读，但顶部的未读数量角标仍然显示旧值，需要刷新页面才能更新。",
        "severity": SEVERITY_MINOR,
        "status": STATUS_FIXED,
        "file_path": "frontend/src/layout/components/NotificationBell.vue",
        "test_case_id": "notif-badge-163",
        "error_snippet": "",
        "assignee": "lisi",
    },
    {
        "title": "深色主题下标签颜色对比度过低",
        "description": "在深色主题模式下，缺陷标签的浅色文字与深色背景对比度过低，可读性差。",
        "severity": SEVERITY_MINOR,
        "status": STATUS_WONT_FIX,
        "file_path": "frontend/src/styles/theme/dark.scss",
        "test_case_id": "theme-contrast-178",
        "error_snippet": "",
        "assignee": "admin",
    },
]


def _seed_exists(title: str) -> bool:
    """判断是否已存在相同标题的缺陷（用于幂等）。"""
    for d in DefectRepo.list(limit=500):
        if d.get("title") == title:
            return True
    return False


def seed_defects(reset: bool = False, dry_run: bool = False) -> dict:
    """插入种子缺陷数据。

    Args:
        reset: 是否先清空现有缺陷
        dry_run: 是否仅预览不实际执行

    Returns:
        dict: {"inserted": int, "skipped": int, "total": int}
    """
    stats = {"inserted": 0, "skipped": 0, "total": len(SEED_DEFECTS)}

    if reset and not dry_run:
        # 清空现有缺陷数据
        from app.core.database import Database
        conn = Database.get_conn("defects.db")
        conn.execute("DELETE FROM defects")
        conn.commit()
        print("已清空现有缺陷数据。")
        stats["skipped"] = 0
    elif reset and dry_run:
        print("[DRY-RUN] 将清空现有缺陷数据。")

    for item in SEED_DEFECTS:
        title = item["title"]

        if dry_run:
            print(f"[DRY-RUN] 待插入: {title}")
            stats["inserted"] += 1
            continue

        # 幂等检查
        if _seed_exists(title):
            print(f"[SKIP] 已存在，跳过: {title}")
            stats["skipped"] += 1
            continue

        try:
            defect = DefectRepo.create({
                "title": title,
                "description": item.get("description", ""),
                "severity": item.get("severity", SEVERITY_MAJOR),
                "file_path": item.get("file_path", ""),
                "test_case_id": item.get("test_case_id", ""),
                "error_snippet": item.get("error_snippet", ""),
                "assignee": item.get("assignee", ""),
            })
            # 更新状态（create_defect 默认状态为 open）
            status = item.get("status", STATUS_OPEN)
            if status != STATUS_OPEN:
                DefectRepo.update(defect["id"], {"status": status})
            stats["inserted"] += 1
            print(f"[OK] 已插入: {title}")
        except Exception as e:
            print(f"[ERROR] 插入失败: {title} → {e}")

    return stats


def print_summary(stats: dict) -> None:
    """打印执行摘要。"""
    print("\n" + "=" * 60)
    print(f"种子数据执行完成：共 {stats['total']} 条")
    print(f"  新插入: {stats['inserted']} 条")
    print(f"  已跳过: {stats['skipped']} 条")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="初始化种子缺陷数据脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="先清空现有缺陷数据再重新插入（慎用！）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览将要插入的数据，不实际写入数据库",
    )
    args = parser.parse_args()

    print("开始初始化种子缺陷数据...")
    if args.dry_run:
        print("[DRY-RUN] 模式：仅预览不写入\n")
    stats = seed_defects(reset=args.reset, dry_run=args.dry_run)
    print_summary(stats)

    if not args.dry_run:
        # 验证插入结果
        defects = DefectRepo.list(limit=500)
        if defects:
            print(f"\n当前缺陷列表（共 {len(defects)} 条，仅显示前 5 条）:")
            for d in defects[:5]:
                print(f"  [{d.get('status')}/{d.get('severity')}] {d.get('title')}")
        else:
            print("\n⚠️  警告：插入后未查询到任何缺陷数据！")


if __name__ == "__main__":
    main()
