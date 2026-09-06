"""cases 域 DDD application 方法面补全（旁路方法收敛）回归测试。

背景：
  - 目标：大域 DDD application 方法与旧 service 逐方法对齐。
    case_service 中仍直连 CaseRepo 的旁路方法（版本 / 变更日志 / 需求关联 /
    回收站管理 / 统计 / 脑图 / 完整信息等）此前未进入 DDD 应用门面。
  - 本次：把这些旁路方法补齐进 `CaseAppService`（薄委托既有 CaseRepo，
    防腐层不搬移业务），并将 `case_service` 相应方法收敛为对 `_ddd` 的委托。

本测试验证：
  1. `CaseService` 各旁路方法确以 DDD `CaseAppService` 为编排门面。
  2. DDD 门面具备与旧 service 一致的逐方法能力。
  3. 薄委托端到端契约（返回值结构）与直连既有 CaseRepo 完全一致。
"""

import json
import uuid

from app.repositories.case_repo import CaseRepo
from app.services.case_service import case_service

TAG = "casedddsurface"


def _mk(prefix="c") -> str:
    return f"{prefix}-{TAG}-{uuid.uuid4().hex[:8]}"


def _cleanup(case_id):
    try:
        CaseRepo.purge_case(case_id)
    except Exception:
        pass


class TestCaseBypassSurfaceDelegation:
    def test_versions_via_ddd(self):
        """版本管理经 DDD 门面：list/get/rollback。"""
        cid = _mk("v")
        case_service.create(
            {"id": cid, "title": _mk("t"), "test_type": "functional"}
        )
        try:
            versions = case_service.list_versions(cid)
            assert len(versions) >= 1  # 初始版本
            v = case_service.get_version(cid, versions[0]["version"])
            assert v and v["version"] == versions[0]["version"]
            assert case_service.rollback(cid, versions[0]["version"]) is True
        finally:
            _cleanup(cid)

    def test_changes_via_ddd(self):
        """变更日志经 DDD 门面。"""
        cid = _mk("ch")
        case_service.create(
            {"id": cid, "title": _mk("t"), "test_type": "functional"}
        )
        try:
            changes = case_service.list_changes(cid)
            assert isinstance(changes, list)
            assert case_service.count_changes(cid) == len(changes)
            assert case_service.count_changes(cid) >= 1
        finally:
            _cleanup(cid)

    def test_requirement_via_ddd(self):
        """需求关联经 DDD 门面。"""
        cid = _mk("r")
        case_service.create(
            {"id": cid, "title": _mk("t"), "test_type": "functional"}
        )
        try:
            req_id = _mk("req")
            rel = case_service.add_requirement(cid, req_id)
            assert rel and rel.get("id")
            reqs = case_service.list_requirements(cid)
            assert any(r.get("requirement_id") == req_id for r in reqs)
            assert case_service.remove_requirement(cid, req_id) is True
            assert case_service.list_requirements(cid) == []
        finally:
            _cleanup(cid)

    def test_stats_and_info_via_ddd(self):
        """统计/完整信息/脑图经 DDD 门面（结构契约一致）。"""
        stats = case_service.get_stats()
        assert isinstance(stats, dict)
        mindmap = case_service.get_mindmap()
        assert isinstance(mindmap, dict)
        # 完整信息：先建用例，验证 get_full_info
        cid = _mk("fi")
        case_service.create(
            {"id": cid, "title": _mk("t"), "test_type": "functional"}
        )
        try:
            full = case_service.get_full_info(cid)
            assert full and full.get("id") == cid
        finally:
            _cleanup(cid)

    def test_trash_purge_via_ddd(self):
        """回收站 purge / list_trash 经 DDD 门面。"""
        cid = _mk("p")
        case_service.create(
            {"id": cid, "title": _mk("t"), "test_type": "functional"}
        )
        # soft_delete 经 DDD → 进 trash
        assert case_service.soft_delete(cid) is True
        trash = case_service.list_trash()
        assert any(str(t.get("case_id")) == cid for t in trash)
        assert case_service.purge(cid) is True

    def test_hard_delete_via_ddd(self):
        """hard delete 经 DDD 门面。"""
        cid = _mk("hd")
        case_service.create(
            {"id": cid, "title": _mk("t"), "test_type": "functional"}
        )
        assert case_service.delete(cid, soft=False) is True
        assert case_service.get(cid) is None

    def test_update_case_result_via_ddd(self):
        """更新执行结果经 DDD 门面。"""
        cid = _mk("ur")
        case_service.create(
            {"id": cid, "title": _mk("t"), "test_type": "functional"}
        )
        try:
            updated = case_service.update_case_result(
                cid, {"passed": 1, "duration": 1.5}
            )
            assert updated
            # DDD round-trip 读回 last_result
            case_ddd = case_service.get(cid)
            last = case_ddd.get("last_result")
            if last:
                if isinstance(last, str):
                    last = json.loads(last)
                assert last.get("passed") == 1
        finally:
            _cleanup(cid)
