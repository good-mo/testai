"""DDD 缺陷试点域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：严重程度守卫、状态机、软删除/恢复。
  2. 应用服务全链路（对接真实 DefectRepo 存储）。
"""
import uuid

import pytest

from app.domain.common.exceptions import DomainValidationError
from app.domain.defects.application.defect_app_service import defect_app_service
from app.domain.defects.application.dto import (
    ChangeStatusCommand,
    CreateDefectCommand,
    DefectListQuery,
    UpdateDefectCommand,
)
from app.domain.defects.domain.value_objects.severity import Severity, SeverityEnum
from app.domain.defects.domain.value_objects.status import DefectStatus, DefectStatusEnum

TAG = "ddddef"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _defect(**kw):
    from app.domain.defects.domain.entities.defect import Defect
    kw.setdefault("defect_id", _mk())
    kw.setdefault("title", "缺陷")
    return Defect(**kw)


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestValueObjects:
    def test_severity_guard(self):
        assert str(Severity("BLOCKER")) == "blocker"
        with pytest.raises(DomainValidationError):
            Severity("P9")

    def test_severity_weight(self):
        assert Severity(SeverityEnum.BLOCKER.value).weight < Severity("trivial").weight

    def test_status_normalize(self):
        assert str(DefectStatus("In_Progress")) == "in_progress"
        assert str(DefectStatus("")) == "open"

    def test_title_required(self):
        with pytest.raises(DomainValidationError):
            _defect(title="")


class TestAggregate:
    def test_rename(self):
        d = _defect()
        d.rename("新标题", "u")
        assert d.title == "新标题"

    def test_rename_empty_rejected(self):
        d = _defect()
        with pytest.raises(DomainValidationError):
            d.rename("", "u")

    def test_state_machine(self):
        d = _defect()
        d.change_status("in_progress", "u")
        assert str(d.status) == "in_progress"
        d.change_status("fixed", "u")
        d.change_status("closed", "u")
        assert str(d.status) == "closed"
        # 允许重开
        d.change_status("open", "u")
        assert str(d.status) == "open"

    def test_illegal_transition_rejected(self):
        d = _defect()  # open
        # open -> in_progress -> fixed -> closed; 直接 open->trashed 不允许
        with pytest.raises(DomainValidationError):
            d.change_status(DefectStatusEnum.TRASHED.value, "u")
        # open -> in_progress，不能一步跳到... 这里验证一个非法：新 open 直接 fixed 是允许的，
        # 用 closed 直接到 wont_fix 之类验证非法（closed 仅可回 open）
        d2 = _defect(status="closed")
        with pytest.raises(DomainValidationError):
            d2.change_status("in_progress", "u")

    def test_soft_delete_restore(self):
        d = _defect()
        d.delete("u")
        assert d.deleted
        with pytest.raises(DomainValidationError):
            d.delete("u")  # 重复删除
        d.restore("u")
        assert not d.deleted
        with pytest.raises(DomainValidationError):
            d.restore("u")  # 不在回收站

    def test_severity_change(self):
        d = _defect(severity="major")
        d.change_severity("critical", "u")
        assert d.severity.value == "critical"

    def test_events_collected(self):
        d = _defect()
        d.change_status("in_progress", "u")
        d.rename("abc", "u")
        names = [type(e).__name__ for e in d.pull_domain_events()]
        assert "DefectStatusChanged" in names
        assert "DefectTitleChanged" in names


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（真实存储）
# ═══════════════════════════════════════════════════════════
@pytest.fixture
def fresh_defect_id():
    case = defect_app_service.create(CreateDefectCommand(
        title=_mk(), severity="blocker", operator="admin",
    ))
    did = case["id"]
    yield did
    # 清理（物理删除，含回收站残留）
    from app.repositories.defect_repo import DefectRepo
    DefectRepo.purge(did)


def test_create_and_get(fresh_defect_id):
    assert defect_app_service.get(fresh_defect_id) is not None


def test_update(fresh_defect_id):
    r = defect_app_service.update(UpdateDefectCommand(
        defect_id=fresh_defect_id, title=_mk(), severity="minor", operator="admin"))
    assert r is not None
    assert r["severity"] == "minor"


def test_status_flow(fresh_defect_id):
    r = defect_app_service.change_status(ChangeStatusCommand(
        defect_id=fresh_defect_id, target_status="in_progress", operator="admin"))
    assert r["status"] == "in_progress"
    r2 = defect_app_service.change_status(ChangeStatusCommand(
        defect_id=fresh_defect_id, target_status="closed", operator="admin"))
    assert r2["status"] == "closed"


def test_delete_restore_roundtrip(fresh_defect_id):
    assert defect_app_service.soft_delete(fresh_defect_id, "admin")
    tr = defect_app_service.list_trash()
    assert tr["total"] >= 1
    assert defect_app_service.restore(fresh_defect_id, "admin")
    g = defect_app_service.get(fresh_defect_id)
    assert g and g["deleted"] == 0


def test_list_and_stats(fresh_defect_id):
    result = defect_app_service.list(DefectListQuery(limit=10))
    assert "list" in result and "total" in result
    st = defect_app_service.stats()
    assert "by_status" in st and "total" in st
