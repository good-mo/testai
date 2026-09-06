"""DDD 用例评审域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：评审状态机、值对象守卫、关联用例、评审结果、软删除。
  2. 应用服务全链路（对接真实 CaseReviewRepo 存储）。
"""
import os
import sys
import uuid

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app.domain.case_review.domain.entities.case_review import CaseReview
from app.domain.case_review.domain.exceptions import InvalidReviewTransition
from app.domain.case_review.domain.value_objects.case_result import (
    CaseReviewResult,
    CaseReviewResultEnum,
)
from app.domain.case_review.domain.value_objects.pass_rule import (
    ReviewPassRule,
    ReviewPassRuleEnum,
)
from app.domain.case_review.domain.value_objects.review_status import (
    ReviewStatus,
    ReviewStatusEnum,
)
from app.domain.common.exceptions import DomainValidationError

TAG = "dddcrv"  # 测试标识，便于清理


def _mk(prefix=TAG) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _review(**kw):
    kw.setdefault("review_id", _mk())
    kw.setdefault("name", "评审单测")
    return CaseReview(**kw)


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestValueObjects:
    def test_status_normalize(self):
        assert str(ReviewStatus("underway")) == "UNDERWAY"
        assert str(ReviewStatus("prepared")) == "PREPARED"
        assert str(ReviewStatus("")) == "UNDERWAY"  # 默认

    def test_status_invalid_rejected(self):
        with pytest.raises(DomainValidationError):
            ReviewStatus("NONEXISTENT")

    def test_status_transitions(self):
        # UNDERWAY -> PREPARED / COMPLETED 合法
        s = ReviewStatus(ReviewStatusEnum.UNDERWAY.value)
        assert s.can_transition_to(ReviewStatus("COMPLETED"))
        assert s.can_transition_to(ReviewStatus("PREPARED"))

        # COMPLETED -> UNDERWAY 合法（可重新开启）
        c = ReviewStatus("COMPLETED")
        assert c.can_transition_to(ReviewStatus("UNDERWAY"))
        assert not c.can_transition_to(ReviewStatus("PREPARED"))

    def test_case_result_normalize(self):
        assert str(CaseReviewResult("pass")) == "PASS"
        assert str(CaseReviewResult("un_pass")) == "UN_PASS"
        assert str(CaseReviewResult("")) == "UN_REVIEWED"

    def test_case_result_is_reviewed(self):
        assert CaseReviewResult("PASS").is_reviewed is True
        assert CaseReviewResult("UN_PASS").is_reviewed is True
        assert CaseReviewResult("RE_REVIEWED").is_reviewed is True
        assert CaseReviewResult("UN_REVIEWED").is_reviewed is False
        assert CaseReviewResult("UNDER_REVIEWED").is_reviewed is False

    def test_pass_rule_normalize(self):
        assert str(ReviewPassRule("single")) == "SINGLE"
        assert str(ReviewPassRule("ALL")) == "ALL"
        assert str(ReviewPassRule("")) == "SINGLE"  # 默认

    def test_pass_rule_invalid_rejected(self):
        with pytest.raises(DomainValidationError):
            ReviewPassRule("INVALID")


