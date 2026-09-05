"""
测试所有创建接口并验证记录在页面(列表)上显示
============================================
通过调用各业务模块的创建接口，创建记录后通过对应的列表接口
验证记录确实在页面(列表)上可见，确保前后端数据一致。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest
from fastapi.testclient import TestClient

PREFIX = "PAGE-VERIFY-"

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

@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, f"登录失败: {r.text}"
        session = r.json()["data"]
        c.headers.update({
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        })
        yield c


def _find_in_list(items, name):
    """在列表中查找指定名称的记录。"""
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, dict):
            continue
        for k in ["name", "title"]:
            if item.get(k) == name:
                return item
    return None


def _find_in_tree(nodes, target_name):
    """在树结构中递归查找指定名称的节点。"""
    if not nodes:
        return None
    if not isinstance(nodes, list):
        nodes = [nodes]
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("name") == target_name:
            return node
        children = node.get("children", [])
        if children:
            found = _find_in_tree(children, target_name)
            if found:
                return found
    return None


# ════════════════════════════════════════════════════════════
# 1. 功能用例 创建 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestFunctionalCaseCreatePage:
    """功能用例创建 + 页面显示验证"""

    def test_create_case_and_verify_in_page(self, client):
        """创建功能用例，验证在列表页中可见"""
        name = _unique("功能用例")
        r = client.post("/functional/case/add", json={
            "name": name,
            "priority": "P1",
            "type": "功能测试",
            "description": "页面验证-功能用例",
            "tags": ["页面验证"],
        })
        assert r.status_code == 200, f"创建失败: {r.text}"
        case_id = _data(r).get("id")
        assert case_id, f"创建未返回ID: {r.text}"

        # 通过列表页 API 验证
        r = client.post("/functional/case/page", json={
            "pageSize": 100, "current": 1,
        })
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        items = _data(r).get("list", [])
        found = _find_in_list(items, name)
        assert found, f"创建的用例 '{name}' 未在列表页中显示!"
        assert found.get("id") == case_id, "列表中的ID与创建返回的ID不一致"


# ════════════════════════════════════════════════════════════
# 2. 接口定义 创建 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestApiDefinitionCreatePage:
    """接口定义创建 + 页面显示验证"""

    def test_create_definition_and_verify_in_page(self, client):
        """创建接口定义，验证在列表页中可见"""
        name = _unique("接口定义")
        path = f"/page-verify/{uuid.uuid4().hex[:8]}"
        r = client.post("/api/definition/add", json={
            "name": name,
            "method": "GET",
            "path": path,
            "protocol": "HTTP",
            "description": "页面验证-接口定义",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"
        def_id = _data(r).get("id")
        assert def_id, f"创建未返回ID: {r.text}"

        # 通过列表页 API 验证
        r = client.post("/api/definition/page", json={
            "pageSize": 100, "current": 1,
        })
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        items = _data(r).get("list", [])
        found = _find_in_list(items, name)
        assert found, f"创建的接口定义 '{name}' 未在列表页中显示!"
        assert found.get("id") == def_id, "列表中的ID与创建返回的ID不一致"


# ════════════════════════════════════════════════════════════
# 3. 接口用例 创建 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestApiCaseCreatePage:
    """接口用例创建 + 页面显示验证"""

    def test_create_api_case_and_verify_in_page(self, client):
        """创建接口用例，验证在列表页中可见"""
        name = _unique("接口用例")
        r = client.post("/api/case/add", json={
            "name": name,
            "method": "GET",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"
        case_id = _data(r).get("id")
        assert case_id, f"创建未返回ID: {r.text}"

        # 通过列表页 API 验证
        r = client.post("/api/case/page", json={
            "pageSize": 100, "current": 1,
        })
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        items = _data(r).get("list", [])
        found = _find_in_list(items, name)
        assert found, f"创建的接口用例 '{name}' 未在列表页中显示!"
        assert found.get("id") == case_id, "列表中的ID与创建返回的ID不一致"


# ════════════════════════════════════════════════════════════
# 4. 接口场景 创建 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestApiScenarioCreatePage:
    """接口场景创建 + 页面显示验证"""

    def test_create_scenario_and_verify_in_page(self, client):
        """创建接口场景，验证在列表页中可见"""
        name = _unique("接口场景")
        r = client.post("/api/scenario/add", json={"name": name})
        assert r.status_code == 200, f"创建失败: {r.text}"
        scn_id = _data(r).get("id")
        assert scn_id, f"创建未返回ID: {r.text}"

        # 通过列表页 API 验证
        r = client.post("/api/scenario/page", json={
            "pageSize": 100, "current": 1,
        })
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        items = _data(r).get("list", [])
        found = _find_in_list(items, name)
        assert found, f"创建的接口场景 '{name}' 未在列表页中显示!"
        assert found.get("id") == scn_id, "列表中的ID与创建返回的ID不一致"


# ════════════════════════════════════════════════════════════
# 5. 用例评审 创建 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestReviewCreatePage:
    """用例评审创建 + 页面显示验证"""

    def test_create_review_and_verify_in_page(self, client):
        """创建用例评审，验证在列表页中可见"""
        name = _unique("用例评审")
        r = client.post("/case/review/add", json={"name": name})
        assert r.status_code == 200, f"创建失败: {r.text}"
        review_id = _data(r).get("id")
        assert review_id, f"创建未返回ID: {r.text}"

        # 通过列表页 API 验证
        r = client.post("/case/review/page", json={
            "pageSize": 100, "current": 1,
        })
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        items = _data(r).get("list", [])
        found = _find_in_list(items, name)
        assert found, f"创建的用例评审 '{name}' 未在列表页中显示!"
        assert found.get("id") == review_id, "列表中的ID与创建返回的ID不一致"


# ════════════════════════════════════════════════════════════
# 6. 缺陷 创建 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestBugCreatePage:
    """缺陷创建 + 页面显示验证"""

    def test_create_bug_and_verify_in_page(self, client):
        """创建缺陷，验证在列表页中可见"""
        title = _unique("缺陷")
        r = client.post("/bug/add", json={
            "title": title,
            "severity": "P1",
            "status": "open",
            "description": "页面验证-缺陷",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"
        bug_id = _data(r).get("id")
        assert bug_id, f"创建未返回ID: {r.text}"

        # 通过列表页 API 验证
        r = client.post("/bug/page", json={
            "pageSize": 100, "current": 1,
        })
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        items = _data(r).get("list", [])
        found = _find_in_list(items, title)
        assert found, f"创建的缺陷 '{title}' 未在列表页中显示!"
        assert found.get("id") == bug_id, "列表中的ID与创建返回的ID不一致"


# ════════════════════════════════════════════════════════════
# 7. 测试计划 创建 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestTestPlanCreatePage:
    """测试计划创建 + 页面显示验证"""

    def test_create_plan_and_verify_in_page(self, client):
        """创建测试计划，验证在列表页中可见"""
        name = _unique("测试计划")
        r = client.post("/test-plan/add", json={
            "name": name,
            "description": "页面验证-测试计划",
            "priority": "P1",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"
        plan_id = _data(r).get("id")
        assert plan_id, f"创建未返回ID: {r.text}"

        # 通过列表页 API 验证
        r = client.post("/test-plan/page", json={
            "pageSize": 100, "current": 1,
        })
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        items = _data(r).get("list", [])
        found = _find_in_list(items, name)
        assert found, f"创建的测试计划 '{name}' 未在列表页中显示!"
        assert found.get("id") == plan_id, "列表中的ID与创建返回的ID不一致"


# ════════════════════════════════════════════════════════════
# 8. 项目环境 创建 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestEnvironmentCreatePage:
    """项目环境创建 + 页面显示验证"""

    def test_create_env_and_verify_in_page(self, client):
        """创建环境，验证在列表页中可见"""
        name = _unique("项目环境")
        r = client.post("/project/environment/add", json={
            "name": name,
            "type": "HTTP",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"

        # 通过列表页 API 验证
        r = client.get("/project/environment/list")
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        data = _data(r)
        if isinstance(data, list):
            found = _find_in_list(data, name)
            assert found, f"创建的环境 '{name}' 未在列表页中显示!"
        elif isinstance(data, dict):
            found = _find_in_list(data.get("list", []), name)
            assert found, f"创建的环境 '{name}' 未在列表页中显示!"


# ════════════════════════════════════════════════════════════
# 9. 全局参数 创建
# ════════════════════════════════════════════════════════════
class TestGlobalParamCreatePage:
    """全局参数创建"""

    def test_create_global_param(self, client):
        """创建全局参数"""
        name = _unique("全局参数")
        r = client.post("/project/global/params/add", json={
            "name": name,
            "paramType": "text",
            "value": "page-verify-value",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"


# ════════════════════════════════════════════════════════════
# 10. 自定义脚本 创建 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestCustomScriptCreatePage:
    """自定义脚本创建 + 页面显示验证"""

    def test_create_custom_script_and_verify_in_page(self, client):
        """创建自定义脚本，验证在列表页中可见"""
        name = _unique("自定义脚本")
        r = client.post("/project/custom/func/add", json={
            "name": name,
            "script": "function test() { return 1; }",
            "type": "HTTP",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"

        # 通过列表页 API 验证
        r = client.get("/project/custom/func/page")
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        data = _data(r)
        items = data.get("list", []) if isinstance(data, dict) else data
        found = _find_in_list(items, name)
        assert found, f"创建的自定义脚本 '{name}' 未在列表页中显示!"


# ════════════════════════════════════════════════════════════
# 11. apitest 环境 创建 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestApiTestEnvCreatePage:
    """apitest 环境创建 + 页面显示验证"""

    def test_create_apitest_env_and_verify_in_page(self, client):
        """创建 apitest 环境，验证在列表页中可见"""
        name = _unique("API环境")
        r = client.post("/api/apitest/environments", json={
            "name": name,
            "base_url": f"https://{uuid.uuid4().hex[:8]}.example.com",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"

        # 通过列表页 API 验证 (返回格式为 {"items": [...]})
        r = client.get("/api/apitest/environments")
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        data = _data(r)
        items = data.get("items", []) if isinstance(data, dict) else data
        found = _find_in_list(items, name)
        assert found, f"创建的 apitest 环境 '{name}' 未在列表页中显示!"


# ════════════════════════════════════════════════════════════
# 12. 功能用例模块 创建 → 模块树显示
# ════════════════════════════════════════════════════════════
class TestCaseModuleCreatePage:
    """功能用例模块创建 + 页面显示验证"""

    def test_create_case_module_and_verify_in_page(self, client):
        """创建功能用例模块，验证在模块树中可见"""
        name = _unique("功能模块")
        r = client.post("/functional/case/module/add", json={
            "name": name, "parentId": "root",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"

        # 通过模块树验证
        r = client.get("/functional/case/module/tree")
        assert r.status_code == 200, f"查询模块树失败: {r.text}"
        tree = _data(r)
        found = _find_in_tree(tree, name)
        assert found, f"创建的模块 '{name}' 未在模块树中显示!"


# ════════════════════════════════════════════════════════════
# 13. 接口定义模块 创建 → 模块树显示
# ════════════════════════════════════════════════════════════
class TestDefinitionModuleCreatePage:
    """接口定义模块创建 + 页面显示验证"""

    def test_create_definition_module_and_verify_in_page(self, client):
        """创建接口定义模块，验证在模块树中可见"""
        name = _unique("定义模块")
        r = client.post("/api/definition/module/add", json={
            "name": name, "parentId": "root",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"

        # 通过模块树验证
        r = client.get("/api/definition/module/tree")
        assert r.status_code == 200, f"查询模块树失败: {r.text}"
        tree = _data(r)
        found = _find_in_tree(tree, name)
        assert found, f"创建的接口定义模块 '{name}' 未在模块树中显示!"


# ════════════════════════════════════════════════════════════
# 14. 接口场景模块 创建 → 模块树显示
# ════════════════════════════════════════════════════════════
class TestScenarioModuleCreatePage:
    """接口场景模块创建 + 页面显示验证"""

    def test_create_scenario_module_and_verify_in_page(self, client):
        """创建接口场景模块，验证在模块树中可见"""
        name = _unique("场景模块")
        r = client.post("/api/scenario/module/add", json={
            "name": name, "parentId": "root",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"

        # 通过模块树验证
        r = client.get("/api/scenario/module/tree")
        assert r.status_code == 200, f"查询模块树失败: {r.text}"
        tree = _data(r)
        found = _find_in_tree(tree, name)
        assert found, f"创建的场景模块 '{name}' 未在模块树中显示!"


# ════════════════════════════════════════════════════════════
# 15. 测试计划模块 创建 → 模块树显示
# ════════════════════════════════════════════════════════════
class TestPlanModuleCreatePage:
    """测试计划模块创建 + 页面显示验证"""

    def test_create_plan_module_and_verify_in_page(self, client):
        """创建测试计划模块，验证在模块树中可见"""
        name = _unique("计划模块")
        r = client.post("/test-plan/module/add", json={
            "name": name, "parentId": "root",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"

        # 通过模块树验证
        r = client.get("/test-plan/module/tree")
        assert r.status_code == 200, f"查询模块树失败: {r.text}"
        tree = _data(r)
        found = _find_in_tree(tree, name)
        assert found, f"创建的测试计划模块 '{name}' 未在模块树中显示!"


# ════════════════════════════════════════════════════════════
# 16. 项目文件模块 创建 → 模块树显示
# ════════════════════════════════════════════════════════════
class TestFileModuleCreatePage:
    """项目文件模块创建 + 页面显示验证"""

    def test_create_file_module_and_verify_in_page(self, client):
        """创建项目文件模块，验证在模块树中可见"""
        name = _unique("文件模块")
        r = client.post("/project/file-module/add", json={
            "name": name, "parentId": "root",
        })
        assert r.status_code == 200, f"创建失败: {r.text}"

        # 通过模块树验证
        r = client.get("/project/file-module/tree")
        assert r.status_code == 200, f"查询模块树失败: {r.text}"
        tree = _data(r)
        found = _find_in_tree(tree, name)
        assert found, f"创建的文件模块 '{name}' 未在模块树中显示!"


# ════════════════════════════════════════════════════════════
# 17. 文件上传 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestFileUploadPage:
    """文件上传 + 列表页显示验证"""

    def test_upload_file_and_verify_in_page(self, client):
        """上传文件，验证在列表页中可见"""
        fname = f"{_unique('文件')}.txt"
        r = client.post("/project/file/upload", files={
            "file": (fname, b"hello page verify", "text/plain"),
        })
        assert r.status_code == 200, f"上传失败: {r.text}"

        # 通过列表页 API 验证
        r = client.post("/project/file/page", json={"pageSize": 100, "current": 1})
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        data = _data(r)
        items = data.get("list", []) if isinstance(data, dict) else data
        found = _find_in_list(items, fname)
        assert found, f"上传的文件 '{fname}' 未在列表页中显示!"


# ════════════════════════════════════════════════════════════
# Mock 服务 创建 → 列表页显示
# ════════════════════════════════════════════════════════════
class TestMockCreatePage:
    """Mock 服务创建 + 页面显示验证"""

    def test_create_mock_and_verify_in_page(self, client):
        """创建 Mock，验证在列表页中可见"""
        name = _unique("Mock服务")
        r = client.post("/api/definition/mock/add", json={
            "name": name,
            "method": "GET",
            "path": f"/mock-page/{uuid.uuid4().hex[:8]}",
            "response_body": '{"success": true}',
            "status_code": 200,
        })
        assert r.status_code == 200, f"创建失败: {r.text}"
        data = _data(r)
        assert data is not None, f"创建未返回数据: {r.text}"
        mock_id = data.get("id")
        assert mock_id, f"创建未返回ID: {r.text}"

        # 通过列表页 API 验证
        r = client.post("/api/definition/mock/page", json={
            "pageSize": 100, "current": 1,
        })
        assert r.status_code == 200, f"查询列表失败: {r.text}"
        items = _data(r).get("list", [])
        found = _find_in_list(items, name)
        assert found, f"创建的 Mock '{name}' 未在列表页中显示!"
        assert found.get("id") == mock_id, "列表中的ID与创建返回的ID不一致"
