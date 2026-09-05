#!/usr/bin/env python3
"""
全量种子数据脚本
================
为所有前端界面初始化完整、真实的演示数据。

覆盖模块：
  - 组织/项目/用户/成员
  - 用例管理（用例、关联、评审、依赖、版本、需求、变更记录）
  - 缺陷管理（缺陷、评论）
  - 接口测试（定义、用例、场景、Mock、环境、环境组、全局参数、模块树）
  - API 测试（接口定义、用例、场景、Mock 服务、环境、断言规则）
  - 测试计划（计划、关联用例、模块）
  - 环境管理（Docker 环境、告警）
  - 数据工厂（模板、批次）
  - 洞察/追溯（测试运行记录）
  - 运行记录（完整快照）
  - 脚本健康度（脚本、定位器、执行历史）
  - 资源池
  - 用户组/权限

用法：
    python3 scripts/seed_all_data.py            # 幂等执行
    python3 scripts/seed_all_data.py --reset    # 先清空再插入
    python3 scripts/seed_all_data.py --dry-run  # 仅预览
"""
import argparse
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.logging_config import get_logger

logger = get_logger(__name__)


def _idempotent(func_name, check_func, create_func, label=""):
    """幂等执行：如果已存在则跳过。"""
    if check_func():
        print(f"  [SKIP] {label} 已存在，跳过")
        return False
    create_func()
    print(f"  [OK] {label} 已创建")
    return True


def seed_projects_and_members():
    """确保组织和项目数据存在。"""
    print("\n📁 项目与组织")
    from app.repositories.project_repo import ProjectRepo
    from app.services.organization_service import organization_service

    # 调用已有的租户种子数据
    organization_service.seed_tenant_data()
    print("  [OK] 租户数据（组织/用户/项目）已就绪")

    # 确保项目成员数据
    projects = ProjectRepo.list(limit=100)
    if not projects:
        print("  [ERROR] 无项目可用")
        return []

    # 获取用户
    from app.auth.store import auth_store
    users = []
    for username in ["admin", "org_admin", "test_leader", "dev_engineer", "qa_engineer"]:
        try:
            u = auth_store.get_user_by_username(username)
            if u:
                users.append(u)
        except Exception:
            pass

    # 给每个项目添加成员
    for proj in projects:
        ProjectRepo.add_member(
            project_id=proj["id"],
            user_id="admin",
            username="admin",
            name="管理员",
            role="admin",
        )
        for u in users:
            if u.get("username") != "admin":
                ProjectRepo.add_member(
                    project_id=proj["id"],
                    user_id=u["id"],
                    username=u.get("username", ""),
                    name=u.get("name", u.get("username", "")),
                    role="member",
                )
    print(f"  [OK] 已为 {len(projects)} 个项目添加成员")

    return projects


