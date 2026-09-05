"""DDD project_version 域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/project_version/` DDD 层（阶段 A）此前是分层齐全却从未被生产引用的
「未接线骨架」。issue #708 选定 Option A「接死为活」，本测试锁定 project_version
域的阶段 C 薄门面接线契约：
  - `app/services/project_version_service.py` 收敛为对 `project_version_app_service`
    的薄委托门面，对外方法签名与返回结构（camelCase 版本对象，createTime 仍为
    历史秒口径）不变，调用方 `project_compat_extra2` 零改动；
  - 版本「功能开关」委托已接线的 project_app_config 域（Round 1）；
  - DDD 应用服务补齐 `set_latest` / `toggle_status` 用例。

并锁定历史缺陷的修复：
  ① `ProjectVersionRepoAdapter.save` 新建不再忽略聚合 id
     → 创建返回的 id 与落库 id 一致（此前双 id 漂移，落库根本查不到）；
  ② `save` 更新分支补持久化 publish_time / update_time
     → 读聚合→改 publishTime→存回 不再丢字段。

本测试以 Service 为界验证接线后行为与旧契约一致，作为逐域切换回归基线。
"""
import uuid

from app.domain.project_version.application.project_version_app_service import (
    project_version_app_service as pv_ddd,
)
from app.repositories.project_version_repo import ProjectVersionRepo, project_version_repo
from app.services.project_version_service import project_version_service as pv_svc