class TestAggregate:
    def test_name_required(self):
        with pytest.raises(DomainValidationError):
            _review(name="")

    def test_rename(self):
        r = _review()
        r.rename("新评审名", "u")
        assert r.name == "新评审名"

    def test_rename_empty_rejected(self):
        r = _review()
        with pytest.raises(DomainValidationError):
            r.rename("", "u")

    def test_status_state_machine(self):
        r = _review()
        assert str(r.status) == "UNDERWAY"
        r.change_status("COMPLETED")
        assert str(r.status) == "COMPLETED"
        r.change_status("UNDERWAY")
        assert str(r.status) == "UNDERWAY"

    def test_illegal_transition_rejected(self):
        r = _review()
        r.change_status("COMPLETED")
        # COMPLETED -> PREPARED 不允许
        with pytest.raises(InvalidReviewTransition):
            r.change_status("PREPARED")

    def test_link_cases_dedup(self):
        r = _review()
        added = r.link_cases(["c1", "c2", "c1"])
        assert added == 2
        assert r.case_count == 2

    def test_link_cases_on_deleted_rejected(self):
        r = _review()
        r.delete("u")
        with pytest.raises(DomainValidationError):
            r.link_cases(["c1"])

    def test_unlink_cases(self):
        r = _review()
        r.link_cases(["c1", "c2", "c3"])
        removed = r.unlink_cases(["c1", "c3"])
        assert removed == 2
        assert r.case_count == 1
        assert r.links[0].case_id == "c2"

    def test_update_link_result(self):
        r = _review()
        r.link_cases(["c1"])
        r.update_link_result("c1", "PASS", reviewer="qa1", comment="ok")
        assert r.links[0].result.is_passed
        assert r.links[0].reviewer == "qa1"
        assert r.links[0].comment == "ok"

    def test_update_link_result_not_linked(self):
        r = _review()
        r.link_cases(["c1"])
        with pytest.raises(DomainValidationError):
            r.update_link_result("c999", "PASS")

    def test_batch_update_links(self):
        r = _review()
        r.link_cases(["c1", "c2"])
        updated = r.update_links_result(["c1", "c2"], "PASS", "qa1", "good")
        assert updated == 2
        counts = r.get_result_counts()
        assert counts["passCount"] == 2
        assert counts["reviewedCount"] == 2

    def test_is_completed(self):
        r = _review()
        r.link_cases(["c1", "c2"])
        assert not r.is_completed()  # 未评审
        r.update_links_result(["c1"], "PASS")
        assert not r.is_completed()  # 只过一半
        r.update_links_result(["c2"], "UN_PASS")
        assert r.is_completed()  # 全部有结论

    def test_soft_delete(self):
        r = _review()
        assert not r.deleted
        r.delete("u")
        assert r.deleted
        with pytest.raises(DomainValidationError):
            r.delete("u")  # 重复删除拒绝

    def test_result_counts(self):
        r = _review()
        r.link_cases(["c1", "c2", "c3"])
        r.update_link_result("c1", "PASS")
        r.update_link_result("c2", "UN_PASS")
        counts = r.get_result_counts()
        assert counts["passCount"] == 1
        assert counts["unPassCount"] == 1
        assert counts["unReviewCount"] == 1
        assert counts["reviewedCount"] == 2

    def test_events_collected(self):
        r = _review()
        r.rename("renamed", "u")
        r.change_status("COMPLETED", "u")
        events = r.pull_domain_events()
        types = [type(e).__name__ for e in events]
        assert "CaseReviewUpdated" in types
        assert "CaseReviewStatusChanged" in types

    def test_reviewers_parse(self):
        r = _review(reviewers=[
            {"userId": "u1", "userName": "User1"},
            {"userId": "u2", "userName": ""},  # userName 为空时回退到 userId
        ])
        assert len(r.reviewers) == 2
        assert r.reviewers[0].user_id == "u1"
        assert r.reviewers[0].user_name == "User1"
        assert r.reviewers[1].user_id == "u2"
        assert r.reviewers[1].user_name == "u2"


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（真实存储）
# ═══════════════════════════════════════════════════════════
@pytest.fixture
def fresh_review_id():
    from app.domain.case_review.application.case_review_app_service import (
        case_review_app_service,
    )
    from app.domain.case_review.application.dto import (
        CreateReviewCommand,
        DeleteReviewCommand,
    )

    rv = case_review_app_service.create(CreateReviewCommand(
        name=_mk(), description="DDD test",
        project_id="p_ddd", reviewers=[{"userId": "qa1", "userName": "QA1"}],
        operator="admin",
    ))
    rid = rv["id"]
    yield rid
    # 清理（物理删除）
    try:
        from app.core.database import Database
        conn = Database.get_conn("testcases.db")
        conn.execute("DELETE FROM case_review_case_links WHERE review_id=?", (rid,))
        conn.execute("DELETE FROM case_review_follows WHERE review_id=?", (rid,))
        conn.execute("DELETE FROM case_review_headers WHERE id=?", (rid,))
        conn.commit()
    except Exception:
        pass


def test_app_create_and_get(fresh_review_id):
    from app.domain.case_review.application.case_review_app_service import (
        case_review_app_service,
    )
    detail = case_review_app_service.get_detail(fresh_review_id)
    assert detail is not None
    assert detail["name"].startswith(TAG)
    assert detail["status"] == "UNDERWAY"


def test_app_link_and_review(fresh_review_id):
    from app.domain.case_review.application.case_review_app_service import (
        case_review_app_service,
    )
    from app.domain.case_review.application.dto import (
        LinkCasesCommand,
        UpdateLinkResultCommand,
    )

    case_a = _mk("case")
    case_b = _mk("case")
    case_review_app_service.link_cases(LinkCasesCommand(
        review_id=fresh_review_id, case_ids=[case_a, case_b], operator="admin"))

    result = case_review_app_service.update_link_result(UpdateLinkResultCommand(
        review_id=fresh_review_id, case_ids=[case_a, case_b],
        status="PASS", reviewer="qa1", comment="good", operator="admin"))

    assert result["updated"] == 2
    assert result["counts"]["passCount"] == 2


def test_app_list(fresh_review_id):
    from app.domain.case_review.application.case_review_app_service import (
        case_review_app_service,
    )
    from app.domain.case_review.application.dto import CaseReviewListQuery

    lst = case_review_app_service.list_reviews(CaseReviewListQuery(project_id="p_ddd"))
    assert lst["total"] >= 1


def test_app_soft_delete(fresh_review_id):
    from app.domain.case_review.application.case_review_app_service import (
        case_review_app_service,
    )
    from app.domain.case_review.application.dto import DeleteReviewCommand

    case_review_app_service.soft_delete(DeleteReviewCommand(
        review_id=fresh_review_id, operator="admin"))
    # 已软删除的评审无法直接 get
    detail = case_review_app_service.get(fresh_review_id)
    assert detail is None