def seed_case_management():
    """用例管理高级数据：关联、评审、依赖、需求、变更记录。"""
    print("\n📋 用例管理")
    from app.cases.management import (
        add_case_dependency,
        add_case_relation,
        add_case_requirement,
        get_case_reviews,
        list_case_relations,
        submit_for_review,
    )
    from app.repositories.case_repo import CaseRepo

    cases = CaseRepo.list_cases(limit=500)
    if len(cases) < 2:
        print("  [WARN] 用例数量不足，先创建一些用例")
        return

    # 添加关联关系（前 20 对）
    rel_count = 0
    for i in range(min(20, len(cases) - 1)):
        c1, c2 = cases[i], cases[i + 1]
        try:
            rels = list_case_relations(c1["id"])
            existing_ids = {r.get("related_case_id") for r in rels}
            if c2["id"] not in existing_ids:
                add_case_relation(c1["id"], c2["id"], relation_type="related")
                rel_count += 1
        except Exception:
            pass
    print(f"  [OK] 添加 {rel_count} 条用例关联关系")

    # 添加评审
    review_count = 0
    for _, c in enumerate(cases[:30]):
        try:
            reviews = get_case_reviews(c["id"])
            if not reviews:
                submit_for_review(c["id"], reviewer="test_leader",
                                  comment="请评审此用例")
                review_count += 1
        except Exception:
            pass
    print(f"  [OK] 添加 {review_count} 条用例评审")

    # 添加依赖关系（幂等）
    from app.cases.management import list_case_dependencies
    dep_count = 0
    for i in range(min(15, len(cases) - 1)):
        c1, c2 = cases[i], cases[i + 1]
        try:
            deps = list_case_dependencies(c1["id"])
            existing_dep_ids = {d.get("depends_on") for d in deps}
            if c2["id"] not in existing_dep_ids:
                add_case_dependency(c1["id"], c2["id"], dep_type="before",
                                    description="前置依赖")
                dep_count += 1
        except Exception:
            pass
    print(f"  [OK] 添加 {dep_count} 条用例依赖关系")

    # 添加需求关联（幂等）
    from app.cases.management import list_case_requirements
    req_count = 0
    for i, c in enumerate(cases[:20]):
        try:
            reqs = list_case_requirements(c["id"])
            existing_req_ids = {r.get("requirement_id") for r in reqs}
            req_id = f"REQ-{100+i:04d}"
            if req_id not in existing_req_ids:
                add_case_requirement(c["id"], req_id,
                                     requirement_type="jira",
                                     requirement_title=f"需求 #{100+i:04d}")
                req_count += 1
        except Exception:
            pass
    print(f"  [OK] 添加 {req_count} 条需求关联")


def seed_defect_comments():
    """缺陷评论。"""
    print("\n🐛 缺陷管理")
    from app.repositories.defect_repo import DefectRepo

    defects = DefectRepo.list(limit=100)
    if not defects:
        print("  [WARN] 无缺陷数据")
        return

    comment_count = 0
    for d in defects[:10]:
        try:
            existing = DefectRepo.list_comments(d["id"])
            if not existing:
                DefectRepo.create_comment(
                    bug_id=d["id"],
                    content=f"这是缺陷「{d.get('title', '')}」的处理评论，需要及时修复。",
                    create_user="test_leader",
                )
                comment_count += 1
        except Exception:
            pass
    print(f"  [OK] 添加 {comment_count} 条缺陷评论")


