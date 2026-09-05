"""curl 导入解析单元测试：覆盖解析器与 /api/debug/import-curl 接口。"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.curl_parser import parse_curl


@pytest.fixture
def client():
    """创建已登录测试客户端。"""
    c = TestClient(app)
    r = c.post("/login", json={"username": "admin", "password": "admin123"})
    if r.status_code == 200:
        session = r.json()["data"]
        c.headers.update({
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        })
    return c


class TestCurlParser:
    """解析器单元测试。"""

    def test_parse_simple_get(self):
        r = parse_curl("curl https://api.example.com/items")
        assert r["method"] == "GET"
        assert r["url"] == "https://api.example.com/items"
        assert r["bodyType"] == "NONE"
        assert r["body"] is None

    def test_parse_get_with_query(self):
        r = parse_curl("curl 'https://api.example.com/users?page=1&size=20'")
        assert r["url"] == "https://api.example.com/users"
        assert r["queryParams"] == {"page": "1", "size": "20"}

    def test_parse_post_json(self):
        r = parse_curl(
            'curl -X POST https://api.example.com/users'
            ' -H "Content-Type: application/json"'
            " -d '{\"name\":\"john\",\"age\":30}'"
        )
        assert r["method"] == "POST"
        assert r["bodyType"] == "JSON"
        assert r["body"] == {"name": "john", "age": 30}

    def test_parse_post_form(self):
        r = parse_curl(
            "curl -X POST https://api.example.com/login"
            " -d 'name=foo&password=bar'"
        )
        assert r["method"] == "POST"
        assert r["bodyType"] == "WWW_FORM"
        assert r["body"] == {"name": "foo", "password": "bar"}

    def test_parse_multipart(self):
        r = parse_curl(
            'curl -F "file=@/tmp/a.txt" -F "name=test" http://up.example.com/upload'
        )
        assert r["method"] == "POST"
        assert r["bodyType"] == "FORM_DATA"
        assert r["body"] == {"file": "", "name": "test"}

    def test_parse_method_inference(self):
        r = parse_curl("curl -X DELETE http://example.com/r/7?force=true")
        assert r["method"] == "DELETE"
        assert r["queryParams"] == {"force": "true"}

    def test_parse_raw(self):
        r = parse_curl(
            'curl --request POST https://httpbin.org/anything'
            ' --header "content-type: text/plain" --data-raw "hello world"'
        )
        assert r["method"] == "POST"
        assert r["bodyType"] == "RAW"
        assert r["body"] == "hello world"

    def test_parse_headers(self):
        r = parse_curl(
            'curl https://api.example.com/items'
            ' -H "Authorization: Bearer abc123"'
            ' -H "X-Custom: v1"'
        )
        assert r["headers"] == {"Authorization": "Bearer abc123", "X-Custom": "v1"}


class TestImportCurlEndpoint:
    """接口测试。"""

    def test_import_valid_curl(self, client):
        resp = client.post(
            "/api/debug/import-curl",
            json={"curl": "curl -X POST https://api.example.com/users"
                          ' -H "Content-Type: application/json"'
                          " -d '{\"name\":\"john\"}'"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["method"] == "POST"
        assert data["url"] == "https://api.example.com/users"
        assert data["bodyType"] == "JSON"
        assert data["body"] == {"name": "john"}

    def test_import_empty_curl(self, client):
        resp = client.post("/api/debug/import-curl", json={"curl": ""})
        assert resp.status_code == 200
        data = resp.json()["data"]
        # 空命令不得返回 null，需给出兜底结构避免前端解构报错
        assert data == {
            "method": "GET",
            "url": "",
            "headers": {},
            "body": None,
            "bodyType": "NONE",
            "queryParams": {},
        }

    def test_import_no_curl_key(self, client):
        resp = client.post("/api/debug/import-curl", json={})
        assert resp.status_code == 200
        assert resp.json()["data"]["method"] == "GET"
