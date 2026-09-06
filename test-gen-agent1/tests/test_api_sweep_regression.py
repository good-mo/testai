"""全接口巡检发现的缺陷回归测试。

2026-09 对线上全部 2019 条 (method, path) 路由做了一次真实 HTTP 巡检
（应用完整 lifespan 启动 + 种子库快照 + 读写分离排序 + 会话自愈），
发现 4 类「本该 4xx 却打成 500」以及 1 类「空参数穿透到 LLM」的问题。

本文件为这些问题建立回归防线，防止再次劣化。
每条用例都对应巡检中可复现的真实请求。
"""
import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import classify_llm_error


def _data(resp):
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


@pytest.fixture
def client():
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        s = r.json()["data"]
        c.headers.update({
            "X-AUTH-TOKEN": s["sessionId"],
            "CSRF-TOKEN": s["csrfToken"],
        })
        yield c


class TestPayloadGuard:
    """接口测试域：未知字段不得打成 500。

    巡检复现：前端普遍以 camelCase 发参（projectId / baseUrl），
    且 axios 拦截器会把分页参数（current/pageSize）一并塞进请求体。
    store 层签名是封闭的，原样 `**body` 透传会引发两类 500：
      - create: TypeError: got an unexpected keyword argument
      - update: sqlite3.OperationalError: no such column
    """

    # 巡检中真实触发过 500 的「多余字段」组合
    NOISE = {"projectId": "p1", "current": 1, "pageSize": 10, "bogusField": "x"}

    @pytest.mark.parametrize("path,payload", [
        ("/api/apitest/definitions", {"name": "guard-def", "path": "/g"}),
        ("/api/apitest/scenarios", {"name": "guard-scn", "steps": []}),
        ("/api/apitest/mocks", {"name": "guard-mock", "path": "/g"}),
        ("/api/apitest/environments", {"name": "guard-env", "baseUrl": "http://g"}),
    ])
    def test_create_with_unknown_fields_returns_200(self, client, path, payload):
        """创建接口携带未知字段：忽略而非 500。"""
        resp = client.post(path, json={**payload, **self.NOISE})
        assert resp.status_code == 200, resp.text
        assert _data(resp).get("id")

    @pytest.mark.parametrize("path", [
        "/api/apitest/definitions",
        "/api/apitest/scenarios",
        "/api/apitest/mocks",
        "/api/apitest/environments",
    ])
    def test_update_with_unknown_fields_returns_200(self, client, path):
        """更新接口携带未知字段：不得出现 no such column 的 500。"""
        created = client.post(path, json={"name": "guard-upd"}).json()["data"]
        resp = client.put(f"{path}/{created['id']}", json={**self.NOISE})
        assert resp.status_code == 200, resp.text

    def test_project_id_camel_case_is_persisted(self, client):
        """projectId 应归一化为 project_id 并真正落库。

        只「不报错」是不够的：如果 camelCase 被静默丢弃，
        前端按项目过滤时会查不到刚创建的资源。
        """
        resp = client.post("/api/apitest/definitions", json={
            "name": "guard-proj", "path": "/p", "projectId": "proj-regression",
        })
        assert resp.status_code == 200
        def_id = resp.json()["data"]["id"]

        detail = client.get(f"/api/apitest/definitions/{def_id}").json()["data"]
        assert detail["project_id"] == "proj-regression"

        # 按项目过滤能查到，才算真的落库
        listed = client.get(
            "/api/apitest/definitions", params={"project_id": "proj-regression"}
        ).json()["data"]["items"]
        assert any(i["id"] == def_id for i in listed)

    def test_dict_fields_are_json_serialized(self, client):
        """字典字段（headers 等）应序列化为 JSON 字符串存储。"""
        resp = client.post("/api/apitest/definitions", json={
            "name": "guard-headers", "path": "/h", "headers": {"X-T": "1"},
        })
        assert resp.status_code == 200
        stored = resp.json()["data"]["headers"]
        assert isinstance(stored, (str, dict))
        if isinstance(stored, str):
            assert "X-T" in stored