def seed_api_test_data():
    """接口测试模块数据。"""
    print("\n🔌 接口测试")
    from app.apitest.module_store import (
        add_module,
        list_modules,
    )
    from app.apitest.store import (
        create_api_case,
        create_definition,
        create_env_group,
        create_environment,
        create_mock,
        create_scenario,
        list_definitions,
        save_global_params,
    )
    from app.repositories.project_repo import ProjectRepo

    projects = ProjectRepo.list(limit=10)
    if not projects:
        print("  [WARN] 无项目")
        return
    project_id = projects[0]["id"]

    # 确保接口定义存在
    defs = list_definitions(limit=20)
    if not defs:
        create_definition(
            name="获取用户列表", method="GET", path="/api/users",
            description="获取系统用户列表", project_id=project_id,
        )
        create_definition(
            name="创建用户", method="POST", path="/api/users",
            description="创建新用户", project_id=project_id,
        )
        create_definition(
            name="更新用户信息", method="PUT", path="/api/users/{id}",
            description="更新用户信息", project_id=project_id,
        )
        defs = list_definitions(limit=20)
        print(f"  [OK] 创建 {len(defs)} 个接口定义")

    # 接口用例：为所有接口定义创建用例（幂等：按 definition_id 去重）
    from app.apitest.store import list_api_cases
    existing_cases = list_api_cases(limit=1000)
    existing_def_ids = {c.get("api_definition_id") for c in existing_cases}
    created = 0
    for i, d in enumerate(defs):
        if d["id"] in existing_def_ids:
            continue
        create_api_case(
            name=f"测试-{d['name']}",
            api_definition_id=d["id"],
            request={"method": d["method"], "path": d["path"]},
            asserts=[
                {"type": "status_code", "expected": 200},
                {"type": "jsonpath", "expression": "$.code", "expected": "0"},
            ],
            status="draft" if i % 2 == 0 else "approved",
            priority="P2",
            project_id=project_id,
            method=d.get("method", "GET"),
            path=d.get("path", ""),
        )
        created += 1
    if created:
        print(f"  [OK] 为 {created} 个接口定义创建用例")

    # 接口场景
    from app.apitest.store import count_scenarios
    if count_scenarios(project_id) == 0:
        for i in range(5):
            steps = [
                {"case_id": c["id"], "order": 1, "enabled": True}
                for c in list_api_cases(limit=5)
            ] if list_api_cases(limit=5) else []
            create_scenario(
                name=f"用户管理场景 {i+1}",
                steps=steps or [],
                description=f"测试场景 {i+1}",
                status="draft" if i % 2 == 0 else "approved",
                project_id=project_id,
            )
        print("  [OK] 创建 5 个接口场景")

    # Mock
    from app.apitest.store import count_mocks
    if count_mocks(project_id) == 0:
        for _, d in enumerate(defs[:6]):
            create_mock(
                name=f"Mock-{d['name']}",
                api_definition_id=d["id"],
                method=d.get("method", "GET"),
                path=d.get("path", "/mock/api"),
                status_code=200,
                response_body=json.dumps({"code": 0, "data": {}}),
                active=1,
                project_id=project_id,
            )
        print("  [OK] 创建 6 个 Mock 服务")

    # 环境（为每个项目都补齐演示环境，避免切换到非默认项目时环境管理页为空）
    from app.apitest.store import count_environments
    _env_created_total = 0
    for _pid in {p["id"] for p in projects}:
        if count_environments(_pid) > 0:
            continue
        create_environment(
            name="开发环境",
            base_url="http://dev.example.com",
            headers={"Content-Type": "application/json", "Authorization": "Bearer dev-token"},
            variables={"username": "admin", "baseUrl": "http://dev.example.com"},
            project_id=_pid,
        )
        create_environment(
            name="测试环境",
            base_url="http://test.example.com",
            headers={"Content-Type": "application/json", "Authorization": "Bearer test-token"},
            variables={"username": "tester", "baseUrl": "http://test.example.com"},
            project_id=_pid,
        )
        create_environment(
            name="生产环境",
            base_url="https://prod.example.com",
            headers={"Content-Type": "application/json", "Authorization": "Bearer prod-token"},
            variables={"username": "operator", "baseUrl": "https://prod.example.com"},
            project_id=_pid,
        )
        _env_created_total += 3
    if _env_created_total:
        print(f"  [OK] 为各项目补齐接口测试环境 {_env_created_total} 个")

    # 环境组
    from app.apitest.store import list_env_groups
    if not list_env_groups(project_id):
        create_env_group(
            name="默认环境组",
            description="系统默认环境组",
            project_id=project_id,
            env_group_project=[{"projectId": project_id}],
        )
        print("  [OK] 创建环境组")

    # 全局参数
    from app.apitest.store import get_global_params
    if not get_global_params(project_id):
        save_global_params(
            project_id=project_id,
            headers=[
                {"key": "Content-Type", "value": "application/json", "enable": True},
                {"key": "Authorization", "value": "Bearer {{token}}", "enable": True},
            ],
            common_variables=[
                {"key": "baseUrl", "value": "http://example.com", "enable": True},
                {"key": "token", "value": "", "enable": True},
            ],
        )
        print("  [OK] 创建全局参数")

    # 模块树
    modules = list_modules("definition", project_id)
    if not modules:
        for mname in ["用户模块", "订单模块", "商品模块", "支付模块"]:
            add_module("definition", mname, project_id=project_id)
        print("  [OK] 创建接口定义模块树")


