"""
test_structured_cases.py — 结构化测试用例（方案A）测试

覆盖:
  - 功能: JSON 数组提取函数
  - 功能: 结构化用例数据模型
  - 功能: API 支持 structured_cases 字段
  - 功能: 用例库结构化字段存取
"""
import pytest

from app.generators.test_generator import _extract_code, _extract_json_array, _parse_test_type


def _data(resp):
    """统一解析 {code, message, data} 响应，返回 data 层。"""
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


class TestJsonArrayExtraction:
    """JSON 数组提取测试"""

    def test_direct_json(self):
        """功能: 直接解析纯 JSON 数组"""
        text = '[{"title": "test", "test_steps": []}]'
        result = _extract_json_array(text)
        assert isinstance(result, list)
        assert result[0]["title"] == "test"

    def test_markdown_fenced_json(self):
        """功能: 解析 markdown 代码块包裹的 JSON"""
        text = '```json\n[{"title": "test", "priority": "P1"}]\n```'
        result = _extract_json_array(text)
        assert isinstance(result, list)
        assert result[0]["priority"] == "P1"

    def test_embedded_json_in_text(self):
        """功能: 从文本中提取 JSON 数组"""
        text = '这里是说明\n[{"title": "test"}]\n请查看'
        result = _extract_json_array(text)
        assert isinstance(result, list)
        assert result[0]["title"] == "test"

    def test_invalid_json_raises(self):
        """边界: 无法解析 JSON 时抛出 ValueError"""
        with pytest.raises(ValueError):
            _extract_json_array("这不是 JSON")


class TestCodeExtraction:
    """代码提取测试"""

    def test_python_fenced_code(self):
        """功能: 提取 python 代码块"""
        text = '```python\ndef test_x():\n    pass\n```'
        result = _extract_code(text)
        assert "def test_x()" in result

    def test_plain_text_returns_as_is(self):
        """边界: 无代码块时原样返回"""
        text = "def test_x():\n    pass"
        result = _extract_code(text)
        assert result == text


class TestParseTestType:
    """测试类型解析测试"""

    def test_valid_type_passthrough(self):
        """功能: 合法类型原样返回"""
        assert _parse_test_type("api") == "api"
        assert _parse_test_type("security") == "security"

    def test_invalid_type_falls_back(self):
        """边界: 非法类型回退到 functional"""
        assert _parse_test_type("invalid") == "functional"




def _data(resp):
    """解析响应，统一取 data 层。"""
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


class TestStructuredCaseAPI:
    """结构化用例 API 测试"""

    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient

        from app.main import app

        c = TestClient(app)
        # 登录获取认证令牌
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        if r.status_code == 200:
            session = r.json()["data"]
            c.headers.update({
                "X-AUTH-TOKEN": session["sessionId"],
                "CSRF-TOKEN": session["csrfToken"],
            })
        return c

    def test_create_case_with_structured_cases(self, client):
        """功能: 创建用例时可指定 structured_cases"""
        structured = [
            {
                "title": "测试用例1",
                "description": "测试功能",
                "preconditions": ["系统可用"],
                "test_steps": [
                    {"step": "输入参数", "data": "1,2", "expected": "返回3"}
                ],
                "test_data": {"a": 1, "b": 2},
                "priority": "P1",
                "risk_level": "low",
                "execution_type": "manual"
            }
        ]
        resp = client.post("/api/cases", json={
            "title": "structured_case_test",
            "source_code": "def add(a, b): return a + b",
            "test_code": "def test_add(): assert add(1, 2) == 3",
            "file_path": "structured_demo.py",
            "status": "review",
            "test_type": "functional",
            "structured_cases": structured,
        })
        assert resp.status_code == 200
        data = _data(resp)
        assert data.get("test_type") == "functional"
        assert data.get("structured_cases")
        assert data["structured_cases"][0]["title"] == "测试用例1"
        assert data["structured_cases"][0]["test_steps"][0]["expected"] == "返回3"

        # 清理
        client.delete(f"/api/cases/{data['id']}")

    def test_get_case_returns_structured_cases(self, client):
        """功能: 获取用例时返回 structured_cases"""
        structured = [{
            "title": "用例",
            "test_steps": [{"step": "操作", "expected": "结果"}]
        }]
        resp = client.post("/api/cases", json={
            "title": "get_structured_test",
            "source_code": "def x(): pass",
            "file_path": "get_structured.py",
            "status": "draft",
            "structured_cases": structured,
        })
        assert resp.status_code == 200
        case_id = _data(resp)["id"]

        try:
            resp = client.get(f"/api/cases/{case_id}")
            assert resp.status_code == 200
            data = _data(resp)
            assert len(data["structured_cases"]) == 1
            assert data["structured_cases"][0]["title"] == "用例"
        finally:
            client.delete(f"/api/cases/{case_id}")

    def test_update_case_structured_cases(self, client):
        """功能: 更新用例的 structured_cases"""
        resp = client.post("/api/cases", json={
            "title": "update_structured_test",
            "source_code": "def y(): pass",
            "file_path": "update_structured.py",
            "status": "draft",
        })
        assert resp.status_code == 200
        case_id = _data(resp)["id"]

        try:
            new_structured = [{
                "title": "更新后的用例",
                "preconditions": ["新前置"],
                "test_steps": [{"step": "新步骤", "expected": "新预期"}]
            }]
            resp = client.put(f"/api/cases/{case_id}", json={
                "structured_cases": new_structured,
            })
            assert resp.status_code == 200
            data = _data(resp)
            assert data["structured_cases"][0]["title"] == "更新后的用例"
            assert data["structured_cases"][0]["preconditions"] == ["新前置"]
        finally:
            client.delete(f"/api/cases/{case_id}")

    def test_generate_script_flag_in_request(self):
        """功能: ChatRequest 支持 generate_script 字段"""
        from app.models.schemas import ChatRequest
        req = ChatRequest(source_code="def a(): pass", generate_script=False)
        assert req.generate_script is False

        req2 = ChatRequest(source_code="def b(): pass")
        assert req2.generate_script is True