# 清理历史测试残留项目数据可能干扰 DB 状态，用随机 project_id 隔离
def _pid(prefix="DDD-PV"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════
# 一、薄门面确实委托 DDD 应用服务
# ═══════════════════════════════════════════════════════════
def test_service_delegates_to_ddd_app_service(monkeypatch):
    """list/get/add/update/delete/set_latest/toggle_status 均委托 DDD 门面。"""
    calls = []

    def fake_list(cmd):
        calls.append(("list", cmd.project_id, cmd.keyword))
        return []

    def fake_get(cmd):
        calls.append(("get", cmd.version_id))
        return None

    def fake_create(cmd):
        calls.append(("create", cmd.project_id, cmd.name))
        return {"id": "v1", "projectId": cmd.project_id, "name": cmd.name,
                "status": False, "latest": False, "publishTime": 0,
                "createTime": 1788500000000, "createUser": "admin"}

    def fake_update(cmd):
        calls.append(("update", cmd.version_id, cmd.name))
        return {"id": cmd.version_id, "name": cmd.name}

    def fake_delete(cmd):
        calls.append(("delete", cmd.version_id))
        return True

    def fake_options(project_id):
        calls.append(("options", project_id))
        return []

    monkeypatch.setattr(pv_ddd, "list", fake_list)
    monkeypatch.setattr(pv_ddd, "get", fake_get)
    monkeypatch.setattr(pv_ddd, "create", fake_create)
    monkeypatch.setattr(pv_ddd, "update", fake_update)
    monkeypatch.setattr(pv_ddd, "delete", fake_delete)
    monkeypatch.setattr(pv_ddd, "options", fake_options)

    assert pv_svc.list_items("proj", "kw") == []
    assert pv_svc.get_item("v1") is None
    assert pv_svc.add("proj", "n") is not None
    assert pv_svc.update("v1", {"name": "n2"}) is not None
    assert pv_svc.delete("v1") is True
    assert pv_svc.options("proj") == []
    assert calls[0] == ("list", "proj", "kw")
    assert calls[1] == ("get", "v1")
    assert calls[2][0:2] == ("create", "proj")
    assert calls[3] == ("update", "v1", "n2")
    assert calls[4] == ("delete", "v1")
    assert calls[5] == ("options", "proj")


def test_service_set_latest_and_toggle_delegate_to_ddd(monkeypatch):
    """set_latest / toggle_status 委托 DDD 新增用例，缺版本返回 None。"""
    monkeypatch.setattr(pv_ddd, "set_latest", lambda version_id: {
        "id": version_id, "name": "x", "latest": True})
    monkeypatch.setattr(pv_ddd, "toggle_status", lambda version_id: {
        "id": version_id, "name": "x", "status": True})

    got = pv_svc.set_latest("v9")
    assert got is not None and got["id"] == "v9"
    got2 = pv_svc.toggle_status("v9")
    assert got2 is not None and got2["status"] is True


# ═══════════════════════════════════════════════════════════
# 二、创建返回 id == 落库 id（历史双 id 漂移缺陷修复）
# ═══════════════════════════════════════════════════════════
def test_add_returns_real_stored_id():
    """service.add 经 DDD 接线后，返回 id 与落库 id 一致。"""
    pid = _pid()
    v = pv_svc.add(pid, "v1.0", "desc", status=False, latest=False,
                   publish_time=1700000000000)
    assert v is not None
    vid = v["id"]
    assert vid
    stored = ProjectVersionRepo.get_version(vid)
    assert stored is not None, "落库行应存在（此前双 id 漂移导致查不到）"
    assert stored["id"] == vid
    assert stored["name"] == "v1.0"
    assert stored["project_id"] == pid
    # 清理
    ProjectVersionRepo.delete_version(vid)


def test_service_camelcase_and_feature_roundtrip():
    """service 驼峰版本对象 + 版本功能开关读写契约保持。"""
    pid = _pid()
    v = pv_svc.add(pid, "v2.0")
    vid = v["id"]
    for key in ("id", "name", "description", "status", "latest",
                "publishTime", "createTime", "createUser", "projectId"):
        assert key in v, f"版本项缺字段 {key}"
    assert v["projectId"] == pid
    assert v["status"] is False and v["latest"] is False

    # options
    opts = pv_svc.options(pid)
    assert opts and opts[0]["id"] == vid and opts[0]["enable"] is False

    # 版本功能开关（project_app_configs 委托）
    assert pv_svc.is_feature_enabled(pid) is False
    pv_svc.set_feature_enabled(pid, True)
    assert pv_svc.is_feature_enabled(pid) is True
    assert pv_svc.toggle_feature_enabled(pid) is False
    assert pv_svc.is_feature_enabled(pid) is False

    try:
        ProjectVersionRepo.delete_version(vid)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 三、DDD 应用层 set_latest / toggle_status 语义
# ═══════════════════════════════════════════════════════════
def test_set_latest_and_toggle_status_real():
    """set_latest 清除同项目其他 latest；toggle_status 取反。"""
    pid = _pid()
    v1 = pv_svc.add(pid, "v1")
    v2 = pv_svc.add(pid, "v2")
    try:
        # set_latest(v1) 后 v1 latest、v2 非 latest
        pv_svc.set_latest(v1["id"])
        assert project_version_repo.get_version(v1["id"])["latest"] == 1
        assert project_version_repo.get_version(v2["id"])["latest"] == 0
        # set_latest(v2) 后 v2 latest、v1 被清除
        pv_svc.set_latest(v2["id"])
        assert project_version_repo.get_version(v2["id"])["latest"] == 1
        assert project_version_repo.get_version(v1["id"])["latest"] == 0

        # toggle_status 取反
        before = bool(project_version_repo.get_version(v1["id"])["status"])
        got = pv_svc.toggle_status(v1["id"])
        assert got is not None
        assert got["status"] is (not before)

        # 不存在的版本返回 None
        assert pv_svc.set_latest("no-such-version") is None
        assert pv_svc.toggle_status("no-such-version") is None
        assert pv_svc.update("no-such-version", {"name": "x"}) is None
        assert pv_svc.get_item("no-such-version") is None
        assert pv_svc.delete("no-such-version") is False
    finally:
        ProjectVersionRepo.delete_version(v1["id"])
        ProjectVersionRepo.delete_version(v2["id"])


# ═══════════════════════════════════════════════════════════
# 四、save 更新分支补持久化 publish_time（历史缺陷修复）
# ═══════════════════════════════════════════════════════════
def test_update_persists_publish_time_and_partial_fields():
    """读聚合→改 publishTime/name→存回 不丢字段（save 更新分支补持久化）。"""
    pid = _pid()
    v = pv_svc.add(pid, "orig", publish_time=1700000000000)
    vid = v["id"]
    try:
        up = pv_svc.update(vid, {"name": "renamed", "publishTime": 1600000000000})
        assert up is not None
        assert up["name"] == "renamed"
        assert up["publishTime"] == 1600000000000
        stored = ProjectVersionRepo.get_version(vid)
        assert stored["name"] == "renamed"
        assert stored["publish_time"] == 1600000000000.0

        # 部分更新：仅给 description，不影响 name/status
        up2 = pv_svc.update(vid, {"description": "only-desc"})
        assert up2["description"] == "only-desc"
        assert up2["name"] == "renamed"  # 未变
    finally:
        ProjectVersionRepo.delete_version(vid)