def seed_api_testing_data():
    """api_testing 模块数据（与 apitest 共用部分表）。"""
    print("\n🔧 API 测试")
    from app.api_testing.management import (
        create_api_test_case,
        create_assertion_rule,
        create_mock_service,
        create_scenario,
    )
    from app.api_testing.management import (
        create_environment as create_api_env,
    )
    from app.apitest.store import list_definitions

    defs = list_definitions(limit=20)
    if not defs:
        print("  [SKIP] 接口定义不存在")
        return

    # API 测试用例（写入 api_test_cases 表）：为所有定义创建（幂等）
    from app.core.database import Database
    conn = Database.get_conn("apitest.db")
    existing_api_cases = conn.execute("SELECT definition_id FROM api_test_cases").fetchall()
    existing_def_ids = {r["definition_id"] for r in existing_api_cases}
    created = 0
    for _, d in enumerate(defs):
        if d["id"] in existing_def_ids:
            continue
        create_api_test_case(
            name=f"API用例-{d['name']}",
            definition_id=d["id"],
            method=d.get("method", "GET"),
            path=d.get("path", "/api/test"),
            assertions=[
                {"type": "status_code", "value": "200"},
                {"type": "jsonpath", "field": "$.code", "value": "0"},
            ],
            project_id=d.get("project_id", ""),
        )
        created += 1
    if created:
        print(f"  [OK] 为 {created} 个接口定义创建 API 测试用例")

    # API 场景
    # 检查通过 management 创建的场景
    from app.core.database import Database as DB
    c2 = DB.get_conn("apitest.db")
    sc = c2.execute("SELECT COUNT(*) FROM api_scenarios WHERE name LIKE 'API场景%'").fetchone()[0]
    if sc == 0:
        for i in range(3):
            create_scenario(
                name=f"API场景 {i+1}",
                description=f"API测试场景 {i+1}",
                project_id="",
            )
        print("  [OK] 创建 3 个 API 测试场景")

    # Mock 服务
    mock_count = conn.execute("SELECT COUNT(*) FROM mock_services").fetchone()[0]
    if mock_count == 0:
        for _, d in enumerate(defs[:5]):
            create_mock_service(
                name=f"APIMock-{d['name']}",
                method=d.get("method", "GET"),
                path=d.get("path", "/mock"),
                response_code=200,
                response_body=json.dumps({"code": 0, "data": {"status": "ok"}}),
                project_id=d.get("project_id", ""),
            )
        print("  [OK] 创建 5 个 Mock 服务")

    # API 环境
    env_count = conn.execute("SELECT COUNT(*) FROM api_environments").fetchone()[0]
    if env_count == 0:
        create_api_env(
            name="API测试环境",
            description="API测试专用环境",
            base_url="http://api.example.com",
            project_id="",
        )
        print("  [OK] 创建 API 测试环境")

    # 断言规则
    rule_count = conn.execute("SELECT COUNT(*) FROM assertion_rules").fetchone()[0]
    if rule_count == 0:
        for name, rule_type, expression, expected in [
            ("状态码检查", "status_code", "", "200"),
            ("JSON路径检查", "jsonpath", "$.code", "0"),
            ("文本包含", "text", "", "success"),
            ("正则匹配", "regex", r"\d{4}-\d{2}-\d{2}", ""),
        ]:
            create_assertion_rule(
                name=name,
                rule_type=rule_type,
                expression=expression,
                expected=expected,
                description=f"内置规则：{name}",
            )
        print("  [OK] 创建 4 条断言规则")


