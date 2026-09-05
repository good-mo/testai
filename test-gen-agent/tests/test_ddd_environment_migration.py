"""DDD environment 域 A→B→C 渐进迁移回归测试。

背景
----
`app/domain/environment/` DDD 层（阶段 A）就绪后，本测试锁定「阶段 B/C」接入契约：
  - 阶段 C：`app/services/environment_service.py` 的纯 CRUD / 回收站 / 告警已收敛为
    对 `environment_app_service` 的薄委托门面；
  - 阶段 B：Router 经薄 Service → DDD 门面 → 聚合，环境生命周期 CRUD/回收站/告警
    全链路落库可查可删；
  - Docker 拉起/停止/健康检查副作用保留在 Service，状态流转经 DDD 生命周期钩子。

本测试以 Service 为界验证迁移后行为与旧契约一致，作为逐域切换的回归基线。
"""
import uuid

from app.repositories.environment_repo import EnvironmentRepo
from app.services.environment_service import environment_service as svc

TAG = "envmig"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _cleanup(eid: str) -> None:
    try:
        EnvironmentRepo.purge(eid)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 一、CRUD 委托 DDD（阶段 C）
# ═══════════════════════════════════════════════════════════
def test_create_get_update_roundtrip():
    d = svc.create({"name": _mk(), "env_type": "docker", "description": "desc"})
    eid = d["id"]
    try:
        assert d and d["name"]
        assert d["status"] == "offline"          # 默认态由聚合守护
        g = svc.get(eid)
        assert g is not None and g["description"] == "desc"
        u = svc.update(eid, {"description": "updated"})
        assert u and u["description"] == "updated"
    finally:
        _cleanup(eid)


def test_create_ignores_unknown_fields():
    """宽松入参（base_url 等）不影响 DDD 命令翻译。"""
    d = svc.create({"name": _mk(), "env_type": "docker", "base_url": "http://x"})
    try:
        assert d and d["id"]
    finally:
        _cleanup(d["id"])


def test_get_missing_returns_none():
    assert svc.get(f"nope_{uuid.uuid4().hex[:6]}") is None


# ═══════════════════════════════════════════════════════════
# 二、回收站 / 告警 委托 DDD 门面
# ═══════════════════════════════════════════════════════════
def test_trash_restore_purge_cycle():
    d = svc.create({"name": _mk()})
    eid = d["id"]
    try:
        assert svc.trash(eid) is True
        assert any(x["id"] == eid for x in svc.list_trash())
        assert svc.restore(eid) is True
        assert svc.get(eid) is not None
        assert svc.delete(eid) is True
        assert svc.get(eid) is None
    finally:
        _cleanup(eid)


def test_alerts_and_stats_shape():
    stats = svc.get_stats()
    assert isinstance(stats, dict)
    alerts = svc.list_alerts(limit=5)
    assert isinstance(alerts, list)


# ═══════════════════════════════════════════════════════════
# 三、Router 契约（阶段 B）
# ═══════════════════════════════════════════════════════════
def test_router_crud(auth_client):
    name = _mk()
    r = auth_client.post("/api/environments", json={"name": name})
    assert r.status_code == 200
    data = r.json().get("data", {})
    eid = data.get("id")
    assert eid
    try:
        got = auth_client.get(f"/api/environments/{eid}").json()["data"]
        assert got["name"] == name
        # trash list endpoint
        rl = auth_client.get("/api/environments/trash/list")
        assert rl.status_code == 200
    finally:
        auth_client.delete(f"/api/environments/{eid}")
        _cleanup(eid)


def test_router_get_missing_404(auth_client):
    r = auth_client.get(f"/api/environments/nope_{uuid.uuid4().hex[:6]}")
    assert r.status_code == 404