class TestPytestCountParser:
    """pytest 输出用例计数解析（run_tests 新增字段）。"""

    def test_parse_basic_passed(self):
        """功能: 解析简单的 'N passed' 输出"""
        from app.runners.subprocess_runner import _parse_pytest_counts
        result = _parse_pytest_counts("2 passed in 0.01s")
        assert result["passed"] == 2
        assert result["failed"] == 0
        assert result["error"] == 0

    def test_parse_mixed_failed_passed(self):
        """功能: 解析混合 'failed + passed' 输出"""
        from app.runners.subprocess_runner import _parse_pytest_counts
        result = _parse_pytest_counts("1 failed, 2 passed in 0.05s")
        assert result["passed"] == 2
        assert result["failed"] == 1
        assert result["error"] == 0

    def test_parse_errors(self):
        """功能: 解析 error 计数"""
        from app.runners.subprocess_runner import _parse_pytest_counts
        result = _parse_pytest_counts("5 errors in 0.2s")
        assert result["passed"] == 0
        assert result["failed"] == 0
        assert result["error"] == 5

    def test_parse_empty(self):
        """边界: 无计数信息时返回 0"""
        from app.runners.subprocess_runner import _parse_pytest_counts
        result = _parse_pytest_counts("no tests ran")
        assert result == {"passed": 0, "failed": 0, "error": 0}

    def test_parse_multiline_output(self):
        """功能: 从完整 pytest stdout 中解析计数"""
        from app.runners.subprocess_runner import _parse_pytest_counts
        output = "test_module.py::test_a PASSED\n" \
                 "test_module.py::test_b FAILED\n" \
                 "test_module.py::test_c PASSED\n\n" \
                 "=== FAILURES ===\n..." \
                 "1 failed, 2 passed in 0.05s"
        result = _parse_pytest_counts(output)
        assert result["passed"] == 2
        assert result["failed"] == 1


class TestAICaseGenDataContract:
    """AI 用例生成页面数据契约（前后端字段对齐）。"""

    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient

        from app.main import app
        c = TestClient(app)
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        if r.status_code == 200:
            session = r.json()["data"]
            c.headers.update({
                "X-AUTH-TOKEN": session["sessionId"],
                "CSRF-TOKEN": session["csrfToken"],
            })
        return c

    def test_lowcode_returns_generated_test_field(self, client):
        """契约: 低代码生成返回 generated_test 字段（前端读取 generated_test 而非 generated_tests）"""
        resp = client.post("/api/insights/lowcode", json={
            "description": "生成一个登录接口的测试"
        })
        assert resp.status_code == 200
        data = _data(resp)
        # 前端 lowcode.vue 读取 res?.generated_test
        assert "generated_test" in data, "缺少 generated_test 字段"
        assert data["generated_test"], "generated_test 不能为空"
        # 不依赖已废弃的 generated_tests（复数）
        assert "generated_tests" not in data or not data.get("generated_tests")

    def test_lowcode_frontend_field_access_contract(self, client):
        """契约: 验证前端可读取的字段顺序（generated_test 应在第一个位置）"""
        resp = client.post("/api/insights/lowcode", json={
            "description": "测试用户注册功能"
        })
        assert resp.status_code == 200
        data = _data(resp)
        # 前端处理: generated.value = res?.generated_test || res?.code || res?.generated_tests || ...
        assert "generated_test" in data
        # 兼容检查：如果同时存在 generated_tests，也应该指向可运行代码
        if "generated_tests" in data:
            assert data["generated_tests"]

    def test_project_scan_returns_expected_shape(self, client):
        """契约: 项目扫描返回 files 数组且每项含 relative_path/size/signatures"""
        resp = client.post("/api/projects/scan", json={
            "project_path": "/workspace/examples"
        })
        assert resp.status_code == 200
        data = _data(resp)
        assert "files" in data
        assert "total_files" in data
        assert data["total_files"] >= 1
        f = data["files"][0]
        # 前端 project.vue 读取这些字段
        for key in ("relative_path", "size", "signatures", "path"):
            assert key in f, f"文件缺少字段: {key}"
        # 前端读取 record.signatures?.length
        assert isinstance(f["signatures"], list)

    def test_lowcode_empty_desc_returns_400(self, client):
        """边界: 低代码生成空描述返回 400"""
        resp = client.post("/api/insights/lowcode", json={"description": ""})
        assert resp.status_code == 400