def seed_test_plan_data():
    """测试计划模块数据。"""
    print("\n📊 测试计划")
    from app.apitest.store import list_api_cases
    from app.repositories.case_repo import CaseRepo
    from app.repositories.project_repo import ProjectRepo
    from app.services.test_plan_service import test_plan_service
    projects = ProjectRepo.list(limit=1)
    default_project_id = projects[0]["id"] if projects else ""

    plans = test_plan_service.list_plans(limit=10)
    if not plans:
        print("  [WARN] 无测试计划")
        return

    # 确保测试计划有关联项目
    from app.core.database import Database
    conn = Database.get_conn("test_plans.db")
    for plan in plans:
        if not plan.get("project_id"):
            conn.execute(
                "UPDATE test_plans SET project_id = ? WHERE id = ?",
                (default_project_id, plan["id"]),
            )
    conn.commit()

    cases = CaseRepo.list_cases(limit=20)
    api_cases = list_api_cases(limit=20)

    # 给测试计划关联用例（幂等：已有关联的跳过）
    added = 0
    for plan in plans[:5]:
        plan_cases = test_plan_service.list_plan_cases(plan["id"])
        existing_case_ids = {pc.get("case_id") for pc in plan_cases}
        # 关联功能用例
        for c in cases[:5]:
            if c["id"] in existing_case_ids:
                continue
            try:
                test_plan_service.add_plan_case(plan["id"], c["id"], case_type="functional")
                added += 1
                existing_case_ids.add(c["id"])
            except Exception:
                pass
        # 关联接口用例
        for ac in api_cases[:5]:
            if ac["id"] in existing_case_ids:
                continue
            try:
                test_plan_service.add_plan_case(plan["id"], ac["id"], case_type="api")
                added += 1
                existing_case_ids.add(ac["id"])
            except Exception:
                pass
    print(f"  [OK] 为测试计划关联 {added} 个用例")

    # 创建模块
    modules = test_plan_service.list_modules()
    if not modules:
        test_plan_service.create_module("核心功能", parent_id="root")
        test_plan_service.create_module("接口测试", parent_id="root")
        test_plan_service.create_module("性能测试", parent_id="root")
        print("  [OK] 创建测试计划模块")


def seed_environments_and_alerts():
    """环境管理（Docker 环境）与告警。"""
    print("\n🌐 环境管理")
    from app.environment.manager import (
        list_environments,
        register_environment,
    )

    envs = list_environments()
    if not envs:
        register_environment(
            name="Docker-测试环境A",
            description="用于功能测试的 Docker 环境",
            env_type="docker",
            endpoint="http://localhost:8080",
            container_name="test-container-a",
            image="python:3.12-slim",
            health_check_url="http://localhost:8080/health",
            owner="test_leader",
            tags=["docker", "test", "functional"],
        )
        register_environment(
            name="Docker-测试环境B",
            description="用于接口测试的 Docker 环境",
            env_type="docker",
            endpoint="http://localhost:9090",
            container_name="test-container-b",
            image="nginx:alpine",
            health_check_url="http://localhost:9090/health",
            owner="qa_engineer",
            tags=["docker", "test", "api"],
        )
        register_environment(
            name="Docker-性能压测环境",
            description="性能压测专用环境",
            env_type="docker",
            endpoint="http://localhost:7070",
            container_name="perf-container",
            image="locustio/locust",
            health_check_url="http://localhost:7070/health",
            owner="dev_engineer",
            tags=["docker", "perf", "load"],
        )
        print("  [OK] 创建 3 个 Docker 环境")


def seed_data_factory():
    """数据工厂模块数据。"""
    print("\n📦 数据工厂")
    from app.repositories.datafactory_repo import DatafactoryRepo

    # 先确保默认模板存在
    DatafactoryRepo.seed_default_templates()
    templates = DatafactoryRepo.list_templates(limit=20)
    print(f"  [OK] 已有 {len(templates)} 个数据模板")

    # 生成数据批次
    batches = DatafactoryRepo.list_batches(limit=5)
    if not batches:
        for t in templates[:3]:
            try:
                DatafactoryRepo.generate_data(
                    template_id=t["id"],
                    batch_size=5,
                    env_key="test",
                )
            except Exception as e:
                logger.warning(f"生成数据失败: {e}")
        print("  [OK] 生成数据批次")


