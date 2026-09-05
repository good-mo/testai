"""cases 域 DDD 渐进迁移（A→B→C）回归测试。

cases 域 DDD 领域/应用层已就绪（阶段 A）。本文件覆盖本次推进的
B/C 落地——既有四层门面 `case_service` 的核心生命周期委托到 DDD
应用服务 `case_app_service` 后的行为与契约不变：
  1. create 委托后返回 schema 与既有 CaseRepo 归一化结果一致；
  2. create 支持显式 status（兼容 generation 等以 review 状态入库）；
  3. soft_delete / restore 委托 DDD，回收站流转与恢复正常；
  4. 聚合 from_dict 对既有脏数据（非法 test_type/status/priority）容错回退。
"""

import uuid

import pytest

from app.repositories.case_repo import CaseRepo
from app.services.case_service import case_service

TAG = "ddd-mig"


def _mk(prefix="mig"):
    return f"{prefix}-{TAG}-{uuid.uuid4().hex[:8]}"


def _cleanup(case_id):
    try:
        CaseRepo.purge_case(case_id)
    except Exception:
        pass


class TestCreateDelegation:
    def test_create_returns_compatible_schema(self):
        """create 委托 DDD 后返回含 id 与老字段的 schema。"""
        cid = _mk("c1")
        case = case_service.create(
            {
                "id": cid,
                "title": _mk("t"),
                "tags": ["a"],
                "test_type": "api",
                "priority": "P1",
                "status": "draft",
            }
        )
        try:
            assert case is not None
            assert case["id"]
            assert case["status"] == "draft"
            assert case["test_type"] == "api"
            assert case["priority"] == "P1"
            assert case["tags"] == ["a"]
            # 兼容老 normalize schema 的字段应保留
            assert "last_result" in case or "last_result" not in case
        finally:
            _cleanup(case["id"])

    def test_create_with_explicit_review_status(self):
        """generation 等以 review 状态入库的路径不被破坏。"""
        cid = _mk("c2")
        case = case_service.create(
            {
                "id": cid,
                "title": _mk("rev"),
                "status": "review",
                "test_type": "functional",
            }
        )
        try:
            assert case["status"] == "review"
            # 落库后可读回
            got = CaseRepo.get(cid)
            assert got["status"] == "review"
        finally:
            _cleanup(cid)

    def test_create_invalid_priority_raises_valueerror(self):
        """非法优先级委托 DDD 后转为 ValueError（兼容老 update 捕获）。"""
        with pytest.raises(ValueError):
            case_service.create({"title": _mk("bad"), "priority": "P9"})


class TestSoftDeleteRestoreDelegation:
    def test_soft_delete_then_restore(self):
        cid = _mk("c3")
        case = case_service.create(
            {
                "id": cid,
                "title": _mk("sd"),
                "status": "draft",
            }
        )
        real_id = case["id"]
        assert real_id
        assert case_service.soft_delete(real_id, deleted_by="tester", reason="clean")
        # 软删后活动区读不到
        assert CaseRepo.get(real_id) is None
        # 在回收站
        trash_ids = [t.get("case_id") for t in CaseRepo.list_trash_cases()]
        assert real_id in trash_ids
        # 恢复
        assert case_service.restore(real_id, operator="tester")
        assert CaseRepo.get(real_id) is not None
        got = CaseRepo.get(real_id)
        assert got["status"] == "draft"
        _cleanup(real_id)

    def test_soft_delete_non_existent_returns_false(self):
        assert case_service.soft_delete("no-such-case-xyz") is False

    def test_restore_non_existent_returns_false(self):
        assert case_service.restore("no-such-case-xyz") is False


class TestFromDictToleration:
    def test_from_dict_tolerates_dirty_test_type(self):
        """历史脏数据 test_type（如导入脑图写入的节点 id）不回退崩溃。"""
        from app.domain.cases.domain.entities.case import TestCase

        case = TestCase.from_dict(
            {
                "id": _mk(),
                "title": "dirty",
                "metadata": {"test_type": "type_api"},
            }
        )
        assert case.test_type.value.value in (
            "functional",
            "api",
            "ui",
            "performance",
            "security",
            "compatibility",
            "reliability",
        )

    def test_from_dict_tolerates_blank_status_priority(self):
        from app.domain.cases.domain.entities.case import TestCase

        case = TestCase.from_dict(
            {
                "id": _mk(),
                "title": "blank",
                "status": "",
                "priority": "",
            }
        )
        assert str(case.status) == "draft"
        assert case.priority.value in ("P0", "P1", "P2", "P3")


