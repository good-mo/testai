"""
Schema Registry 单一来源维护回归测试。

验证目标（Issue #512 · Schema 单一来源收敛）：
  1. schema_registry.py 与当前各模块内联 DDL 保持一致（无漂移）。
  2. 重新生成是幂等的（--update 不会反复产生新的 diff）。
  3. 公共查询 API（get_table_ddl / audit_all_schemas 等）正常，
     且共享表 api_definitions 的权威列并集覆盖被保留。
"""
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "sync_schema_registry.py")


def _run_check():
    return subprocess.run(
        [sys.executable, SCRIPT, "--check"],
        capture_output=True, text=True, cwd=PROJECT_ROOT)


def test_registry_in_sync_with_module_ddl():
    """registry 与模块内联 DDL 无漂移（--check 返回 0）。"""
    r = _run_check()
    assert r.returncode == 0, f"存在漂移:\n{r.stdout}\n{r.stderr}"


def test_regeneration_is_idempotent():
    """重新生成后 registry 内容不变（单一来源收敛稳定）。"""
    # 先备份当前文件内容
    reg_path = os.path.join(PROJECT_ROOT, "app", "core", "schema_registry.py")
    with open(reg_path, encoding="utf-8") as f:
        committed = f.read()
    # 执行一次 --update（应生成与当前完全一致的文本）
    r = subprocess.run(
        [sys.executable, SCRIPT, "--update"],
        capture_output=True, text=True, cwd=PROJECT_ROOT)
    assert r.returncode == 0, f"--update 失败:\n{r.stdout}\n{r.stderr}"
    with open(reg_path, encoding="utf-8") as f:
        regenerated = f.read()
    assert regenerated == committed, "schema_registry 重新生成后内容发生变化（非幂等）"


def test_public_api_and_override_preserved():
    """公共查询 API 正常；共享表 api_definitions 权威列并集保留。"""
    sys.path.insert(0, PROJECT_ROOT)
    from app.core.schema_registry import (
        TABLE_DDL,
        audit_all_schemas,
        get_table_ddl,
        list_all_tables,
    )
    # 表清单完整
    assert len(TABLE_DDL) >= 70
    assert "api_definitions" in TABLE_DDL
    # api_definitions 权威 DDL 应含 V1(V1 兼容层) 与 V2(apitest) 两套列
    ddl = get_table_ddl("api_definitions")
    assert "request_headers" in ddl, "api_definitions 权威 DDL 缺少 V1 兼容层列"
    assert "headers" in ddl, "api_definitions 权威 DDL 缺少 V2 主引擎列"
    # 审计应能正常运行
    report = audit_all_schemas()
    assert report["total_tables"] == len(list_all_tables())


def _run_check_alter():
    """运行 --check-alter 子命令。"""
    return subprocess.run(
        [sys.executable, SCRIPT, "--check-alter"],
        capture_output=True, text=True, cwd=PROJECT_ROOT)


def test_alter_columns_converged_to_create_table():
    """运行时 ALTER TABLE 添加的列已收敛进模块 CREATE TABLE DDL。

    防止「Alembic 基线 DDL 落后于运行时 ALTER」导致新库缺列。
    """
    r = _run_check_alter()
    assert r.returncode == 0, f"ALTER 补列漂移:\n{r.stdout}\n{r.stderr}"
    assert "ALTER 补列漂移检测通过" in r.stdout


def test_alter_added_columns_present_in_registry_ddl():
    """已验证收敛的关键列应出现在 schema_registry DDL 中。"""
    sys.path.insert(0, PROJECT_ROOT)
    from app.core.schema_registry import TABLE_DDL

    # projects: organization_id / deleted 由 organizations 模块运行时 ALTER 补列
    ddl_projects = TABLE_DDL.get("projects", "")
    assert "organization_id" in ddl_projects, "projects DDL 缺 organization_id"
    assert "deleted" in ddl_projects, "projects DDL 缺 deleted"

    # fake_error_rules: type/resp_type/relation/expression 由运行时 ALTER 补列
    ddl_fer = TABLE_DDL.get("fake_error_rules", "")
    assert "type TEXT" in ddl_fer, "fake_error_rules DDL 缺 type"
    assert "resp_type TEXT" in ddl_fer, "fake_error_rules DDL 缺 resp_type"
    assert "relation TEXT" in ddl_fer, "fake_error_rules DDL 缺 relation"
    assert "expression TEXT" in ddl_fer, "fake_error_rules DDL 缺 expression"

    # case_review_headers: reviewers_json 由运行时 ALTER 补列
    ddl_crh = TABLE_DDL.get("case_review_headers", "")
    assert "reviewers_json" in ddl_crh, "case_review_headers DDL 缺 reviewers_json"