def seed_trace_and_runs():
    """洞察/追溯与运行记录。"""
    print("\n📈 追溯与运行记录")
    # 追溯记录
    from app.core.database import Database
    from app.insights.trace import record_run
    from app.repositories.run_repo import RunRepo
    conn = Database.get_conn("trace.db")
    run_count = conn.execute("SELECT COUNT(*) FROM test_runs").fetchone()[0]
    if run_count == 0:
        record_run(
            file_path="app/auth/router.py",
            result="passed",
            passed_count=12,
            failed_count=0,
            error_count=0,
            coverage=85.5,
            attribution="requirement_change",
            note="登录认证模块测试通过",
            created_by="admin",
        )
        record_run(
            file_path="app/cases/repository.py",
            result="passed",
            passed_count=18,
            failed_count=1,
            error_count=0,
            coverage=92.0,
            attribution="code_regression",
            note="用例管理模块测试基本通过",
            created_by="test_leader",
        )
        record_run(
            file_path="app/api_testing/services/cases.py",
            result="failed",
            passed_count=8,
            failed_count=3,
            error_count=1,
            coverage=65.0,
            attribution="coverage_gap",
            note="接口测试部分用例失败",
            created_by="qa_engineer",
        )
        print("  [OK] 创建 3 条追溯记录")

    # 运行记录
    conn2 = Database.get_conn("runs.db")
    record_count = conn2.execute("SELECT COUNT(*) FROM run_records").fetchone()[0]
    if record_count == 0:
        RunRepo.save(
            file_path="app/auth/router.py",
            source_code="def login(): pass",
            generated_tests="def test_login(): assert True",
            test_result={"passed": True, "total": 12, "passed_count": 12},
            coverage_report={"lines": 85.5, "branches": 72.0},
            performance_report={"duration": 0.5, "throughput": 100},
            retry_count=0,
            saved_to="output/test_auth.py",
            source="single",
        )
        RunRepo.save(
            file_path="app/cases/repository.py",
            source_code="def create_case(): pass",
            generated_tests="def test_create_case(): assert True",
            test_result={"passed": True, "total": 18, "passed_count": 17},
            coverage_report={"lines": 92.0, "branches": 88.0},
            performance_report={"duration": 1.2, "throughput": 80},
            retry_count=1,
            saved_to="output/test_cases.py",
            source="project",
        )
        print("  [OK] 创建 2 条运行记录")


def seed_script_health():
    """脚本健康度模块数据。"""
    print("\n🩺 脚本健康度")
    from app.repositories.script_repo import ScriptRepo

    scripts = ScriptRepo.list(limit=10)
    if not scripts:
        ScriptRepo.register(
            name="登录测试脚本",
            file_path="tests/test_login.py",
            framework="pytest",
            description="登录功能测试脚本",
            locators=[
                {"name": "username", "element_type": "input",
                 "current_strategy": "css", "current_selector": "#username",
                 "best_strategy": "data-testid", "best_selector": "login-username"},
                {"name": "login_btn", "element_type": "button",
                 "current_strategy": "css", "current_selector": ".login-btn",
                 "best_strategy": "data-testid", "best_selector": "login-submit"},
            ],
        )
        ScriptRepo.register(
            name="API接口测试脚本",
            file_path="tests/test_api.py",
            framework="pytest",
            description="API接口功能测试脚本",
            locators=[
                {"name": "api_request", "element_type": "api",
                 "current_strategy": "css", "current_selector": "/api/users",
                 "best_strategy": "data-testid", "best_selector": "api-users"},
            ],
        )
        scripts = ScriptRepo.list(limit=10)
        print(f"  [OK] 创建 {len(scripts)} 个测试脚本")

        # 记录执行历史
        for s in scripts:
            ScriptRepo.record_execution(
                script_id=s["id"],
                success=True,
                duration=0.8,
            )
            ScriptRepo.record_execution(
                script_id=s["id"],
                success=True,
                duration=1.1,
            )
            ScriptRepo.record_execution(
                script_id=s["id"],
                success=False,
                duration=1.5,
                error_type="AssertionError",
                error_message="断言失败：期望值不匹配",
            )
        print("  [OK] 记录脚本执行历史")


