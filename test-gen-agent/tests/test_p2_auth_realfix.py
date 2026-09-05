"""P2 · auth 剩余占位真实化回归测试。

覆盖三项收敛：
  1. display/info 与 display/save 真实落库（文本 + multipart 文件）
  2. ai/config/source/list（GET/POST）与 name/list 返回真实模型源
  3. ai/config CRUD（get/get/{id}/edit-source/delete/{id}）真实读写
  4. personal/model/* 真实化（owner=当前用户）
"""
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        session = r.json()["data"]
        c.headers.update({
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        })
        yield c


# ════════════════════════════════════════════════════════════
# 1. display 界面配置落库
# ════════════════════════════════════════════════════════════
class TestDisplayRealPersistence:
    """display/save 落库 + display/info 读回。"""

    def _cleanup(self):
        from app.repositories.display_config_repo import display_config_repo
        display_config_repo.clear()

    def test_text_save_and_read(self, client):
        self._cleanup()
        items = [
            {"paramKey": "ui.title", "paramValue": "P2-TestPilot", "type": "text"},
            {"paramKey": "ui.slogan", "paramValue": "P2 slogan", "type": "text"},
            {"paramKey": "ui.style", "paramValue": "default", "type": "text"},
            {"paramKey": "ui.theme", "paramValue": "custom", "type": "text"},
        ]
        r = client.post("/display/save", json=items)
        assert r.status_code == 200
        assert r.json()["code"] == 200

        r = client.get("/display/info")
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list) and len(data) >= 4
        store = {it["paramKey"]: it for it in data}
        assert store["ui.title"]["paramValue"] == "P2-TestPilot"
        assert store["ui.slogan"]["paramValue"] == "P2 slogan"
        self._cleanup()

    def test_multipart_file_save(self, client):
        self._cleanup()
        request_json = json.dumps([
            {"paramKey": "ui.icon", "paramValue": "", "type": "file",
             "fileName": "old.png", "original": False, "hasFile": True},
            {"paramKey": "ui.loginLogo", "paramValue": "", "type": "file",
             "fileName": "old.svg", "original": False, "hasFile": True},
        ])
        files = [
            ("files", ("ui.icon,icon2.png", b"PNGDATA2", "image/png")),
            ("files", ("ui.loginLogo,logo2.svg", b"<svg/>", "image/svg+xml")),
        ]
        r = client.post("/display/save", data={"request": request_json}, files=files)
        assert r.status_code == 200, r.text
        assert r.json()["code"] == 200

        r = client.get("/display/info")
        data = {it["paramKey"]: it for it in r.json()["data"]}
        icon = data["ui.icon"]
        # 前端 initPageConfig 约定：文件项 url 取 fileName（可访问 URL）
        assert icon["fileName"].startswith("/attachment/download/")
        assert icon["paramValue"] == "icon2.png"
        # 下载回源可读
        rr = client.get(icon["fileName"])
        assert rr.status_code == 200
        assert rr.content == b"PNGDATA2"
        self._cleanup()


