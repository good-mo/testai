"""DDD ai_model 域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/ai_model/` DDD 层就绪后，本测试锁定阶段 C 薄门面接线契约：
`app/services/ai_model_service.py` 已收敛为对 `ai_model_app_service` 的薄委托
门面（list / get / get_or_default / save / delete），并保留系统默认源种子
`_ensure_system_default` 与前端 `createUserName` 展示字段补齐。

验证：
  1. 新建模型落库 id 与返回 id 一致（修复 adapter 新建忽略聚合 id 缺陷）；
  2. service 确实委托 DDD 门面；
  3. 对外 camelCase 契约 + createUserName 补齐不回归；
  4. 更新 / 删除闭环。
"""
import uuid

from app.domain.ai_model.application.ai_model_app_service import (
    ai_model_app_service as ddd,
)
from app.services.ai_model_service import ai_model_service as svc


def _mid(prefix="model"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _cleanup(model_id):
    if model_id:
        try:
            svc.delete(model_id)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# 一、落库 id 与聚合 id 一致（新建不丢 id）
# ─────────────────────────────────────────────────────────────
def test_create_returns_persisted_id():
    """新建模型返回的 id 必须等于落库 id（回读一致）。"""
    d = None
    try:
        d = svc.save(
            {"name": "接线-新建", "providerName": "Open AI",
             "baseName": "gpt-4o", "type": "LLM"},
            owner_type="SYSTEM",
        )
        assert d.get("id"), "新建应返回 id"
        got = svc.get(d["id"])
        assert got and got["id"] == d["id"], "回读 id 必须等于返回 id（不得漂移）"
        d = d["id"]
    finally:
        _cleanup(d)


# ─────────────────────────────────────────────────────────────
# 二、service 委托 DDD 门面
# ─────────────────────────────────────────────────────────────
def test_service_delegates_to_ddd_get(monkeypatch):
    """get 委托 DDD get。"""
    d = None
    try:
        d = svc.save({"name": "委托", "providerName": "DeepSeek"}, owner_type="SYSTEM")
        nid = d["id"]
        called = []
        real = ddd.get

        def fake_get(cmd):
            called.append(cmd.model_id)
            return real(cmd)

        monkeypatch.setattr(ddd, "get", fake_get)
        got = svc.get(nid)
        assert called == [nid]
        assert got and got["id"] == nid
        d = nid
    finally:
        _cleanup(d)


def test_service_delegates_to_ddd_upsert(monkeypatch):
    """save 委托 DDD upsert（走聚合权威裁决）。"""
    d = None
    try:
        d = svc.save({"name": "委托保存", "providerName": "ZhiPu AI"}, owner_type="SYSTEM")
        nid = d["id"]
        called = []
        real = ddd.upsert

        def fake_upsert(data, create_user="admin"):
            called.append((data.get("name"), create_user))
            return real(data, create_user=create_user)

        monkeypatch.setattr(ddd, "upsert", fake_upsert)
        svc.save({"id": nid, "name": "委托改名"})
        assert called and called[0][0] == "委托改名"
        d = nid
    finally:
        _cleanup(d)


# ─────────────────────────────────────────────────────────────
# 三、对外 camelCase 契约 + createUserName 补齐
# ─────────────────────────────────────────────────────────────
def test_contract_fields_preserved():
    """返回包含前端依赖字段（camelCase + createUserName）。"""
    d = None
    try:
        d = svc.save(
            {"name": "契约字段", "providerName": "Open AI",
             "baseName": "gpt-4o", "appKey": "k", "apiUrl": "http://x",
             "advSettingDTOList": [], "type": "LLM"},
            owner_type="SYSTEM",
        )
        for f in ("id", "name", "type", "providerName", "permissionType",
                  "status", "baseName", "appKey", "apiUrl",
                  "advSettingDTOList", "createUser", "createUserName"):
            assert f in d, f"缺字段 {f}"
        assert d["createUserName"] == d["createUser"]
        d = d["id"]
    finally:
        _cleanup(d)


# ─────────────────────────────────────────────────────────────
# 四、更新 / 删除闭环
# ─────────────────────────────────────────────────────────────
def test_update_and_delete_roundtrip():
    """更新字段落库，删除后回读为空。"""
    d = None
    try:
        d = svc.save({"name": "闭环", "providerName": "Open AI"}, owner_type="SYSTEM")
        nid = d["id"]
        upd = svc.save({"id": nid, "name": "闭环-改名", "baseName": "gpt-4o"})
        assert upd["name"] == "闭环-改名"
        got = svc.get(nid)
        assert got and got["name"] == "闭环-改名" and got["baseName"] == "gpt-4o"
        assert svc.delete(nid) is True
        assert svc.get(nid) is None
        d = None
    finally:
        _cleanup(d)
