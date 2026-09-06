"""缺陷域旁路方法面 DDD 收敛迁移回归测试。

`defect_service` 的核心生命周期（create/update/trash/restore/purge/list/list_trash）
已收敛委托 `defect_app_service`。本文件补齐本次推进的**旁路方法面**收敛——
评论（list_comments/create_comment/update_comment/delete_comment）、
auto_create_from_result、permanent_delete 也改为委托 DDD 门面，使
`defect_service` 不再直连 `DefectRepo` 的旁路数据访问：

  1. 评论四方法确实委托 DDD 门面（monkeypatch 断言）；
  2. auto_create_from_result 委托 DDD 门面；
  3. permanent_delete 委托 DDD 门面（不存在抛 404）；
  4. 端到端契约不回归：创建评论→列表→更新→删除、永久删除闭环。
"""
import uuid

from app.core.exceptions import NotFoundError
from app.domain.defects.application.defect_app_service import (
    defect_app_service as ddd,
)
from app.repositories.defect_repo import DefectRepo
from app.services.defect_service import defect_service as svc

TAG = "ddddefbyp"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _mk_defect() -> str:
    did = DefectRepo.create({
        "title": _mk(), "severity": "major", "status": "open",
    })["id"]
    return did


def _cleanup_defect(did):
    try:
        DefectRepo.delete(did, permanent=True)
    except Exception:
        pass


def _cleanup_comments(did):
    try:
        for c in DefectRepo.list_comments(did):
            DefectRepo.delete_comment(c["id"])
    except Exception:
        pass


def test_create_comment_delegates_to_ddd(monkeypatch):
    """create_comment 委托 DDD 门面。"""
    did = _mk_defect()
    called = []
    real = ddd.create_comment

    def fake(cmd):
        called.append((cmd.bug_id, cmd.content))
        return real(cmd)

    monkeypatch.setattr(ddd, "create_comment", fake)
    try:
        svc.create_comment(did, content="hello")
        assert called and called[0] == (did, "hello")
    finally:
        _cleanup_comments(did)
        _cleanup_defect(did)


def test_list_update_delete_comment_delegates_to_ddd(monkeypatch):
    """list/update/delete_comment 委托 DDD 门面。"""
    did = _mk_defect()
    cid = svc.create_comment(did, content="orig", create_user="u1")
    cid = cid["id"]

    seen = []
    real_list = ddd.list_comments
    real_update = ddd.update_comment
    real_delete = ddd.delete_comment

    def fake_list(q):
        seen.append(("list", q.bug_id))
        return real_list(q)

    def fake_update(cmd):
        seen.append(("update", cmd.comment_id))
        return real_update(cmd)

    def fake_delete(cmd):
        seen.append(("delete", cmd.comment_id))
        return real_delete(cmd)

    monkeypatch.setattr(ddd, "list_comments", fake_list)
    monkeypatch.setattr(ddd, "update_comment", fake_update)
    monkeypatch.setattr(ddd, "delete_comment", fake_delete)
    try:
        rows = svc.list_comments(did)
        assert ("list", did) in seen
        assert any(r["id"] == cid for r in rows)

        updated = svc.update_comment(cid, content="edited")
        assert updated["content"] == "edited"
        assert ("update", cid) in seen

        ok = svc.delete_comment(cid)
        assert ok is True
        assert ("delete", cid) in seen
        assert all(r["id"] != cid for r in svc.list_comments(did))
    finally:
        _cleanup_comments(did)
        _cleanup_defect(did)


def test_auto_create_delegates_to_ddd(monkeypatch):
    """auto_create_from_result 委托 DDD 门面（失败触发、通过不创建）。"""
    did = None
    called = []
    real = ddd.auto_create_from_result

    def fake(cmd):
        called.append(cmd.file_path)
        return real(cmd)

    monkeypatch.setattr(ddd, "auto_create_from_result", fake)
    try:
        # passed=True → 不创建、仍经 DDD
        svc.auto_create_from_result("f.py", {"passed": True})
        assert called == ["f.py"]

        # 失败 → 创建一条缺陷
        created = svc.auto_create_from_result(
            "f.py", {"passed": False, "stderr": "AssertionError: boom"})
        assert created is not None
        did = created["id"]
        assert "断言失败" in created["title"]
    finally:
        if did:
            _cleanup_defect(did)


def test_permanent_delete_delegates_to_ddd(monkeypatch):
    """permanent_delete 委托 DDD 门面；不存在抛 404。"""
    did = _mk_defect()
    called = []
    real = ddd.permanent_delete

    def fake(cmd):
        called.append(cmd.defect_id)
        return real(cmd)

    monkeypatch.setattr(ddd, "permanent_delete", fake)
    try:
        svc.permanent_delete(did)
        assert called == [did]
        # 已彻底删除，再次删抛 404
        try:
            svc.permanent_delete(did)
            raise AssertionError("应抛 NotFoundError")
        except NotFoundError:
            pass
    finally:
        _cleanup_defect(did)
