"""DDD script 域 A→B→C 渐进迁移回归测试。

背景
----
`app/domain/script/` DDD 层（阶段 A）就绪后，本测试锁定「阶段 B/C」接入契约：
  - 阶段 C：`app/services/script_service.py` 已收敛为对 `script_app_service`
    的薄委托门面，脚本 CRUD / 执行记录 / 定位器修复 / 统计全部经 DDD 门面；
  - 阶段 B：Router 调用薄 Service → DDD 门面 → 聚合，完成 DDD 路由；
  - 缺失语义保持 404 化（get 缺失返回 None、delete 缺失返回 False）。

本测试以 Service 为界验证迁移后行为与旧契约一致（创建/读取/更新/回收、
缺失语义、健康度执行记录），作为逐域切换的回归基线。
"""
import uuid

from app.repositories.script_repo import ScriptRepo
from app.services.script_service import script_service as svc

TAG = "scrmig"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _cleanup(sid: str) -> None:
    try:
        ScriptRepo.delete(sid)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 一、register / get / list / update 委托 DDD（阶段 C）
# ═══════════════════════════════════════════════════════════
def test_register_and_get_roundtrip():
    name = _mk()
    d = svc.register(name=name, file_path="/a/b.py", framework="pytest",
                     description="desc", locators=[{"name": "btn"}])
    try:
        assert d and d["id"]
        assert d["name"] == name
        assert d["framework"] == "pytest"
        assert d["status"] == "healthy"
        g = svc.get(d["id"])
        assert g is not None
        assert g["name"] == name
        assert g["locators"] == [{"name": "btn"}]
    finally:
        _cleanup(d["id"])


def test_list_by_search():
    name = _mk()
    d = svc.register(name=name, file_path="/search/x.py")
    try:
        rows = [x for x in svc.list(search=name)]
        assert len(rows) == 1
        assert rows[0]["name"] == name
    finally:
        _cleanup(d["id"])


def test_update_roundtrip():
    d = svc.register(name=_mk(), file_path="/u.py")
    try:
        up = svc.update(d["id"], name="updated-name", framework="playwright")
        assert up and up["name"] == "updated-name"
        assert up["framework"] == "playwright"
    finally:
        _cleanup(d["id"])


def test_missing_semantics():
    missing = f"nope_{uuid.uuid4().hex[:6]}"
    assert svc.get(missing) is None
    assert svc.update(missing, name="x") is None
    assert svc.delete(missing) is False


# ═══════════════════════════════════════════════════════════
# 二、执行记录 / 统计（委托 DDD 门面）
# ═══════════════════════════════════════════════════════════
def test_record_execution_and_list_executions():
    d = svc.register(name=_mk(), file_path="/exec.py")
    try:
        r = svc.record_execution(d["id"], success=True, duration=1.5)
        assert r and r.get("success") is True
        execs = svc.list_executions(d["id"])
        assert isinstance(execs, list)
    finally:
        _cleanup(d["id"])


def test_stats_shape():
    s = svc.get_stats()
    assert isinstance(s, dict)


def test_evaluate_and_recommend():
    ev = svc.evaluate_selector("css", "#login-btn")
    rec = svc.recommend_strategy("#login-btn", "css")
    assert ev is not None
    assert rec is not None


# ═══════════════════════════════════════════════════════════
# 三、Router 契约（阶段 B）
# ═══════════════════════════════════════════════════════════
def test_router_list_scripts(anon_client):
    r = anon_client.get("/api/scripts")
    assert r.status_code == 200
    data = r.json().get("data", {})
    assert "scripts" in data
    assert "total" in data


def test_router_get_missing_404(anon_client):
    r = anon_client.get(f"/api/scripts/nope_{uuid.uuid4().hex[:6]}")
    assert r.status_code == 404


def test_router_stats(anon_client):
    r = anon_client.get("/api/scripthealth/stats")
    assert r.status_code == 200
