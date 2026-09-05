"""缺陷缺陷域 DDD 渐进迁移（A→B→C）回归测试。

缺陷域 DDD 领域/应用层已就绪（阶段 A）。本文件覆盖本次推进的 B/C
落地——既有四层门面 `defect_service` 的核心生命周期写路径（create /
update / trash / restore / purge）委托到 DDD 应用服务
`defect_app_service` 后的行为与既有契约一致：
  1. create 委托后返回 schema 与既有 DefectRepo 归一化结果一致（含显式 status）；
  2. update 委托 DDD 聚合根（rename / change_severity / 状态机），不存在抛 404、
     非法值抛 400；
  3. trash / restore / purge 委托 DDD，回收站流转与恢复正常；
  4. 非法严重程度 / 状态迁移由聚合根守护并翻译为既有 ValidationError（400）。
"""
import uuid

from app.core.exceptions import NotFoundError, ValidationError
from app.repositories.defect_repo import DefectRepo
from app.services.defect_service import defect_service

TAG = "ddddefmig"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _cleanup(defect_id):
    try:
        DefectRepo.purge(defect_id)
    except Exception:
        pass


class TestCreateDelegation:
    def test_create_returns_compatible_schema(self):
        """create 委托 DDD 后返回含 id / status / severity 的既有 schema。"""
        d = defect_service.create({
            "title": _mk(),
            "severity": "critical",
            "tags": ["a", "b"],
            "assignee": "u1",
        })
        try:
            assert d is not None
            assert d["id"]
            assert d["status"] == "open"
            assert d["severity"] == "critical"
            # 读回（DDD 落库后经 DefectRepo 归一化行）字段齐全
            got = DefectRepo.get(d["id"])
            assert got["title"] == d["title"]
            assert got["severity"] == "critical"
        finally:
            _cleanup(d["id"])

    def test_create_with_explicit_status(self):
        """create 支持显式 status（兼容 bug_add / 兼容路由以非 open 入库）。"""
        d = defect_service.create({
            "title": _mk(),
            "status": "in_progress",
            "severity": "major",
        })
        try:
            assert d["status"] == "in_progress"
            assert DefectRepo.get(d["id"])["status"] == "in_progress"
        finally:
            _cleanup(d["id"])

    def test_create_invalid_severity_falls_back_to_major(self):
        """非法严重程度沿用既有 create 语义：落到默认 major，不抛错。"""
        d = defect_service.create({"title": _mk(), "severity": "not-a-real-severity"})
        try:
            assert d["severity"] == "major"
            assert DefectRepo.get(d["id"])["severity"] == "major"
        finally:
            _cleanup(d["id"])


class TestUpdateDelegation:
    def _create(self):
        return defect_service.create({"title": _mk(), "severity": "major"})

    def test_update_rename_and_severity(self):
        d = self._create()
        try:
            r = defect_service.update(d["id"], {"title": _mk(), "severity": "minor"})
            assert r["severity"] == "minor"
            got = DefectRepo.get(d["id"])
            assert got["severity"] == "minor"
        finally:
            _cleanup(d["id"])

    def test_update_status_via_state_machine(self):
        """update 委托 DDD 状态机：open -> in_progress -> fixed -> closed。"""
        d = self._create()
        try:
            assert defect_service.update(d["id"], {"status": "in_progress"})["status"] == "in_progress"
            assert defect_service.update(d["id"], {"status": "fixed"})["status"] == "fixed"
            r = defect_service.update(d["id"], {"status": "closed"})
            assert r["status"] == "closed"
        finally:
            _cleanup(d["id"])

    def test_update_nonexistent_raises_not_found(self):
        try:
            defect_service.update("no-such-defect-xyz", {"title": _mk()})
            raise AssertionError("应抛 NotFoundError")
        except NotFoundError:
            pass

    def test_update_invalid_severity_raises_validation_error(self):
        d = self._create()
        try:
            try:
                defect_service.update(d["id"], {"severity": "weird"})
                raise AssertionError("应抛 ValidationError")
            except ValidationError:
                pass
        finally:
            _cleanup(d["id"])


class TestTrashRestorePurgeDelegation:
    def test_trash_restore_roundtrip(self):
        d = defect_service.create({"title": _mk()})
        did = d["id"]
        try:
            # 软删除：活动区读不到、回收站可见
            defect_service.trash(did)
            assert defect_service.get(did) is None
            trash_ids = [t["id"] for t in DefectRepo.list_trash(limit=200)]
            assert did in trash_ids
            # 恢复
            defect_service.restore(did)
            assert defect_service.get(did) is not None
            assert DefectRepo.get(did)["deleted"] == 0
        finally:
            _cleanup(did)

    def test_trash_nonexistent_raises_not_found(self):
        try:
            defect_service.trash("no-such-defect-xyz")
            raise AssertionError("应抛 NotFoundError")
        except NotFoundError:
            pass

    def test_restore_active_defect_raises_not_found(self):
        """对非回收站缺陷 restore：聚合根拒绝 -> 404。"""
        d = defect_service.create({"title": _mk()})
        did = d["id"]
        try:
            try:
                defect_service.restore(did)
                raise AssertionError("应抛 NotFoundError")
            except NotFoundError:
                pass
        finally:
            _cleanup(did)

    def test_purge_delegation(self):
        d = defect_service.create({"title": _mk()})
        did = d["id"]
        try:
            defect_service.trash(did)
            defect_service.purge(did)
            assert DefectRepo.get(did) is None
        finally:
            _cleanup(did)

    def test_batch_restore_purge(self):
        ids = []
        for _ in range(2):
            d = defect_service.create({"title": _mk()})
            defect_service.trash(d["id"])
            ids.append(d["id"])
        try:
            assert defect_service.batch_restore(ids) == 2
            for did in ids:
                assert defect_service.get(did) is not None
            for did in ids:
                defect_service.trash(did)
            assert defect_service.batch_purge(ids) == 2
            for did in ids:
                assert DefectRepo.get(did) is None
        finally:
            for did in ids:
                _cleanup(did)