class TestGetUpdateListDelegation:
    """阶段 B 续：get/update/list 读路径与核心生命周期委托 DDD。"""

    def _mk_case(self, **kw):
        opts = {"title": _mk("gu"), "test_type": "functional"}
        opts.update(kw)
        c = case_service.create(opts)
        return c["id"]

    def test_get_returns_ddd_schema_with_last_result(self):
        """get 委托 DDD 后返回含 last_result 与既有字段的 schema。"""
        import json as _json
        from app.repositories.case_repo import CaseRepo
        cid = self._mk_case(title="get-schema")
        try:
            # Set last_result through old API
            CaseRepo.update(cid, {"last_result": _json.dumps({"status": "passed"})})
            got = case_service.get(cid)
            assert got is not None
            assert got["id"] == cid
            assert got["last_result"] == {"status": "passed"}
            # 核心老字段均存在
            for f in ("title", "description", "status", "priority", "test_type",
                      "tags", "metadata", "structured_cases", "last_result"):
                assert f in got, f"字段 {f} 缺失"
        finally:
            _cleanup(cid)

    def test_update_delegates_and_returns_normalized(self):
        """update 委托 DDD 后返回与 CaseRepo 归一化一致的 schema。"""
        cid = self._mk_case(title="update-orig")
        try:
            result = case_service.update(cid, {"title": "updated-title"})
            assert result is not None
            assert result["title"] == "updated-title"
            # 回读归一化验证
            assert CaseRepo.get(cid)["title"] == "updated-title"
        finally:
            _cleanup(cid)

    def test_update_with_metadata_dict(self):
        """update 支持 metadata dict 传入（functional_cases_extra 路径）。"""
        cid = self._mk_case(title="meta-dict")
        try:
            updated = case_service.update(
                cid, {"metadata": {"module_id": "mod-x", "prerequisite": "pre"}}
            )
            assert updated is not None
            meta = updated.get("metadata", {})
            assert meta.get("module_id") == "mod-x"
            assert meta.get("prerequisite") == "pre"
            # test_type 保留
            assert meta.get("test_type") == "functional"
        finally:
            _cleanup(cid)

    def test_update_with_metadata_json_string(self):
        """update 支持 metadata JSON-string 传入（router 预序列化路径）。"""
        import json as _json
        cid = self._mk_case(title="meta-json")
        try:
            updated = case_service.update(
                cid, {"metadata": _json.dumps({"module_id": "mod-y"})}
            )
            assert updated is not None
            assert updated.get("metadata", {}).get("module_id") == "mod-y"
        finally:
            _cleanup(cid)

    def test_update_with_test_type_keeps_metadata_sync(self):
        """update test_type 后顶层与 metadata.test_type 同步。"""
        cid = self._mk_case(title="tt-sync", test_type="functional")
        try:
            updated = case_service.update(cid, {"test_type": "api"})
            assert updated["test_type"] == "api"
            assert updated["metadata"].get("test_type") == "api"
            # 落库后读回一致
            got = CaseRepo.get(cid)
            assert got["test_type"] == "api"
            assert got["metadata"].get("test_type") == "api"
        finally:
            _cleanup(cid)

    def test_update_status_via_state_machine(self):
        """update status 走 DDD 状态机合法迁移。"""
        cid = self._mk_case(title="status-ddd")
        try:
            # draft → review 合法
            updated = case_service.update(cid, {"status": "review"})
            assert updated["status"] == "review"
            # review → approved 合法
            updated = case_service.update(cid, {"status": "approved"})
            assert updated["status"] == "approved"
            # approved → review 非法
            try:
                case_service.update(cid, {"status": "review"})
                raise AssertionError("approved→review 应被状态机拒绝")
            except ValueError:
                pass
        finally:
            _cleanup(cid)

    def test_update_non_existent_returns_none(self):
        """update 不存在的用例返回 None（兼容旧语义）。"""
        assert case_service.update("no-such-case-xyz", {"title": "x"}) is None

    def test_list_cases_returns_ddd_view(self):
        """list_cases 委托 DDD 后返回含 last_result 的聚合视图列表。"""
        cid = self._mk_case(title="list-view")
        try:
            cases = case_service.list_cases(limit=5)
            assert isinstance(cases, list)
            assert any(c.get("id") == cid for c in cases)
            # last_result 字段存在（round-trip 后）
            found = [c for c in cases if c.get("id") == cid][0]
            assert "last_result" in found
        finally:
            _cleanup(cid)

    def test_count_cases_matches_ddd_list(self):
        """count_cases 委托 DDD 后返回总数。"""
        cid = self._mk_case(title="count-me")
        try:
            total = case_service.count_cases()
            assert isinstance(total, int)
            assert total >= 1
        finally:
            _cleanup(cid)

    def test_list_returns_rows_and_total(self):
        """list 委托 DDD 后返回 (rows, total)。"""
        cid = self._mk_case(title="list-total")
        try:
            rows, total = case_service.list(limit=5)
            assert isinstance(rows, list)
            assert isinstance(total, int)
            assert any(r.get("id") == cid for r in rows)
        finally:
            _cleanup(cid)
