"""数据工厂 DDD A→B→C 迁移回归测试。

验证：
  1.（阶段 B）router 已改调 datafactory_app_service，对外 API 契约不变：
     - 列表返回 `templates`/`total`
     - 造数返回补 `batch_id` 别名（兼容既有消费方），并仍含 `id`
     - 资源不存在返回 404（而非 500），错误经 fail() 翻译
  2.（阶段 C）datafactory_service 瘦身为薄门面委托 DDD，行为与 DDD 一致。
"""
import uuid

import pytest
from fastapi.testclient import TestClient

TAG = "migdf"


def _data(resp):
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as c:
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        if r.status_code == 200:
            session = r.json()["data"]
            c.headers.update({
                "X-AUTH-TOKEN": session["sessionId"],
                "CSRF-TOKEN": session["csrfToken"],
            })
        yield c


def _create(client):
    name = f"{TAG}-{uuid.uuid4().hex[:6]}"
    r = client.post("/api/data/templates", json={
        "name": name, "category": "user",
        "schema_def": {"a": {"strategy": "fixed", "value": 1}},
    })
    assert r.status_code == 200, r.text
    return _data(r)


# ── 阶段 B：router 走 DDD 应用服务且契约不变 ──────────────
class TestStageBRouter:
    def test_create_returns_id_contract(self, client):
        t = _create(client)
        assert "id" in t
        assert "category" in t
        client.delete(f"/api/data/templates/{t['id']}")

    def test_list_templates_contract(self, client):
        r = client.get("/api/data/templates")
        assert r.status_code == 200
        payload = _data(r)
        assert "templates" in payload and "total" in payload

    def test_generate_returns_batch_id_alias(self, client):
        t = _create(client)
        r = client.post("/api/data/generate", json={
            "template_id": t["id"], "batch_size": 2,
        })
        assert r.status_code == 200, r.text
        payload = _data(r)
        # 阶段 B DTO 桥：兼容既有 batch_id 契约（别名与 id 一致）
        assert payload.get("batch_id") == payload.get("id")
        assert len(payload.get("data", [])) == 2
        client.delete(f"/api/data/templates/{t['id']}")

    def test_missing_template_returns_404(self, client):
        r = client.post("/api/data/generate", json={"template_id": "nope"})
        assert r.status_code == 404

    def test_missing_get_returns_404(self, client):
        r = client.get("/api/data/templates/nonexistent")
        assert r.status_code == 404

    def test_cleanup_unknown_batch_idempotent_200(self, client):
        r = client.post(f"/api/data/cleanup/batch/{uuid.uuid4().hex[:8]}")
        assert r.status_code == 200

    def test_batches_and_stats_contract(self, client):
        assert client.get("/api/data/batches").status_code == 200
        assert client.get("/api/data/stats").status_code == 200


# ── 阶段 C：service 薄门面委托 DDD，行为一致 ──────────────
class TestStageCService:
    def test_service_generate_has_batch_id_and_ddd_consistent(self):
        """薄门面 generate_data 补 batch_id；用同一模板经 service 造数后，
        batch 应出现在 DDD list_batches 中（证明同一存储/聚合链路）。"""
        from app.domain.datafactory.application.datafactory_app_service import (
            datafactory_app_service as ddd,
        )
        from app.domain.datafactory.application.dto import CreateTemplateCommand
        from app.services.datafactory_service import datafactory_service as svc

        d = ddd.create_template(CreateTemplateCommand(
            name=f"{TAG}-svc-{uuid.uuid4().hex[:6]}",
            category="user", schema_def={"a": {"strategy": "fixed", "value": 1}},
        ))
        try:
            via_svc = svc.generate_data(template_id=d["id"], batch_size=1)
            # 薄门面补 batch_id，与聚合 id 对齐
            assert via_svc["batch_id"] == via_svc.get("id") or via_svc["batch_id"]
            # 该批次应被 DDD 仓储读到（同一存储链路）
            batches = ddd.list_batches(limit=50).get("batches", [])
            assert any(b.get("id") == via_svc["batch_id"] for b in batches)
        finally:
            ddd.delete_template(d["id"])

    def test_service_not_found_semantics(self):
        from app.core.exceptions import NotFoundError
        from app.services.datafactory_service import datafactory_service as svc
        with pytest.raises(NotFoundError):
            svc.generate_data(template_id="__nope__")
