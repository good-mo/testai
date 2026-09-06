"""DDD 用例试点域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：值对象守卫、状态机、评审流转、软删除/恢复。
  2. 应用服务全链路（对接真实 CaseRepo 存储）。
"""
import uuid

import pytest

from app.domain.cases.application.case_app_service import case_app_service
from app.domain.cases.application.dto import (
    ChangeStatusCommand,
    CreateCaseCommand,
    DeleteCaseCommand,
    ListQuery,
    RestoreCaseCommand,
    ReviewCommand,
    UpdateCaseCommand,
)
from app.domain.cases.domain.value_objects.case_status import CaseStatusEnum
from app.domain.cases.domain.value_objects.priority import Priority
from app.domain.common.exceptions import DomainValidationError


def _case(**kw):
    from app.domain.cases.domain.entities.case import TestCase
    return TestCase(**kw)

TAG = "dddd"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestValueObjects:
    def test_priority_guard(self):
        assert str(Priority("p1")) == "P1"
        with pytest.raises(DomainValidationError):
            Priority("P9")

    def test_priority_weight(self):
        assert Priority("P0").weight < Priority("P3").weight

    def test_case_status_normalize(self):
        c = _case(case_id="c1", title="t", status="review")
        assert str(c.status) == "review"


class TestAggregate:
    def test_rename(self):
        c = _case(case_id="c1", title="旧")
        c.rename("新", "u")
        assert c.title == "新"

    def test_rename_empty_rejected(self):
        c = _case(case_id="c1", title="旧")
        with pytest.raises(DomainValidationError):
            c.rename("", "u")

    def test_state_machine(self):
        c = _case(case_id="c1", title="t")
        c.change_status(CaseStatusEnum.REVIEW.value, "u")
        assert str(c.status) == "review"
        c.review(outcome="approved", reviewer="qa")
        assert str(c.status) == "approved"
        # approved 不可退回 review
        with pytest.raises(DomainValidationError):
            c.change_status(CaseStatusEnum.REVIEW.value, "u")

    def test_soft_delete_restore(self):
        c = _case(case_id="c1", title="t")
        c.delete("u", "reason")
        assert c.deleted
        assert str(c.status) == "deprecated"
        c.restore("u")
        assert not c.deleted
        assert str(c.status) == "draft"

    def test_delete_twice_rejected(self):
        c = _case(case_id="c1", title="t")
        c.delete("u")
        with pytest.raises(DomainValidationError):
            c.delete("u")

    def test_events_collected(self):
        c = _case(case_id="c1", title="t")
        c.rename("t2", "u")
        events = c.pull_domain_events()
        assert len(events) == 1
        assert type(events[0]).__name__ == "CaseTitleChanged"


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（真实存储）
# ═══════════════════════════════════════════════════════════
@pytest.fixture
def fresh_case_id():
    from app.repositories.case_repo import CaseRepo
    case = case_app_service.create(CreateCaseCommand(
        title=_mk(), priority="P1", test_type="api", operator="admin",
    ))
    cid = case["id"]
    yield cid
    # 清理（物理删除，含子表）
    try:
        CaseRepo.hard_delete(cid)
    except Exception:
        pass


def test_create_and_get(fresh_case_id):
    assert case_app_service.get(fresh_case_id) is not None


def test_update(fresh_case_id):
    r = case_app_service.update(UpdateCaseCommand(
        case_id=fresh_case_id, title=_mk(), operator="admin",
    ))
    assert r is not None


def test_review_flow(fresh_case_id):
    case_app_service.change_status(
        ChangeStatusCommand(case_id=fresh_case_id, target_status="review", operator="admin"))
    rv = case_app_service.review(ReviewCommand(
        case_id=fresh_case_id, outcome="approved", reviewer="qa", comment="ok"))
    assert rv["status"] == "approved"


def test_delete_restore_roundtrip(fresh_case_id):
    assert case_app_service.soft_delete(DeleteCaseCommand(
        case_id=fresh_case_id, operator="admin", reason="清理"))
    tr = case_app_service.list_trash()
    assert tr["total"] >= 1
    assert case_app_service.restore(RestoreCaseCommand(case_id=fresh_case_id, operator="admin"))
    g = case_app_service.get(fresh_case_id)
    assert g and g["status"] == "draft"


def test_list_query(fresh_case_id):
    result = case_app_service.list_cases(ListQuery(limit=10))
    assert "list" in result and "total" in result
