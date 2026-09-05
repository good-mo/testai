"""全面 CRUD 测试 v2：使用正确的前端 API 路由，测试每个功能模块的创建、展示、修改、删除。"""
import os
import sys
import uuid

sys.path.insert(0, '/workspace')
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from fastapi.testclient import TestClient

PREFIX = "CRUDV2-"

def _data(resp):
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body

def _code(resp):
    body = resp.json()
    if isinstance(body, dict):
        return body.get("code", 200)
    return 200

def _unique(prefix=""):
    return f"{PREFIX}{prefix}-{uuid.uuid4().hex[:8]}"

def main():
    from app.main import app
    with TestClient(app) as client:
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, f"登录失败: {r.text}"
        session = r.json()["data"]
        client.headers.update({
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        })

        results = []
        failures = []

        def test(module, test_fn):
            try:
                test_fn(client)
                results.append(f"✅ {module}")
                print(f"✅ {module}")
            except Exception as e:
                failures.append((module, str(e)))
                results.append(f"❌ {module}: {e}")
                print(f"❌ {module}: {e}")

        # ═══ 1. 用例管理 CRUD ═══
        def test_cases_crud(client):
            name = _unique("用例")
            r = client.post("/api/cases", json={"title": name, "description": "CRUD测试", "priority": "P1"})
            assert r.status_code == 200, f"创建用例失败: {r.text}"
            case_id = _data(r).get("id") or r.json().get("id")
            assert case_id, f"创建用例未返回ID: {r.text}"
            r = client.get(f"/api/cases/{case_id}")
            assert r.status_code == 200, f"获取用例失败: {r.text}"
            r = client.get("/api/cases")
            assert r.status_code == 200, f"列出用例失败: {r.text}"
            r = client.put(f"/api/cases/{case_id}", json={"title": name + "-改"})
            assert r.status_code == 200, f"更新用例失败: {r.text}"
            r = client.delete(f"/api/cases/{case_id}")
            assert r.status_code == 200, f"删除用例失败: {r.text}"
            r = client.get(f"/api/cases/{case_id}")
            assert r.status_code == 404, f"删除后仍可获取: {r.text}"
        test("用例管理 CRUD", test_cases_crud)

        # ═══ 2. 缺陷管理 CRUD ═══
        def test_defects_crud(client):
            title = _unique("缺陷")
            r = client.post("/api/defects", json={"title": title, "description": "CRUD测试", "severity": "major"})
            assert r.status_code == 200, f"创建缺陷失败: {r.text}"
            defect_id = _data(r).get("id") or r.json().get("id")
            assert defect_id, f"创建缺陷未返回ID: {r.text}"
            r = client.get(f"/api/defects/{defect_id}")
            assert r.status_code == 200, f"获取缺陷失败: {r.text}"
            r = client.get("/api/defects")
            assert r.status_code == 200, f"列出缺陷失败: {r.text}"
            r = client.put(f"/api/defects/{defect_id}", json={"status": "closed"})
            assert r.status_code == 200, f"更新缺陷失败: {r.text}"
            r = client.delete(f"/api/defects/{defect_id}")
            assert r.status_code == 200, f"删除缺陷失败: {r.text}"
            r = client.get(f"/api/defects/{defect_id}")
            assert r.status_code == 404, f"删除后仍可获取: {r.text}"
        test("缺陷管理 CRUD", test_defects_crud)

        # ═══ 3. 接口定义 CRUD (apitest) ═══
        def test_apitest_definitions_crud(client):
            name = _unique("接口定义")
            r = client.post("/api/apitest/definitions", json={
                "name": name, "method": "GET", "path": f"/crud/{uuid.uuid4().hex[:8]}", "protocol": "HTTP"
            })
            assert r.status_code == 200, f"创建接口定义失败: {r.text}"
            def_id = r.json().get("id")
            assert def_id, f"创建接口定义未返回ID: {r.text}"
            r = client.get(f"/api/apitest/definitions/{def_id}")
            assert r.status_code == 200, f"获取接口定义失败: {r.text}"
            r = client.get("/api/apitest/definitions")
            assert r.status_code == 200, f"列出接口定义失败: {r.text}"
            r = client.put(f"/api/apitest/definitions/{def_id}", json={"name": name + "-改"})
            assert r.status_code == 200, f"更新接口定义失败: {r.text}"
            r = client.delete(f"/api/apitest/definitions/{def_id}")
            assert r.status_code == 200, f"删除接口定义失败: {r.text}"
            r = client.get(f"/api/apitest/definitions/{def_id}")
            assert r.status_code == 404, f"删除后仍可获取: {r.text}"
        test("接口定义 CRUD (apitest)", test_apitest_definitions_crud)

        # ═══ 4. 接口用例 CRUD (apitest) ═══
        def test_apitest_cases_crud(client):
            name = _unique("接口用例")
            r = client.post("/api/apitest/cases", json={"name": name, "description": "CRUD测试"})
            assert r.status_code == 200, f"创建接口用例失败: {r.text}"
            case_id = r.json().get("id")
            assert case_id, f"创建接口用例未返回ID: {r.text}"
            r = client.get(f"/api/apitest/cases/{case_id}")
            assert r.status_code == 200, f"获取接口用例失败: {r.text}"
            r = client.get("/api/apitest/cases")
            assert r.status_code == 200, f"列出接口用例失败: {r.text}"
            r = client.put(f"/api/apitest/cases/{case_id}", json={"name": name + "-改"})
            assert r.status_code == 200, f"更新接口用例失败: {r.text}"
            r = client.delete(f"/api/apitest/cases/{case_id}")
            assert r.status_code == 200, f"删除接口用例失败: {r.text}"
            r = client.get(f"/api/apitest/cases/{case_id}")
            assert r.status_code == 404, f"删除后仍可获取: {r.text}"
        test("接口用例 CRUD (apitest)", test_apitest_cases_crud)

        # ═══ 5. 场景编排 CRUD (apitest) ═══
        def test_apitest_scenarios_crud(client):
            name = _unique("场景")
            r = client.post("/api/apitest/scenarios", json={"name": name, "description": "CRUD测试"})
            assert r.status_code == 200, f"创建场景失败: {r.text}"
            scn_id = r.json().get("id")
            assert scn_id, f"创建场景未返回ID: {r.text}"
            r = client.get(f"/api/apitest/scenarios/{scn_id}")
            assert r.status_code == 200, f"获取场景失败: {r.text}"
            r = client.get("/api/apitest/scenarios")
            assert r.status_code == 200, f"列出场景失败: {r.text}"
            r = client.put(f"/api/apitest/scenarios/{scn_id}", json={"name": name + "-改"})
            assert r.status_code == 200, f"更新场景失败: {r.text}"
            r = client.delete(f"/api/apitest/scenarios/{scn_id}")
            assert r.status_code == 200, f"删除场景失败: {r.text}"
            r = client.get(f"/api/apitest/scenarios/{scn_id}")
            assert r.status_code == 404, f"删除后仍可获取: {r.text}"
        test("场景编排 CRUD (apitest)", test_apitest_scenarios_crud)

        # ═══ 6. Mock 服务 CRUD (apitest) ═══
        def test_apitest_mocks_crud(client):
            name = _unique("Mock")
            r = client.post("/api/apitest/mocks", json={
                "name": name, "method": "GET", "path": f"/mock/{uuid.uuid4().hex[:8]}",
                "status_code": 200, "response_body": '{"ok": true}'
            })
            assert r.status_code == 200, f"创建Mock失败: {r.text}"
            mock_id = r.json().get("id")
            assert mock_id, f"创建Mock未返回ID: {r.text}"
            r = client.get(f"/api/apitest/mocks/{mock_id}")
            assert r.status_code == 200, f"获取Mock失败: {r.text}"
            r = client.get("/api/apitest/mocks")
            assert r.status_code == 200, f"列出Mock失败: {r.text}"
            r = client.put(f"/api/apitest/mocks/{mock_id}", json={"name": name + "-改"})
            assert r.status_code == 200, f"更新Mock失败: {r.text}"
            r = client.delete(f"/api/apitest/mocks/{mock_id}")
            assert r.status_code == 200, f"删除Mock失败: {r.text}"
            r = client.get(f"/api/apitest/mocks/{mock_id}")
            assert r.status_code == 404, f"删除后仍可获取: {r.text}"
        test("Mock 服务 CRUD (apitest)", test_apitest_mocks_crud)

        # ═══ 7. API 环境 CRUD (apitest) ═══
        def test_apitest_envs_crud(client):
            name = _unique("API环境")
            r = client.post("/api/apitest/environments", json={
                "name": name, "base_url": f"https://{uuid.uuid4().hex[:8]}.example.com"
            })
            assert r.status_code == 200, f"创建环境失败: {r.text}"
            env_id = r.json().get("id")
            assert env_id, f"创建环境未返回ID: {r.text}"
            r = client.get(f"/api/apitest/environments/{env_id}")
            assert r.status_code == 200, f"获取环境失败: {r.text}"
            r = client.get("/api/apitest/environments")
            assert r.status_code == 200, f"列出环境失败: {r.text}"
            r = client.put(f"/api/apitest/environments/{env_id}", json={"name": name + "-改"})
            assert r.status_code == 200, f"更新环境失败: {r.text}"
            r = client.delete(f"/api/apitest/environments/{env_id}")
            assert r.status_code == 200, f"删除环境失败: {r.text}"
            r = client.get(f"/api/apitest/environments/{env_id}")
            assert r.status_code == 404, f"删除后仍可获取: {r.text}"
        test("API 环境 CRUD (apitest)", test_apitest_envs_crud)

        # ═══ 8. 项目管理 CRUD ═══
        def test_projects_crud(client):
            name = _unique("项目")
            r = client.post("/api/projects", json={"name": name, "description": "CRUD测试", "language": "python"})
            assert r.status_code == 200, f"创建项目失败: {r.text}"
            proj_id = r.json().get("id")
            assert proj_id, f"创建项目未返回ID: {r.text}"
            r = client.get(f"/api/projects/{proj_id}")
            assert r.status_code == 200, f"获取项目失败: {r.text}"
            r = client.get("/api/projects")
            assert r.status_code == 200, f"列出项目失败: {r.text}"
            r = client.put(f"/api/projects/{proj_id}", json={"name": name + "-改"})
            assert r.status_code == 200, f"更新项目失败: {r.text}"
            r = client.delete(f"/api/projects/{proj_id}")
            assert r.status_code == 200, f"删除项目失败: {r.text}"
            r = client.get(f"/api/projects/{proj_id}")
            assert r.status_code == 404, f"删除后仍可获取: {r.text}"
        test("项目管理 CRUD", test_projects_crud)

        # ═══ 9. 环境管理 CRUD ═══
        def test_envs_crud(client):
            name = _unique("环境")
            r = client.post("/api/environments", json={"name": name, "endpoint": "http://localhost:8080", "env_type": "dev"})
            assert r.status_code == 200, f"创建环境失败: {r.text}"
            env_id = r.json().get("id")
            assert env_id, f"创建环境未返回ID: {r.text}"
            r = client.get(f"/api/environments/{env_id}")
            assert r.status_code == 200, f"获取环境失败: {r.text}"
            r = client.get("/api/environments")
            assert r.status_code == 200, f"列出环境失败: {r.text}"
            r = client.put(f"/api/environments/{env_id}", json={"name": name + "-改"})
            assert r.status_code == 200, f"更新环境失败: {r.text}"
            r = client.delete(f"/api/environments/{env_id}")
            assert r.status_code == 200, f"删除环境失败: {r.text}"
            r = client.get(f"/api/environments/{env_id}")
            assert r.status_code == 404, f"删除后仍可获取: {r.text}"
        test("环境管理 CRUD", test_envs_crud)

        # ═══ 10. 数据工厂 CRUD ═══
        def test_datafactory_crud(client):
            name = _unique("数据模板")
            r = client.post("/api/data/templates", json={"name": name, "category": "user"})
            assert r.status_code == 200, f"创建数据模板失败: {r.text}"
            tpl_id = r.json().get("id")
            assert tpl_id, f"创建数据模板未返回ID: {r.text}"
            r = client.get(f"/api/data/templates/{tpl_id}")
            assert r.status_code == 200, f"获取数据模板失败: {r.text}"
            r = client.get("/api/data/templates")
            assert r.status_code == 200, f"列出数据模板失败: {r.text}"
            r = client.put(f"/api/data/templates/{tpl_id}", json={"name": name + "-改"})
            assert r.status_code == 200, f"更新数据模板失败: {r.text}"
            r = client.delete(f"/api/data/templates/{tpl_id}")
            assert r.status_code == 200, f"删除数据模板失败: {r.text}"
            r = client.get(f"/api/data/templates/{tpl_id}")
            assert r.status_code == 404, f"删除后仍可获取: {r.text}"
        test("数据工厂 CRUD", test_datafactory_crud)

        # ═══ 11. 脚本健康度 CRUD ═══
        def test_scripts_crud(client):
            name = _unique("脚本")
            r = client.post("/api/scripts", json={"name": name, "file_path": "test_page.py", "framework": "pytest"})
            assert r.status_code == 200, f"创建脚本失败: {r.text}"
            script_id = r.json().get("id")
            assert script_id, f"创建脚本未返回ID: {r.text}"
            r = client.get(f"/api/scripts/{script_id}")
            assert r.status_code == 200, f"获取脚本失败: {r.text}"
            r = client.get("/api/scripts")
            assert r.status_code == 200, f"列出脚本失败: {r.text}"
            r = client.put(f"/api/scripts/{script_id}", json={"name": name + "-改"})
            assert r.status_code == 200, f"更新脚本失败: {r.text}"
            r = client.delete(f"/api/scripts/{script_id}")
            assert r.status_code == 200, f"删除脚本失败: {r.text}"
            r = client.get(f"/api/scripts/{script_id}")
            assert r.status_code == 404, f"删除后仍可获取: {r.text}"
        test("脚本健康度 CRUD", test_scripts_crud)

        # ═══ 12. 前端接口定义 CRUD (/api/api-definitions) ═══
        def test_frontend_api_defs_crud(client):
            name = _unique("前端接口定义")
            r = client.post("/api/api-definitions", json={"name": name, "method": "POST", "path": f"/fe/{uuid.uuid4().hex[:8]}"})
            assert r.status_code == 200, f"创建前端接口定义失败: {r.text}"
            def_id = r.json().get("id")
            assert def_id, f"创建前端接口定义未返回ID: {r.text}"
            r = client.get(f"/api/api-definitions/{def_id}")
            assert r.status_code == 200, f"获取前端接口定义失败: {r.text}"
            r = client.get("/api/api-definitions")
            assert r.status_code == 200, f"列出前端接口定义失败: {r.text}"
            r = client.put(f"/api/api-definitions/{def_id}", json={"name": name + "-改"})
            assert r.status_code == 200, f"更新前端接口定义失败: {r.text}"
            r = client.delete(f"/api/api-definitions/{def_id}")
            assert r.status_code == 200, f"删除前端接口定义失败: {r.text}"
        test("前端接口定义 CRUD", test_frontend_api_defs_crud)

        # ═══ 13. 功能用例 CRUD (TestPilot) ═══
        def test_functional_cases_crud(client):
            name = _unique("功能用例")
            r = client.post("/functional/case/add", json={"name": name, "priority": "P1"})
            assert r.status_code == 200, f"创建功能用例失败: {r.text}"
            case_id = _data(r).get("id")
            assert case_id, f"创建功能用例未返回ID: {r.text}"
            # Read via detail
            r = client.get(f"/functional/case/detail/{case_id}")
            assert r.status_code == 200, f"获取功能用例失败: {r.text}"
            # List
            r = client.post("/functional/case/page", json={"pageSize": 100, "current": 1})
            assert r.status_code == 200, f"列出功能用例失败: {r.text}"
            # Update
            r = client.post("/functional/case/update", json={"id": case_id, "name": name + "-改"})
            assert r.status_code == 200, f"更新功能用例失败: {r.text}"
            # Delete
            r = client.post("/functional/case/delete", json={"id": case_id})
            assert r.status_code == 200, f"删除功能用例失败: {r.text}"
        test("功能用例 CRUD", test_functional_cases_crud)

        # ═══ 14. MS接口定义 CRUD ═══
        def test_ms_api_definition_crud(client):
            name = _unique("MS接口定义")
            r = client.post("/api/definition/add", json={
                "name": name, "method": "GET", "path": f"/ms/{uuid.uuid4().hex[:8]}", "protocol": "HTTP"
            })
            assert r.status_code == 200, f"创建MS接口定义失败: {r.text}"
            def_id = _data(r).get("id")
            assert def_id, f"创建MS接口定义未返回ID: {r.text}"
            # Read
            r = client.get(f"/api/definition/get-detail/{def_id}")
            assert r.status_code == 200, f"获取MS接口定义失败: {r.text}"
            # List
            r = client.post("/api/definition/page", json={"pageSize": 100, "current": 1})
            assert r.status_code == 200, f"列出MS接口定义失败: {r.text}"
            # Update
            r = client.post("/api/definition/update", json={"id": def_id, "name": name + "-改"})
            assert r.status_code == 200, f"更新MS接口定义失败: {r.text}"
            # Delete
            r = client.post("/api/definition/delete-to-gc", json={"id": def_id})
            assert r.status_code == 200, f"删除MS接口定义失败: {r.text}"
        test("MS接口定义 CRUD", test_ms_api_definition_crud)

        # ═══ 15. MS接口用例 CRUD ═══
        def test_ms_api_case_crud(client):
            name = _unique("MS接口用例")
            r = client.post("/api/case/add", json={"name": name})
            assert r.status_code == 200, f"创建MS接口用例失败: {r.text}"
            case_id = _data(r).get("id")
            assert case_id, f"创建MS接口用例未返回ID: {r.text}"
            # Read
            r = client.get(f"/api/case/get-detail/{case_id}")
            assert r.status_code == 200, f"获取MS接口用例失败: {r.text}"
            # List
            r = client.post("/api/case/page", json={"pageSize": 100, "current": 1})
            assert r.status_code == 200, f"列出MS接口用例失败: {r.text}"
            # Update
            r = client.post("/api/case/update", json={"id": case_id, "name": name + "-改"})
            assert r.status_code == 200, f"更新MS接口用例失败: {r.text}"
            # Delete
            r = client.post("/api/case/delete-to-gc", json={"id": case_id})
            assert r.status_code == 200, f"删除MS接口用例失败: {r.text}"
        test("MS接口用例 CRUD", test_ms_api_case_crud)

        # ═══ 16. MS场景 CRUD ═══
        def test_ms_scenario_crud(client):
            name = _unique("MS场景")
            r = client.post("/api/scenario/add", json={"name": name})
            assert r.status_code == 200, f"创建MS场景失败: {r.text}"
            scn_id = _data(r).get("id")
            assert scn_id, f"创建MS场景未返回ID: {r.text}"
            # Read
            r = client.get(f"/api/scenario/get/{scn_id}")
            assert r.status_code == 200, f"获取MS场景失败: {r.text}"
            # List
            r = client.post("/api/scenario/page", json={"pageSize": 100, "current": 1})
            assert r.status_code == 200, f"列出MS场景失败: {r.text}"
            # Update
            r = client.post("/api/scenario/update", json={"id": scn_id, "name": name + "-改"})
            assert r.status_code == 200, f"更新MS场景失败: {r.text}"
            # Delete
            r = client.post("/api/scenario/delete", json={"id": scn_id})
            assert r.status_code == 200, f"删除MS场景失败: {r.text}"
        test("MS场景 CRUD", test_ms_scenario_crud)

        # ═══ 17. MS项目环境 CRUD ═══
        def test_ms_project_env_crud(client):
            name = _unique("MS项目环境")
            r = client.post("/project/environment/add", json={"name": name, "type": "HTTP"})
            assert r.status_code == 200, f"创建MS项目环境失败: {r.text}"
            env_id = _data(r).get("id")
            assert env_id, f"创建MS项目环境未返回ID: {r.text}"
            # Read
            r = client.get(f"/project/environment/get/{env_id}")
            assert r.status_code == 200, f"获取MS项目环境失败: {r.text}"
            # List
            r = client.get("/project/environment/list")
            assert r.status_code == 200, f"列出MS项目环境失败: {r.text}"
            # Update
            r = client.post("/project/environment/update", json={"id": env_id, "name": name + "-改"})
            assert r.status_code == 200, f"更新MS项目环境失败: {r.text}"
            # Delete
            r = client.post(f"/project/environment/delete/{env_id}")
            assert r.status_code == 200, f"删除MS项目环境失败: {r.text}"
        test("MS项目环境 CRUD", test_ms_project_env_crud)

        # ═══ 18. 用例评审 CRUD ═══
        def test_ms_review_crud(client):
            name = _unique("用例评审")
            r = client.post("/case/review/add", json={"name": name})
            assert r.status_code == 200, f"创建用例评审失败: {r.text}"
            review_id = _data(r).get("id")
            assert review_id, f"创建用例评审未返回ID: {r.text}"
            # Read
            r = client.get(f"/case/review/detail/{review_id}")
            assert r.status_code == 200, f"获取用例评审失败: {r.text}"
            # List
            r = client.post("/case/review/page", json={"pageSize": 100, "current": 1})
            assert r.status_code == 200, f"列出用例评审失败: {r.text}"
            # Update
            r = client.post("/case/review/edit", json={"id": review_id, "name": name + "-改"})
            assert r.status_code == 200, f"更新用例评审失败: {r.text}"
            # Delete
            r = client.post("/case/review/delete", json={"id": review_id})
            assert r.status_code == 200, f"删除用例评审失败: {r.text}"
        test("用例评审 CRUD", test_ms_review_crud)

        # ═══ 19. 测试计划 CRUD ═══
        def test_ms_test_plan_crud(client):
            name = _unique("测试计划")
            r = client.post("/test-plan/add", json={"name": name, "description": "CRUD测试"})
            assert r.status_code == 200, f"创建测试计划失败: {r.text}"
            plan_id = _data(r).get("id")
            assert plan_id, f"创建测试计划未返回ID: {r.text}"
            # Read via GET /test-plan?id=
            r = client.get(f"/test-plan?id={plan_id}")
            assert r.status_code == 200, f"获取测试计划失败: {r.text}"
            # List via page
            r = client.post("/test-plan/page", json={"pageSize": 100, "current": 1})
            assert r.status_code == 200, f"列出测试计划失败: {r.text}"
            # Update
            r = client.post("/test-plan/update", json={"id": plan_id, "name": name + "-改"})
            assert r.status_code == 200, f"更新测试计划失败: {r.text}"
            # Delete
            r = client.post("/test-plan/delete", json={"id": plan_id})
            assert r.status_code == 200, f"删除测试计划失败: {r.text}"
        test("测试计划 CRUD", test_ms_test_plan_crud)

        # ═══ 20. MS缺陷 CRUD ═══
        def test_ms_bug_crud(client):
            title = _unique("MS缺陷")
            r = client.post("/bug/add", json={"title": title, "severity": "P1"})
            assert r.status_code == 200, f"创建MS缺陷失败: {r.text}"
            bug_id = _data(r).get("id")
            assert bug_id, f"创建MS缺陷未返回ID: {r.text}"
            # Read
            r = client.get(f"/bug/get/{bug_id}")
            assert r.status_code == 200, f"获取MS缺陷失败: {r.text}"
            # List
            r = client.post("/bug/page", json={"pageSize": 100, "current": 1})
            assert r.status_code == 200, f"列出MS缺陷失败: {r.text}"
            # Update
            r = client.post("/bug/update", json={"id": bug_id, "title": title + "-改"})
            assert r.status_code == 200, f"更新MS缺陷失败: {r.text}"
            # Delete
            r = client.post("/bug/delete", json={"id": bug_id})
            assert r.status_code == 200, f"删除MS缺陷失败: {r.text}"
        test("MS缺陷 CRUD", test_ms_bug_crud)

        # ═══ 21. 功能用例模块 CRUD ═══
        def test_case_module_crud(client):
            name = _unique("功能模块")
            r = client.post("/functional/case/module/add", json={"name": name, "parentId": "root"})
            assert r.status_code == 200, f"创建功能模块失败: {r.text}"
            module_id = _data(r).get("id")
            assert module_id, f"创建功能模块未返回ID: {r.text}"
            # List/Tree
            r = client.get("/functional/case/module/tree")
            assert r.status_code == 200, f"查询模块树失败: {r.text}"
            # Update
            r = client.post("/functional/case/module/update", json={"id": module_id, "name": name + "-改"})
            assert r.status_code == 200, f"更新功能模块失败: {r.text}"
            # Delete
            r = client.post(f"/functional/case/module/delete/{module_id}")
            assert r.status_code == 200, f"删除功能模块失败: {r.text}"
        test("功能用例模块 CRUD", test_case_module_crud)

        # ═══ 22. 全局参数 CRUD ═══
        def test_global_params_crud(client):
            project_id = _unique("项目ID")
            # Create/Save
            r = client.post("/project/global/params/add", json={
                "projectId": project_id,
                "globalParams": {"headers": [], "commonVariables": []}
            })
            assert r.status_code == 200, f"保存全局参数失败: {r.text}"
            # Get
            r = client.get(f"/project/global/params/get?projectId={project_id}")
            assert r.status_code == 200, f"获取全局参数失败: {r.text}"
            # Update
            r = client.post("/project/global/params/update", json={
                "projectId": project_id,
                "globalParams": {"headers": [{"name": "X-Test", "value": "123"}], "commonVariables": []}
            })
            assert r.status_code == 200, f"更新全局参数失败: {r.text}"
            # Delete
            r = client.post("/project/global/params/delete", json={"projectId": project_id})
            assert r.status_code == 200, f"删除全局参数失败: {r.text}"
        test("全局参数 CRUD", test_global_params_crud)

        # ═══ 23. 用例回收站 CRUD ═══
        def test_case_trash_crud(client):
            name = _unique("回收站用例")
            r = client.post("/api/cases", json={"title": name})
            case_id = _data(r).get("id") or r.json().get("id")
            # Soft delete (no body)
            r = client.post(f"/api/cases/{case_id}/trash")
            assert r.status_code == 200, f"软删除用例失败: {r.text}"
            # Check trash list
            r = client.get("/api/cases/trash")
            assert r.status_code == 200, f"查询回收站失败: {r.text}"
            trash = _data(r).get("trash", [])
            found = [t for t in trash if t.get("case_id") == case_id]
            assert found, "回收站中未找到已删除用例"
            # Restore
            r = client.post(f"/api/cases/{case_id}/restore")
            assert r.status_code == 200, f"恢复用例失败: {r.text}"
            # Check it's back
            r = client.get(f"/api/cases/{case_id}")
            assert r.status_code == 200, "恢复后无法获取用例"
            # Clean up
            client.delete(f"/api/cases/{case_id}")
        test("用例回收站 CRUD", test_case_trash_crud)

        # ═══ 24. 用例关联 CRUD ═══
        def test_case_relations_crud(client):
            r = client.post("/api/cases", json={"title": _unique("关联用例")})
            case_id = _data(r).get("id") or r.json().get("id")
            r = client.post("/api/cases", json={"title": _unique("关联目标")})
            related_id = _data(r).get("id") or r.json().get("id")
            # Add relation
            r = client.post(f"/api/cases/{case_id}/relations", json={
                "related_case_id": related_id, "relation_type": "related"
            })
            assert r.status_code == 200, f"添加关联失败: {r.text}"
            # List relations
            r = client.get(f"/api/cases/{case_id}/relations")
            assert r.status_code == 200, f"查询关联失败: {r.text}"
            # Delete relation
            r = client.delete(f"/api/cases/{case_id}/relations/{related_id}")
            assert r.status_code == 200, f"删除关联失败: {r.text}"
            # Cleanup
            client.delete(f"/api/cases/{case_id}")
            client.delete(f"/api/cases/{related_id}")
        test("用例关联 CRUD", test_case_relations_crud)

        # ═══ 25. 用例评审流程 ═══
        def test_case_review_flow(client):
            r = client.post("/api/cases", json={"title": _unique("评审用例")})
            case_id = _data(r).get("id") or r.json().get("id")
            r = client.post(f"/api/cases/{case_id}/reviews/submit", json={"comment": "请评审"})
            assert r.status_code == 200, f"提交评审失败: {r.text}"
            r = client.get(f"/api/cases/{case_id}/reviews")
            assert r.status_code == 200, f"查询评审失败: {r.text}"
            r = client.post(f"/api/cases/{case_id}/reviews/approve", json={"comment": "通过"})
            assert r.status_code == 200, f"通过评审失败: {r.text}"
            client.delete(f"/api/cases/{case_id}")
        test("用例评审流程", test_case_review_flow)

        # ═══ 26. 用例版本管理 ═══
        def test_case_versions(client):
            r = client.post("/api/cases", json={"title": _unique("版本用例"), "description": "v1"})
            case_id = _data(r).get("id") or r.json().get("id")
            r = client.put(f"/api/cases/{case_id}", json={"description": "v2"})
            assert r.status_code == 200, f"更新用例失败: {r.text}"
            r = client.get(f"/api/cases/{case_id}/versions")
            assert r.status_code == 200, f"查询版本失败: {r.text}"
            client.delete(f"/api/cases/{case_id}")
        test("用例版本管理", test_case_versions)

        # ═══ 27. 报告生成 ═══
        def test_report_generate(client):
            for i in range(3):
                client.post("/api/cases", json={"title": _unique(f"报告用例{i}")})
            r = client.post("/api/reports/generate", json={"format": "html"})
            if r.status_code == 200:
                data = _data(r)
                assert "report_path" in data or "path" in data, f"报告生成失败: {r.text}"
            elif r.status_code != 404:
                raise AssertionError(f"生成报告失败: {r.status_code} {r.text}")
        test("报告生成", test_report_generate)

        # ═══ 28. apitest 模块 CRUD ═══
        def test_apitest_module_crud(client):
            name = _unique("API模块")
            r = client.post("/api/apitest/modules/definition/add", json={"name": name})
            assert r.status_code == 200, f"创建API模块失败: {r.text}"
            module_id = _data(r).get("id")
            assert module_id, f"创建API模块未返回ID: {r.text}"
            r = client.get("/api/apitest/modules/definition")
            assert r.status_code == 200, f"查询API模块列表失败: {r.text}"
            r = client.post("/api/apitest/modules/definition/update", json={"id": module_id, "name": name + "-改"})
            assert r.status_code == 200, f"更新API模块失败: {r.text}"
            r = client.post("/api/apitest/modules/definition/delete", json={"id": module_id})
            assert r.status_code == 200, f"删除API模块失败: {r.text}"
        test("apitest 模块 CRUD", test_apitest_module_crud)

        # ═══ 29. 用例依赖 CRUD ═══
        def test_case_dependencies(client):
            r = client.post("/api/cases", json={"title": _unique("依赖用例")})
            case_id = _data(r).get("id") or r.json().get("id")
            r = client.post("/api/cases", json={"title": _unique("依赖目标")})
            dep_id = _data(r).get("id") or r.json().get("id")
            r = client.post(f"/api/cases/{case_id}/dependencies", json={"depends_on": dep_id})
            assert r.status_code == 200, f"添加依赖失败: {r.text}"
            r = client.get(f"/api/cases/{case_id}/dependencies")
            assert r.status_code == 200, f"查询依赖失败: {r.text}"
            r = client.delete(f"/api/cases/{case_id}/dependencies/{dep_id}")
            assert r.status_code == 200, f"删除依赖失败: {r.text}"
            client.delete(f"/api/cases/{case_id}")
            client.delete(f"/api/cases/{dep_id}")
        test("用例依赖 CRUD", test_case_dependencies)

        # ═══ 30. 自定义函数 CRUD ═══
        def test_custom_func_crud(client):
            name = _unique("自定义函数")
            r = client.post("/project/custom/func/add", json={
                "name": name, "script": "function test() { return 1; }", "type": "HTTP"
            })
            assert r.status_code == 200, f"创建自定义函数失败: {r.text}"
            func_id = _data(r).get("id")
            assert func_id, f"创建自定义函数未返回ID: {r.text}"
            r = client.get(f"/project/custom/func/detail/{func_id}")
            assert r.status_code == 200, f"获取自定义函数失败: {r.text}"
            r = client.post(f"/project/custom/func/delete/{func_id}")
            assert r.status_code == 200, f"删除自定义函数失败: {r.text}"
        test("自定义函数 CRUD", test_custom_func_crud)

        print("\n" + "="*60)
        print(f"共 {len(results)} 项测试，{len(failures)} 项失败")
        if failures:
            print("\n失败详情:")
            for module, err in failures:
                print(f"  ❌ {module}: {err}")
        else:
            print("🎉 所有功能模块 CRUD 测试全部通过！")

        return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
