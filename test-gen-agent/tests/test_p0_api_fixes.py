"""P0 接口缺陷回归测试。

来源：ISSUE #339 全量接口实测。锁死四类缺陷不再复发：
  1. 裸 `await request.json()` 在空/非法请求体时抛 JSONDecodeError → 500
  2. `DELETE /api/apitest/logs` 签名不匹配 → 必然 500
  3. `POST /api/environments` 整表单提交时 base_url 未弹出 → 必然 500
  4. 资源不存在抛裸 ValueError → 500，应为 404
"""
import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _login(client):
    r = client.post("/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    session = r.json()["data"]
    client.headers.update({
        "X-AUTH-TOKEN": session["sessionId"],
        "CSRF-TOKEN": session["csrfToken"],
    })
    return client


@pytest.fixture
def client():
    from app.main import app
    return _login(TestClient(app))


EMPTY_JSON = {"Content-Type": "application/json"}


# ════════════════════════════════════════════════════════════
# 1. 请求体归一化：空体 / 非法 JSON 不得 500
# ════════════════════════════════════════════════════════════

class TestRequestBodyNormalization:
    """read_body() 应吞掉空体与非法 JSON，返回空 dict 交由业务层校验。"""

    # 只挑无副作用的接口：空 ids 批量操作 / 导入空数据
    EMPTY_BODY_ENDPOINTS = [
        "/api/apitest/batch/definitions/delete",
        "/api/apitest/batch/cases/delete",
        "/api/apitest/batch/scenarios/delete",
        "/api/apitest/batch/mocks/delete",
        "/api/apitest/batch/definitions/purge",
        "/api/apitest/batch/definitions/recover",
        "/api/apitest/trash/definitions/batch-restore",
        "/api/apitest/trash/cases/batch-restore",
        "/api/apitest/trash/scenarios/batch-restore",
        "/api/apitest/trash/mocks/batch-restore",
        "/api/definition/batch-delete",
        "/api/api-definitions/import",
    ]

    @pytest.mark.parametrize("path", EMPTY_BODY_ENDPOINTS)
    def test_empty_body_not_500(self, client, path):
        """空请求体：不得 500，应返回 200 且按空入参处理。"""
        resp = client.post(path, content=b"", headers=EMPTY_JSON)
        assert resp.status_code == 200, f"{path} -> {resp.status_code} {resp.text}"

    @pytest.mark.parametrize("path", EMPTY_BODY_ENDPOINTS)
    def test_malformed_json_not_500(self, client, path):
        """非法 JSON 请求体：不得 500。"""
        resp = client.post(path, content=b"{not-json", headers=EMPTY_JSON)
        assert resp.status_code == 200, f"{path} -> {resp.status_code} {resp.text}"

    @pytest.mark.parametrize("path", EMPTY_BODY_ENDPOINTS)
    def test_scalar_body_not_500(self, client, path):
        """裸字符串请求体（前端 axios 拦截器常见产物）：不得 500。"""
        resp = client.post(path, content=b'"some-id"', headers=EMPTY_JSON)
        assert resp.status_code == 200, f"{path} -> {resp.status_code} {resp.text}"

    def test_empty_body_batch_delete_returns_zero(self, client):
        """空体批量删除：不删任何东西，deleted 应为 0。"""
        resp = client.post("/api/apitest/batch/definitions/delete",
                           content=b"", headers=EMPTY_JSON)
        assert resp.json()["data"]["deleted"] == 0


class TestScalarBodyOnCreateEndpoints:
    """裸字符串 / 数组请求体打到创建接口，不得 500。

    回归背景：read_body() 会把 `"x"` 归一化成 `{"id": "x"}`、
    `["a"]` 归一化成 `{"ids": ["a"]}`，而创建接口拿到 body 后是
    `**body` 展开传给 store 的。主键由服务端生成，客户端塞进来的
    id/ids 会让 store 报
    `create_definition() got an unexpected keyword argument 'id'` → 500。
    因此创建接口必须走 read_writable_body()（剔除 id/ids）。
    """

    CREATE_ENDPOINTS = [
        "/api/apitest/definitions",
        "/api/apitest/cases",
        "/api/apitest/scenarios",
        "/api/apitest/mocks",
        "/api/apitest/environments",
    ]

    @pytest.mark.parametrize("path", CREATE_ENDPOINTS)
    @pytest.mark.parametrize("payload", [b'"some-id"', b'["a", "b"]'],
                             ids=["bare-string", "bare-array"])
    def test_scalar_body_create_not_500(self, client, path, payload):
        resp = client.post(path, content=payload, headers=EMPTY_JSON)
        assert resp.status_code == 200, f"{path} -> {resp.status_code} {resp.text}"
        # 服务端必须自己生成 id，不能照抄客户端传来的裸字符串
        assert resp.json()["data"]["id"] != "some-id"


class TestWritableBodyDropsServerGeneratedFields:
    """read_writable_body() 必须剔除客户端传入的 id/ids。"""

    @pytest.mark.parametrize("field", ["id", "ids"])
    def test_client_supplied_id_is_dropped(self, field):
        from app.core.response import read_writable_body

        class _FakeReq:
            @staticmethod
            async def body():
                return b'{"x": 1}'

            @staticmethod
            async def json():
                return {field: "client-value", "name": "keep-me"}

        body = asyncio.run(read_writable_body(_FakeReq()))
        assert field not in body
        assert body["name"] == "keep-me"

    def test_normal_fields_preserved(self):
        from app.core.response import read_writable_body

        class _FakeReq:
            @staticmethod
            async def body():
                return b'{"x": 1}'

            @staticmethod
            async def json():
                return {"name": "x", "project_id": "p1"}

        body = asyncio.run(read_writable_body(_FakeReq()))
        assert body == {"name": "x", "project_id": "p1"}


class TestScalarBodyOnUpdateEndpoints:
    """裸数组请求体打到更新接口，不得 500。

    回归背景：store 的 `_update()` 用 `data.keys()` 直接拼 SQL SET 子句，
    客户端塞进来的 `ids` 会被拼成 `SET ids = ?`，触发
    `no such column: ids` → 500。更新接口同样必须剔除 id/ids。
    """

    UPDATE_ENDPOINTS = [
        "/api/apitest/definitions/{id}",
        "/api/apitest/cases/{id}",
        "/api/apitest/scenarios/{id}",
        "/api/apitest/mocks/{id}",
        "/api/apitest/environments/{id}",
    ]

    @pytest.mark.parametrize("path", UPDATE_ENDPOINTS)
    @pytest.mark.parametrize("payload", [b'"some-id"', b'["a", "b"]'],
                             ids=["bare-string", "bare-array"])
    def test_scalar_body_update_not_500(self, client, path, payload):
        # 用不存在的 id：期望 404（语义正确），绝不能是 500
        resp = client.put(path.format(id="__nonexistent__"),
                          content=payload, headers=EMPTY_JSON)
        assert resp.status_code == 404, f"{path} -> {resp.status_code} {resp.text}"


class TestImportEnvironmentSignature:
    """/api/apitest/environments/import 此前 100% 500。

    路由传了 project_id 关键字，但 Service/Repo 两层签名都没声明，
    于是任何请求都撞 `import_environment() got an unexpected keyword
    argument 'project_id'`。现补齐全链路签名。
    """

    @pytest.mark.parametrize("payload", [
        b"", b"{not-json", b'"some-id"', b'["a"]', b"{}",
    ], ids=["empty", "bad-json", "bare-string", "bare-array", "empty-obj"])
    def test_import_never_500(self, client, payload):
        """缺 name 属于参数问题 → 400；绝不能是 500。"""
        resp = client.post("/api/apitest/environments/import",
                           content=payload, headers=EMPTY_JSON)
        assert resp.status_code == 400, f"{resp.status_code} {resp.text}"

    def test_service_accepts_project_id(self):
        from app.services.apitest_service import apitest_service

        item = apitest_service.import_environment(
            {"name": "env-import-sig", "base_url": "http://x"}, project_id="p1")
        assert item is not None

    def test_import_roundtrip(self, client):
        """正常导入应成功，并带上项目维度。"""
        resp = client.post("/api/apitest/environments/import", json={
            "name": "env-roundtrip", "base_url": "http://x", "project_id": "p1",
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["project_id"] == "p1"


# ════════════════════════════════════════════════════════════
# 2. DELETE /api/apitest/logs 签名对齐
# ════════════════════════════════════════════════════════════

class TestClearOperationLogs:

    def test_endpoint_reachable(self, client):
        """此前 clear_operation_logs(days) 与无参签名不匹配，100% 500。"""
        resp = client.delete("/api/apitest/logs?days=30")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["success"] is True

    def test_service_accepts_days(self):
        """Service/Repo 必须接受 days 参数并透传到底层 store。"""
        from app.services.apitest_service import apitest_service
        assert apitest_service.clear_operation_logs(days=7) is not None


# ════════════════════════════════════════════════════════════
# 3. 环境注册 base_url 兼容
# ════════════════════════════════════════════════════════════

class TestEnvironmentBaseUrlCompat:

    @staticmethod
    def _create_payloads():
        return [
            {"name": "env-base-url-null", "base_url": None},
            {"name": "", "endpoint": "", "tags": [], "base_url": None},
            {"name": "env-base-url-set", "endpoint": "", "base_url": "http://x"},
        ]

    def test_full_form_submission(self, client):
        """整表单提交（endpoint 以空串存在）不得 500。"""
        resp = client.post("/api/environments",
                           json={"name": "", "endpoint": "", "tags": [], "base_url": None})
        assert resp.status_code == 200, resp.text
        client.delete(f"/api/environments/{resp.json()['data']['id']}")

    def test_base_url_maps_to_endpoint(self, client):
        """base_url 应被映射为 endpoint，且不透传给 register_environment。"""
        resp = client.post("/api/environments",
                           json={"name": "env-map", "endpoint": "", "base_url": "http://x"})
        assert resp.status_code == 200, resp.text
        env = resp.json()["data"]
        assert env["endpoint"] == "http://x"
        client.delete(f"/api/environments/{env['id']}")

    def test_repo_strips_base_url(self):
        """Repo 无条件弹出 base_url 并映射为 endpoint（Repository 直连 INSERT）。

        Repository 去空壳化后 create() 已改为仓库内直接 INSERT，不再经由
        manager.register_environment——此前的 monkeypatch 断言已过时。
        此处仅借用 manager 模块导入触发幂等建表，随后直接断言 INSERT 结果：
        创建后 get() 返回的 endpoint == base_url 透传值。
        """
        import app.environment.manager as _mgr  # noqa: F401  (导入即幂等建表)
        from app.repositories.environment_repo import EnvironmentRepo
        env = EnvironmentRepo.create(
            {"name": "x", "endpoint": "", "base_url": "http://y"})
        got = EnvironmentRepo.get(env["id"])
        assert got["endpoint"] == "http://y"
        # base_url 被无条件弹出，不应残留到数据行
        assert not got.get("base_url")
        # 清理
        EnvironmentRepo.delete(env["id"], permanent=True)


# ════════════════════════════════════════════════════════════
# 4. 资源不存在 → 404 而非 500
# ════════════════════════════════════════════════════════════

class TestNotFoundSemantics:

    def test_generate_data_missing_template(self, client):
        resp = client.post("/api/data/generate", json={"template_id": "nope"})
        assert resp.status_code == 404, resp.text
        assert resp.json()["message"]

    def test_launch_missing_environment(self, client):
        resp = client.post("/api/environments/nonexistent/launch")
        assert resp.status_code == 404, resp.text

    def test_stop_missing_environment(self, client):
        resp = client.post("/api/environments/nonexistent/stop")
        assert resp.status_code == 404, resp.text

    def test_not_found_error_is_404(self):
        """NotFoundError 必须映射为 404（异常处理器已注册）。"""
        from app.core.exceptions import NotFoundError
        exc = NotFoundError("nope")
        assert exc.code == 404

    def test_datafactory_raises_not_found(self):
        """造数底层应抛 NotFoundError，而非裸 ValueError。"""
        from app.core.exceptions import NotFoundError
        from app.repositories.datafactory_repo import DatafactoryRepo
        with pytest.raises(NotFoundError):
            DatafactoryRepo.generate_data("__nope__", 1, "default")

    def test_environment_raises_not_found(self):
        """环境启动/停止的"不存在"应为 NotFoundError。

        生命周期实际逻辑已迁移到服务层 environment_service。
        """
        from app.core.exceptions import NotFoundError
        from app.services.environment_service import environment_service
        with pytest.raises(NotFoundError):
            environment_service.launch("__nope__")
        with pytest.raises(NotFoundError):
            environment_service.stop("__nope__")