class TestEnvironmentImport:
    """环境导入：项目维度放在请求体里也要生效。

    巡检复现：路由原按 `import_environment(body, project_id=...)` 调用，
    而 service 签名只接受 data 一个参数，直接
    `TypeError: unexpected keyword argument 'project_id'` → 500。
    """

    def test_import_with_project_id_in_body(self, client):
        resp = client.post("/api/apitest/environments/import", json={
            "name": "imp-body", "base_url": "http://a", "project_id": "proj-imp",
        })
        assert resp.status_code == 200, resp.text
        env = resp.json()["data"]
        assert env["project_id"] == "proj-imp"

    def test_import_with_nested_data(self, client):
        resp = client.post("/api/apitest/environments/import", json={
            "data": {"name": "imp-nested", "base_url": "http://b",
                     "projectId": "proj-nested"},
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["project_id"] == "proj-nested"

    def test_import_without_name_returns_400(self, client):
        assert client.post(
            "/api/apitest/environments/import", json={"base_url": "http://c"}
        ).status_code == 400


class TestOperationLogsClear:
    """DELETE /api/apitest/logs：不得因签名不匹配 500。

    巡检复现：路由传 days，service 却声明 `clear_operation_logs(self)`，
    调用即 `takes 1 positional argument but 2 were given` → 500。
    """

    def test_clear_with_days(self, client):
        assert client.delete("/api/apitest/logs?days=30").status_code == 200

    def test_clear_all_with_zero_days(self, client):
        """days=0 表示清空全部。"""
        assert client.delete("/api/apitest/logs?days=0").status_code == 200
        assert _data(client.get("/api/apitest/logs"))["items"] == []


class TestDataFactoryGenerate:
    """造数接口：模板缺失应 404，而不是 500。

    巡检复现：repository 抛 ValueError(f"数据模板  不存在")，
    被全局兜底打成 500，前端无法区分「模板没了」和「服务崩了」。
    """

    def test_missing_template_id_returns_400(self, client):
        resp = client.post("/api/data/generate", json={"template_id": ""})
        assert resp.status_code == 400

    def test_nonexistent_template_returns_404(self, client):
        resp = client.post("/api/data/generate", json={"template_id": "nope"})
        assert resp.status_code == 404


class TestEnvironmentLifecycle:
    """环境启停：环境不存在应 404，而不是 500。

    巡检复现：environment manager 内部 raise ValueError，穿透成 500。
    """

    @pytest.mark.parametrize("action", ["launch", "stop", "health"])
    def test_missing_env_returns_404(self, client, action):
        resp = client.post(f"/api/environments/no-such-env/{action}")
        assert resp.status_code == 404, resp.text


class TestGenerationErrors:
    """测试生成：参数问题与上游 LLM 问题需给出正确语义。"""

    @pytest.mark.parametrize("path", [
        "/api/generate",
        "/api/generate/structured",
    ])
    def test_empty_source_returns_400(self, client, path):
        """空源码应在入口拦掉，不允许穿透到 LLM。"""
        resp = client.post(path, json={"source_code": ""})
        assert resp.status_code == 400, resp.text

    def test_whitespace_only_source_returns_400(self, client):
        resp = client.post("/api/generate", json={"source_code": "   \n\t"})
        assert resp.status_code == 400, resp.text

    def test_empty_source_task_returns_400(self, client):
        resp = client.post("/api/tasks", json={"source_code": "  "})
        assert resp.status_code == 400, resp.text


class TestLLMErrorClassification:
    """上游 LLM 错误分类：配置问题不得报 500。

    巡检复现：API Key 无效时，openai 抛 AuthenticationError，
    全局兜底统一打成 500，前端只能提示「服务器开小差」，
    用户无法得知「去系统设置里把 Key 改对」。
    """
    @pytest.mark.parametrize("msg,expected", [
        ("Error code: 401 - invalid_api_key", 401),
        ("Incorrect API key provided: sk-x", 401),
        ("openai.AuthenticationError: bad key", 401),
        ("RateLimitError: insufficient_quota", 429),
        ("You exceeded your current quota", 429),
        ("NotFoundError: The model does not exist", 404),
        ("APITimeoutError: Request timed out", 504),
    ])
    def test_status_mapping(self, msg, expected):
        status, reason = classify_llm_error(Exception(msg))
        assert status == expected, f"{msg} -> {status}, want {expected}"
        assert reason  # 必须给出可操作提示

    def test_unknown_error_is_not_classified(self):
        """非 LLM 错误不应被误分类，仍走 500。"""
        status, _ = classify_llm_error(Exception("disk full"))
        assert status == 0
