"""DDD display_config 域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/display_config/` DDD 层就绪后，本测试锁定阶段 C 薄门面接线契约：
`app/services/display_config_service.py` 已收敛为对 `display_app_service` 的
**薄委托门面** —— `save/get_all/get_file_url` 全部经 DDD 应用门面裁决语义并
持久化（消灭 service→repo 双写旁路），仅 `save_uploaded_file`（物理文件落盘、
属 file 限界上下文）保留在门面层。

对外方法签名与返回 schema 与重构前一致（文本保存、multipart 文件、JSON 旧值
幂等重存、文件项清空语义零变化），router 零改动。本测试断言确实走 DDD 门面，
并经 HTTP 全链路验证端到端契约。
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.domain.display_config.application.display_app_service import (
    display_app_service as ddd,
)
from app.repositories.display_config_repo import display_config_repo
from app.services.display_config_service import display_config_service as svc


@pytest.fixture()
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


# ═══════════════════════════════════════════════════════════
# 一、薄门面确实委托 DDD 应用服务（消灭双写旁路）
# ═══════════════════════════════════════════════════════════
def test_save_delegates_to_ddd(monkeypatch):
    """save 委托 DDD app_service；门面不再直连 repo。"""
    display_config_repo.clear()
    seen = []

    def fake_save(cmd):
        seen.append((len(cmd.items), len(cmd.uploaded)))
        return ddd._repo.get_all()

    monkeypatch.setattr(ddd, "save", fake_save)
    request_items = [
        {"paramKey": "ui.title", "paramValue": "平台", "type": "text"},
    ]
    svc.save(request_items, {})
    assert seen == [(1, 0)]


def test_get_all_delegates_to_ddd(monkeypatch):
    """get_all 委托 DDD app_service。"""
    display_config_repo.clear()
    display_config_repo.save_many([
        {"paramKey": "ui.title", "paramValue": "P", "type": "text"},
    ])
    seen = []

    def fake_get_all(cmd):
        seen.append(cmd)
        return [{"paramKey": "ui.title", "paramValue": "P", "type": "text"}]

    monkeypatch.setattr(ddd, "get_all", fake_get_all)
    got = svc.get_all()
    assert got == [{"paramKey": "ui.title", "paramValue": "P", "type": "text"}]
    assert len(seen) == 1


def test_service_does_not_import_repo_directly():
    """门面不再直接 import/repo 调用（无 app.repositories 依赖）。"""
    import inspect

    import app.services.display_config_service as mod
    src = inspect.getsource(mod)
    assert "display_config_repo" not in src
    assert "app.repositories" not in src


# ═══════════════════════════════════════════════════════════
# 二、保存语义端到端（经 HTTP + DDD 门面）
# ═══════════════════════════════════════════════════════════
def test_text_save_and_read(client):
    """文本项保存落库 + display/info 读回。"""
    display_config_repo.clear()
    r = client.post("/display/save", json=[
        {"paramKey": "ui.title", "paramValue": "DDD 平台", "type": "text"},
        {"paramKey": "ui.slogan", "paramValue": "DDD slogan", "type": "text"},
    ])
    assert r.status_code == 200 and r.json()["code"] == 200
    data = {it["paramKey"]: it for it in r.json()["data"]}
    assert data["ui.title"]["paramValue"] == "DDD 平台"
    assert data["ui.slogan"]["paramValue"] == "DDD slogan"

    r = client.get("/display/info")
    store = {it["paramKey"]: it for it in r.json()["data"]}
    assert store["ui.title"]["paramValue"] == "DDD 平台"
    display_config_repo.clear()


def test_multipart_file_save(client):
    """multipart 上传文件：fileName 存 URL、paramValue 存原始文件名，可回源。"""
    display_config_repo.clear()
    request_json = json.dumps([
        {"paramKey": "ui.icon", "paramValue": "", "type": "file",
         "fileName": "old.png", "original": False, "hasFile": True},
    ])
    r = client.post("/display/save", data={"request": request_json},
                    files=[("files", ("ui.icon,icon2.png", b"PNGDATA2", "image/png"))])
    assert r.status_code == 200, r.text
    data = {it["paramKey"]: it for it in r.json()["data"]}
    icon = data["ui.icon"]
    assert icon["fileName"].startswith("/attachment/download/")
    assert icon["paramValue"] == "icon2.png"
    # 回源可读
    rr = client.get(icon["fileName"])
    assert rr.status_code == 200 and rr.content == b"PNGDATA2"
    display_config_repo.clear()


def test_json_existing_url_idempotent(client):
    """未换图 JSON 直提旧 URL：把 URL 搬入 fileName 幂等重存。"""
    display_config_repo.clear()
    display_config_repo.save_many([
        {"paramKey": "ui.loginLogo", "paramValue": "logo.png", "type": "file",
         "fileName": "/attachment/download/abc"},
    ])
    r = client.post("/display/save", json=[
        {"paramKey": "ui.loginLogo", "paramValue": "/attachment/download/abc",
         "type": "file", "fileName": "logo.png"},
    ])
    assert r.status_code == 200, r.text
    data = {it["paramKey"]: it for it in r.json()["data"]}
    logo = data["ui.loginLogo"]
    assert logo["fileName"] == "/attachment/download/abc"
    assert logo["paramValue"] == "logo.png"
    display_config_repo.clear()


def test_get_file_url(client):
    """文件类 key 的可访问 URL 经 DDD 门面读回。"""
    display_config_repo.clear()
    display_config_repo.save_many([
        {"paramKey": "ui.icon", "paramValue": "icon.png", "type": "file",
         "fileName": "/attachment/download/1"},
    ])
    assert svc.get_file_url("ui.icon") == "icon.png"
    assert svc.get_file_url("ui.nope") == ""
    display_config_repo.clear()


def test_clear_file_matches_legacy_semantics(client):
    """文件项清空语义与重构前一致（空值条目仍幂等重入）。"""
    display_config_repo.clear()
    display_config_repo.save_many([
        {"paramKey": "ui.icon", "paramValue": "x.png", "type": "file",
         "fileName": "/att/1"},
    ])
    r = client.post("/display/save", json=[
        {"paramKey": "ui.icon", "paramValue": "", "type": "file",
         "fileName": "", "original": True, "hasFile": False},
    ])
    assert r.status_code == 200, r.text
    store = {it["paramKey"]: it for it in r.json()["data"]}
    # 与重构前一致：清空后该 key 以空值保留（幂等）
    assert store["ui.icon"]["paramValue"] == ""
    display_config_repo.clear()
