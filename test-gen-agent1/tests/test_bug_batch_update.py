"""缺陷管理 - 批量更新 batch-update 真实落库回归测试。

验证 /bug/batch-update 不再是假成功（原先恒 ok(None) 无动作），
而是对选中缺陷逐条真实落库：tags 追加 / 清空 / 覆盖，以及 severity 等字段。
"""
import uuid

from fastapi.testclient import TestClient

from app.main import app

UNIQ = uuid.uuid4().hex[:6]


def _client():
    c = TestClient(app)
    r = c.post("/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    j = r.json()["data"]
    c.headers.update({"X-AUTH-TOKEN": j["sessionId"], "CSRF-TOKEN": j["csrfToken"]})
    return c


def _create_bug(c, title):
    r = c.post("/bug/add", json={"title": f"{title}-{UNIQ}", "severity": "major"})
    assert r.json()["code"] == 200
    return r.json()["data"]["id"]


def _get(c, bid):
    r = c.get(f"/bug/get/{bid}")
    assert r.json()["code"] == 200
    return r.json()["data"]


def _batch(c, payload):
    r = c.post("/bug/batch-update", json=payload)
    assert r.json()["code"] == 200
    return r.json()["data"]


class TestBugBatchUpdate:
    def test_batch_update_tags_append(self):
        c = _client()
        ids = [_create_bug(c, "append") for _ in range(2)]
        assert all(_get(c, i)["tags"] == [] for i in ids)
        data = _batch(c, {"selectIds": ids, "attribute": "tags",
                          "value": ["t1", "t2"], "append": True})
        assert data["updated"] == 2
        assert all(sorted(_get(c, i)["tags"]) == ["t1", "t2"] for i in ids)
        # 重复追加去重
        _batch(c, {"selectIds": ids, "attribute": "tags",
                   "value": ["t2"], "append": True})
        assert all(sorted(_get(c, i)["tags"]) == ["t1", "t2"] for i in ids)

    def test_batch_update_tags_replace(self):
        c = _client()
        ids = [_create_bug(c, "replace") for _ in range(2)]
        _batch(c, {"selectIds": ids, "attribute": "tags",
                   "value": ["a"], "append": False, "clear": False})
        data = _batch(c, {"selectIds": ids, "attribute": "tags",
                          "value": ["x", "y"], "append": False, "clear": False})
        assert data["updated"] == 2
        assert all(sorted(_get(c, i)["tags"]) == ["x", "y"] for i in ids)

    def test_batch_update_tags_clear(self):
        c = _client()
        ids = [_create_bug(c, "clear") for _ in range(2)]
        _batch(c, {"selectIds": ids, "attribute": "tags",
                   "value": ["a"], "append": False, "clear": False})
        data = _batch(c, {"selectIds": ids, "attribute": "tags",
                          "value": [], "clear": True})
        assert data["updated"] == 2
        assert all(_get(c, i)["tags"] == [] for i in ids)

    def test_batch_update_severity(self):
        c = _client()
        ids = [_create_bug(c, "sev") for _ in range(2)]
        data = _batch(c, {"selectIds": ids, "attribute": "severity",
                          "value": "critical"})
        assert data["updated"] == 2
        assert all(_get(c, i)["severity"] == "critical" for i in ids)

    def test_batch_update_empty_selection(self):
        c = _client()
        data = _batch(c, {"selectIds": [], "attribute": "severity", "value": "major"})
        assert data["updated"] == 0
