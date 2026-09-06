"""DDD template 域 A→B→C 渐进迁移回归测试。

背景
----
`app/domain/template/` DDD 层（阶段 A）就绪后，本测试锁定「阶段 B/C」接入契约：
  - 阶段 C：`app/services/template_service.py` 已收敛为对 `template_app_service`
    的薄委托门面，list / get / add / update / delete / set_default 全部经 DDD 门面；
  - 阶段 B：Router 经薄 Service → DDD 门面 → 聚合，模板 CRUD 全链路落库可查可删；
  - 领域不变量（空范围播种默认、首条自动默认）由聚合根/门面守护。

本测试以 Service 为界验证迁移后行为与旧契约一致，作为逐域切换的回归基线。
"""
import uuid

from app.repositories.template_repo import TemplateRepo
from app.services.template_service import template_service as svc

TAG = "tpnmig"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _cleanup(tid: str) -> None:
    try:
        TemplateRepo.delete_template(tid)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 一、add / get / list / update 委托 DDD（阶段 C）
# ═══════════════════════════════════════════════════════════
def test_add_first_template_auto_default():
    sid = _mk()
    tid = _mk()
    body = {"id": tid, "name": "项目模板", "scene": "FUNCTIONAL",
            "scopeId": sid, "customFields": [{"id": "f1", "label": "优先级"}]}
    try:
        d = svc.add_template("PROJECT", body)
        assert d and d["id"] == tid
        assert d["enableDefault"] is True          # 范围内首条自动默认
        assert d["customFields"] == [{"id": "f1", "label": "优先级"}]
        # list 空范围播种后仍能读到本模板
        got = [t for t in svc.list_templates("PROJECT", sid, "FUNCTIONAL")
               if t["id"] == tid]
        assert len(got) == 1
    finally:
        _cleanup(tid)


def test_update_template_roundtrip():
    sid = _mk()
    tid = _mk()
    body = {"id": tid, "name": "原始名", "scene": "BUG", "scopeId": sid}
    try:
        svc.add_template("PROJECT", body)
        u = svc.update_template("PROJECT", tid, {
            **body, "name": "更新名", "remark": "备注",
        })
        assert u and u["name"] == "更新名"
        assert u["remark"] == "备注"
        g = svc.get_template("PROJECT", tid)
        assert g["name"] == "更新名"
    finally:
        _cleanup(tid)


def test_get_missing_returns_none():
    assert svc.get_template("PROJECT", f"nope_{uuid.uuid4().hex[:6]}") is None


# ═══════════════════════════════════════════════════════════
# 二、set_default / delete（委托 DDD 门面）
# ═══════════════════════════════════════════════════════════
def test_set_default_and_delete():
    sid = _mk()
    a, b = _mk(), _mk()
    try:
        svc.add_template("PROJECT", {"id": a, "name": "A", "scene": "API", "scopeId": sid})
        svc.add_template("PROJECT", {"id": b, "name": "B", "scene": "API", "scopeId": sid})
        assert svc.set_default("PROJECT", sid, "API", a) is True
        assert svc.delete_template(b) is True
        assert svc.get_template("PROJECT", b) is None
    finally:
        _cleanup(a)
        _cleanup(b)


# ═══════════════════════════════════════════════════════════
# 三、Router 契约（阶段 B）
# ═══════════════════════════════════════════════════════════
def test_router_crud_persists(auth_client):
    pid = _mk()
    tid = _mk()
    r = auth_client.post("/project/template/add", json={
        "id": tid, "name": "rt-tpl", "scene": "FUNCTIONAL", "scopeId": pid,
    })
    assert r.status_code == 200
    created = r.json().get("data", {})
    assert created.get("id") == tid
    try:
        got = auth_client.get(f"/project/template/get/{tid}").json()["data"]
        assert got.get("name") == "rt-tpl"
        upd = auth_client.post("/project/template/update", json={
            "id": tid, "name": "rt-tpl2", "scene": "FUNCTIONAL", "scopeId": pid,
        })
        assert upd.json()["data"]["name"] == "rt-tpl2"
    finally:
        auth_client.get(f"/project/template/delete/{tid}")
        _cleanup(tid)