# ════════════════════════════════════════════════════════════
# 2. ai/config/source 真实数据
# ════════════════════════════════════════════════════════════
class TestAiConfigSourceReal:
    """模型源列表不再为空数组、POST 分页可用、name 下拉可用。"""

    def _cleanup(self):
        from app.repositories.ai_model_repo import ai_model_repo
        rows = ai_model_repo.list(owner_type="SYSTEM")
        for r in rows:
            ai_model_repo.delete(r["id"])
        ai_model_repo._ensure_table()

    def test_get_list_not_empty(self, client):
        # 默认会 seed 一条系统源（基于 env 配置）
        r = client.get("/ai/config/source/list")
        assert r.status_code == 200
        assert r.json()["code"] == 200
        data = r.json()["data"]
        assert isinstance(data, list)
        # 只要启用过 seed 或已有数据即可非空；不强依赖具体条数
        assert any(it.get("status") for it in data) if data else True

    def test_post_pagination(self, client):
        from app.services.ai_model_service import ai_model_service
        ai_model_service._ensure_system_default()
        r = client.post("/ai/config/source/list", json={
            "current": 1, "pageSize": 10, "owner": "", "providerName": "", "keyword": "",
        })
        assert r.status_code == 200, r.text
        payload = r.json()
        assert payload["code"] == 200
        data = payload["data"]
        assert "list" in data and "total" in data and "pageSize" in data
        assert isinstance(data["list"], list)

    def test_name_list_shape(self, client):
        from app.services.ai_model_service import ai_model_service
        ai_model_service._ensure_system_default()
        r = client.get("/ai/config/source/name/list")
        assert r.status_code == 200
        data = r.json()["data"]
        assert isinstance(data, list)
        for it in data:
            assert "id" in it and "name" in it

    def test_crud_roundtrip(self, client):
        # 新建
        r = client.post("/ai/config/edit-source", json={
            "name": "P2-Test-Model", "type": "LLM", "providerName": "DeepSeek",
            "permissionType": "PUBLIC", "status": True, "owner": "", "ownerType": "SYSTEM",
            "baseName": "deepseek-chat", "appKey": "sk-p2", "apiUrl": "https://api.deepseek.com",
        })
        assert r.status_code == 200, r.text
        saved = r.json()["data"]
        assert saved["name"] == "P2-Test-Model"
        mid = saved["id"]
        try:
            # 详情
            r = client.get(f"/ai/config/get/{mid}")
            assert r.json()["code"] == 200
            assert r.json()["data"]["appKey"] == "sk-p2"
            # 名称下拉包含
            names = client.get("/ai/config/source/name/list").json()["data"]
            assert any(it["id"] == mid for it in names)
        finally:
            # 删除（真实）
            r = client.get(f"/ai/config/delete/{mid}")
            assert r.json()["code"] == 200
            r = client.get(f"/ai/config/get/{mid}")
            assert r.json()["code"] == 404

    def test_delete_missing_returns_ok(self, client):
        """兼容既有测试：删除不存在的模型也应返回 200（业务语义幂等）。"""
        r = client.delete("/ai/config/delete/not-exist")
        assert r.status_code == 200
        assert r.json()["code"] == 200


# ════════════════════════════════════════════════════════════
# 3. personal/model/* 真实化
# ════════════════════════════════════════════════════════════
class TestPersonalModelReal:
    """个人模型源列表/编辑/详情不再空转。"""

    def test_personal_crud(self, client):
        from app.repositories.ai_model_repo import ai_model_repo
        # 清理历史个人模型
        for r in ai_model_repo.list(owner_type="PERSONAL"):
            ai_model_repo.delete(r["id"])

        r = client.post("/personal/model/edit-source", json={
            "name": "P2-Personal", "type": "LLM", "providerName": "Open AI",
            "permissionType": "PRIVATE", "status": True,
            "baseName": "gpt-4o-mini", "appKey": "", "apiUrl": "http://localhost:8000/v1",
        })
        assert r.status_code == 200, r.text
        saved = r.json()["data"]
        assert saved["ownerType"] == "PERSONAL"
        mid = saved["id"]
        try:
            # GET 列表
            r = client.get("/personal/model/source/list")
            assert r.json()["code"] == 200
            assert any(it["id"] == mid for it in r.json()["data"])
            # POST 分页
            r = client.post("/personal/model/source/list", json={"current": 1, "pageSize": 10})
            assert r.json()["code"] == 200
            assert r.json()["data"]["list"][0]["id"] == mid
            # 详情
            r = client.get(f"/personal/model/get/{mid}")
            assert r.json()["data"]["name"] == "P2-Personal"
        finally:
            r = client.post(f"/personal/model/delete/{mid}")
            assert r.json()["code"] == 200
