"""test_plan 域 DDD 迁移（阶段 A→B→C）回归测试。

背景：
  - 阶段 A：`app/domain/test_plan/` DDD 聚合/应用层就绪（`TestPlanAppService`）。
  - 阶段 B/C：`app/services/test_plan_service.py` 计划聚合生命周期
    （create / get / delete / archive / list / 统计）委托 DDD 应用服务，
    经 `_to_legacy` 契约桥补全既有 Web 层读取的元数据列，Service 变薄为门面。

本测试验证：
  1. `TestPlanService` 内部确以 DDD `TestPlanAppService` 为编排门面（接入生效）。
  2. 计划创建/读取/归档/删除走 DDD，业务不变量（空名拒绝）由聚合根守护。
  3. `_to_legacy` 契约桥保证返回结构兼容既有 Web 层
     （含 metadata / execution_rate / pass_rate）。
  4. 未迁移的旁路（计划头通用编辑、关联用例、统计、模块）仍保持可用、可回滚。
"""

import json
import uuid

import pytest

from app.domain.common.exceptions import DomainValidationError
from app.repositories.test_plan_repo import TestPlanRepo
from app.services.test_plan_service import test_plan_service

TAG = "dddtestplanmig"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def plan_id():
    p = test_plan_service.create_plan(name=_mk(), priority="P1")
    yield p["id"]
    # 清理
    existing = test_plan_service.get_plan(p["id"])
    if existing:
        test_plan_service.delete_plan(p["id"])


class TestStageBConsumption:
    def test_service_is_ddd_backed(self):
        """阶段 B/C：门面确以 DDD 应用服务编排。"""
        from app.services.test_plan_service import TestPlanService

        assert type(TestPlanService()._ddd).__name__ == "TestPlanAppService"

    def test_create_returns_legacy_contract(self):
        """创建经 DDD，返回结构兼容既有 `_plan_from_row`（契约桥）。"""
        p = test_plan_service.create_plan(
            name=_mk(),
            priority="P0",
            pass_threshold=90,
            tags=["回归"],
        )
        try:
            for key in (
                "id",
                "name",
                "priority",
                "status",
                "metadata",
                "execution_rate",
                "pass_rate",
                "pass_threshold",
                "tags",
            ):
                assert key in p, f"missing {key}"
            assert p["priority"] == "P0"
            assert p["pass_threshold"] == 90
            assert p["tags"] == ["回归"]
        finally:
            test_plan_service.delete_plan(p["id"])

    def test_create_rejects_empty_name_via_domain(self, plan_id):
        """阶段 C：规则下沉——空名等不变量由 DDD 聚合根守护，门面不再兜底。"""
        with pytest.raises(DomainValidationError):
            test_plan_service.create_plan(name="")

    def test_get_roundtrip_preserves_contract(self, plan_id):
        g = test_plan_service.get_plan(plan_id)
        assert g is not None
        assert g["id"] == plan_id
        assert "metadata" in g and "execution_rate" in g and "pass_rate" in g

    def test_metadata_via_legacy_edit_still_readable(self, plan_id):
        """计划头通用编辑（metadata 等应用层专有列）仍走既有仓库，读取契约不破。"""
        # 直接落库模拟既有 metadata 持久化路径（TestPlanRepo.update_plan 不含 metadata，
        # 由直连/既有旁路负责；此处验证 get 契约桥能透出存储行元数据）。
        TestPlanRepo._conn().execute(
            "UPDATE test_plans SET metadata=? WHERE id=?",
            (json.dumps({"sort_order": 7}), plan_id),
        )
        TestPlanRepo._conn().commit()
        g = test_plan_service.get_plan(plan_id)
        assert g["metadata"] == {"sort_order": 7}

    def test_archive_through_ddd(self, plan_id):
        assert test_plan_service.archive_plan(plan_id) is True
        assert test_plan_service.get_plan(plan_id)["status"] == "archived"

    def test_delete_through_ddd(self, plan_id):
        assert test_plan_service.delete_plan(plan_id) is True
        assert test_plan_service.get_plan(plan_id) is None

    def test_non_migrated_sidecar_still_works(self, plan_id):
        """未迁移旁路（关联用例、统计、计划头编辑）保持可用、可回滚。"""
        # 关联用例（存储级双轨并存）
        rel = test_plan_service.add_plan_case(plan_id, _mk(), "functional")
        assert rel is not None and rel.get("id")
        cases = test_plan_service.list_plan_cases(plan_id)
        assert len(cases) == 1
        assert test_plan_service.update_plan_case_status(cases[0]["id"], "passed")
        st = test_plan_service.get_plan_statistics(plan_id)
        assert st["total"] == 1 and st["passed"] == 1
        # 计划头通用编辑
        upd = test_plan_service.update_plan(plan_id, name=_mk())
        assert upd is not None and upd["name"] != ""
        # 清理关联用例
        test_plan_service.remove_plan_case(cases[0]["id"])