def seed_resource_pools():
    """资源池数据。"""
    print("\n💻 资源池")
    from app.core.database import Database
    conn = Database.get_conn("tga.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resource_pools (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            enable INTEGER DEFAULT 1,
            created_at REAL,
            updated_at REAL
        )
    """)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM resource_pools").fetchone()[0]
    if count == 0:
        pools = [
            ("默认资源池", "系统默认测试资源池"),
            ("高性能资源池", "高性能执行资源池"),
            ("低功耗资源池", "低成本执行资源池"),
        ]
        now = time.time()
        for name, desc in pools:
            conn.execute(
                "INSERT INTO resource_pools (id, name, description, enable, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4()), name, desc, 1, now, now),
            )
        conn.commit()
        print(f"  [OK] 创建 {len(pools)} 个资源池")


def seed_tasks():
    """任务中心数据。"""
    print("\n📌 任务中心")
    from app.core.database import Database
    from app.tasks.manager import TaskStore

    store = TaskStore()
    # 经 Database 统一连接查询是否已有任务
    conn = Database.get_conn("tasks.db")
    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

    if count == 0:
        store.save_task(str(uuid.uuid4()), coro_name="generate_tests", args=["app/auth/router.py"])
        store.save_task(str(uuid.uuid4()), coro_name="run_tests", args=["tests/test_auth.py"])
        print("  [OK] 创建任务中心示例任务")


def seed_user_groups():
    """用户组数据。"""
    print("\n👥 用户组")
    from app.repositories.user_group_repo import UserGroupRepo
    groups = UserGroupRepo.list_groups("SYSTEM", "")
    print(f"  [OK] 已有 {len(groups)} 个用户组")

def seed_additional_data():
    """补充数据：告警、项目环境关联、用户组成员、权限、定位器、调试日志、API关注、API密钥。"""
    print("\n📦 补充数据")
    from app.core.database import Database
    conn = Database.get_conn("tga.db")

    # 1. 告警数据
    from app.environment.manager import list_alerts, list_environments
    from app.repositories.environment_repo import EnvironmentRepo
    envs = list_environments()
    if envs and not list_alerts(limit=1):
        for i, env in enumerate(envs[:3]):
            level = ["info", "warning", "critical"][i % 3]
            EnvironmentRepo.create_alert(
                env_id=env["id"],
                env_name=env.get("name", ""),
                level=level,
                message=f"环境「{env.get('name', '')}」状态监控通知",
                detail="系统自动生成的环境状态告警信息",
            )
        print("  [OK] 创建 3 条环境告警")

    # 2. 项目环境关联
    env_count = conn.execute("SELECT COUNT(*) FROM project_envs").fetchone()[0]
    if env_count == 0:
        from app.repositories.project_repo import ProjectRepo
        projects = ProjectRepo.list(limit=5)
        env_list = conn.execute("SELECT id FROM api_environments LIMIT 3").fetchall()
        if projects and env_list:
            now = time.time()
            for p in projects[:3]:
                for e in env_list:
                    conn.execute(
                        "INSERT INTO project_envs (id, project_id, env_id, created_at) VALUES (?,?,?,?)",
                        (str(uuid.uuid4()), p["id"], e["id"], now),
                    )
            conn.commit()
            print("  [OK] 创建项目环境关联")

    # 3. 用户组成员
    member_count = conn.execute("SELECT COUNT(*) FROM user_group_members").fetchone()[0]
    if member_count == 0:
        from app.auth.store import auth_store
        from app.repositories.user_group_repo import UserGroupRepo
        for username in ["admin", "org_admin", "test_leader", "dev_engineer", "qa_engineer"]:
            try:
                user = auth_store.get_user_by_username(username)
                if user:
                    UserGroupRepo.add_group_member(
                        group_id="admin" if username == "admin" else "member",
                        user_id=user["id"],
                        username=username,
                        name=user.get("name", username),
                        email=user.get("email", ""),
                        group_type="SYSTEM",
                        scope_id="global",
                    )
            except Exception:
                pass
        print("  [OK] 创建用户组成员关系")

    # 4. 用户组权限
    perm_count = conn.execute("SELECT COUNT(*) FROM user_group_permissions").fetchone()[0]
    if perm_count == 0:
        from app.repositories.user_group_repo import UserGroupRepo
        all_perms = ["READ", "ADD", "UPDATE", "DELETE", "EXECUTE"]
        for gid in ["admin", "member", "read-only", "org-admin", "org-member", "project-admin", "project-member", "project-readonly"]:
            try:
                UserGroupRepo.update_group_permissions(gid, all_perms)
            except Exception:
                pass
        print("  [OK] 配置用户组权限")

    # 5. API 调试日志
    # 注：api_debug_logs 表已随 Phase 1 收敛下线，调试执行统一写入
    # api_execution_logs（exec_type='debug'，见 PR #355），此处仅做幂等兜底。
    # 该表位于 apitest.db（见 schema_registry），需用独立连接。
    # 导入 execution_log 模块以触发建表
    from app.apitest import execution_log  # noqa: F401
    apitest_conn = Database.get_conn("apitest.db")
    try:
        debug_count = apitest_conn.execute(
            "SELECT COUNT(*) FROM api_execution_logs WHERE exec_type='debug'"
        ).fetchone()[0]
    except Exception:
        debug_count = 0
    if debug_count == 0:
        now = time.time()
        for i in range(5):
            apitest_conn.execute("""
                INSERT INTO api_execution_logs (id, exec_type, target_id, target_name,
                    method, url, request_data, response_data, asserts,
                    extracted_variables, passed, response_code, duration_ms,
                    error, detail, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (str(uuid.uuid4()), "debug", "", "调试",
                  "GET" if i % 2 == 0 else "POST",
                  f"/api/users/{i+1}" if i % 2 else "/api/users",
                  "{}", "{}", "[]", "{}",
                  1 if i % 3 != 0 else 0,
                  200 if i % 3 != 0 else 500,
                  50 + i * 10,
                  "" if i % 3 != 0 else "Internal Server Error",
                  "", now))
        apitest_conn.commit()
        print("  [OK] 创建 API 调试日志")

    # 6. API 关注
    follow_count = conn.execute("SELECT COUNT(*) FROM api_follows").fetchone()[0]
    if follow_count == 0:
        defs = conn.execute("SELECT id, name FROM api_definitions WHERE deleted = 0 LIMIT 5").fetchall()
        now = time.time()
        for d in defs:
            conn.execute("""
                INSERT INTO api_follows (id, resource_type, resource_id, user_id, created_at)
                VALUES (?,?,?,?,?)
            """, (str(uuid.uuid4()), "definition", d["id"], "admin", now))
        conn.commit()
        print("  [OK] 创建 API 关注关系")

    # 7. API 密钥
    key_count = conn.execute("SELECT COUNT(*) FROM api_keys").fetchone()[0]
    if key_count == 0:
        from app.auth.store import auth_store
        user = auth_store.get_user_by_username("admin")
        if user:
            now = time.time()
            conn.execute("""
                INSERT INTO api_keys (id, user_id, access_key, secret_key, description,
                    enable, forever, expire_time, create_time)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (str(uuid.uuid4()), user["id"],
                  "".join(uuid.uuid4().hex[:16]), "".join(uuid.uuid4().hex[:16]),
                  "默认API密钥", 1, 1, 0, now))
            conn.commit()
            print("  [OK] 创建 API 密钥")


def main():
    parser = argparse.ArgumentParser(
        description="全量种子数据脚本（覆盖所有前端模块）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--reset", action="store_true",
                        help="先清空再插入（慎用！）")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅预览不实际写入")
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY-RUN] 模式：仅预览不写入\n")

    print("🚀 开始初始化全量种子数据...\n")

    # 1. 项目与组织
    seed_projects_and_members()

    # 2. 用例管理
    seed_case_management()

    # 3. 缺陷管理
    seed_defect_comments()

    # 4. 接口测试
    seed_api_test_data()

    # 5. API 测试
    seed_api_testing_data()

    # 6. 测试计划
    seed_test_plan_data()

    # 7. 环境管理
    seed_environments_and_alerts()

    # 8. 数据工厂
    seed_data_factory()

    # 9. 追溯与运行记录
    seed_trace_and_runs()

    # 10. 脚本健康度
    seed_script_health()

    # 11. 资源池
    seed_resource_pools()

    # 12. 任务中心
    seed_tasks()

    # 13. 用户组
    seed_user_groups()

    # 14. 补充数据
    seed_additional_data()

    print("\n✅ 全量种子数据初始化完成！")


if __name__ == "__main__":
    main()

