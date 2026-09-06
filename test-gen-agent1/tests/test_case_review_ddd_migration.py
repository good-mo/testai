"""用例评审 case_review 域 · 迁移三步（阶段 B/C）回归测试。

验证既有调用链（service 层，router 唯一入口）在委托 DDD 应用服务后，
对外 schema 与迁移前一致，领域不变量（名称必填、状态机、软删去重、
未关联用例不可评审）由聚合根真正守护。

覆盖：
  1. create_review 经 DDD：返回 Repo header 契约（reviewers_json 在）。
  2. update_review 经 DDD：改名/评审人/标签更新落库。
  3. delete_review 经 DDD：软删除。
  4. copy_review 经 DDD：复制（含关联用例）。
  5. link_cases / unlink_cases / update_link_status 经 DDD。
  6. 领域不变量：空名称拒绝 / 非法状态迁移拒绝 / 已删除不可再次删除。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

import pytest

from app.core.database import Database  # noqa: E402
from app.domain.case_review.domain.exceptions import (  # noqa: E402
    InvalidReviewTransition,
)
from app.domain.common.exceptions import (  # noqa: E402
    AggregateNotFound,
    DomainValidationError,
)
from app.services.case_review_service import case_review_service as cvs  # noqa: E402


def _uniq(prefix="MIG"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _cleanup(review_id):
    if not review_id:
        return
    try:
        conn = Database.get_conn("testcases.db")
        conn.execute("DELETE FROM case_review_case_links WHERE review_id=?", (review_id,))
        conn.execute("DELETE FROM case_review_follows WHERE review_id=?", (review_id,))
        conn.execute("DELETE FROM case_review_headers WHERE id=?", (review_id,))
        conn.commit()
    except Exception:
        pass


def test_create_returns_repo_header_contract():
    """创建经 DDD 后返回 Repo header 契约（含 reviewers_json）。"""
    h = cvs.create_review(
        name=_uniq(), description="mig 建", project_id="p1", module_id="m1",
        reviewers=[{"userId": "u1", "userName": "Alice"}], tags=["t1"],
        create_user="admin",
    )
    try:
        assert "reviewers_json" in h
        assert h["reviewers_json"] == [{"userId": "u1", "userName": "Alice"}]
        assert h["name"].startswith("MIG")
        assert h["status"] == "UNDERWAY"
        assert h["module_id"] == "m1"
        assert h["project_id"] == "p1"
        assert h["tags"] == ["t1"]
    finally:
        _cleanup(h.get("id"))


def test_create_empty_name_rejected():
    """空名称由聚合根拒绝。"""
    with pytest.raises(DomainValidationError):
        cvs.create_review(name="")


def test_update_renames_and_reviewers():
    """update 经 DDD 更新名称/评审人并落库。"""
    h = cvs.create_review(name=_uniq(), reviewers=[{"userId": "u1", "userName": "A"}])
    try:
        up = cvs.update_review(h["id"], {
            "name": "mig 改名",
            "reviewers": [{"userId": "u2", "userName": "Bob"}],
        })
        assert up["name"] == "mig 改名"
        assert up["reviewers_json"] == [{"userId": "u2", "userName": "Bob"}]
        got = cvs.get_review(h["id"])
        assert got["name"] == "mig 改名"
        assert got["reviewers_json"] == [{"userId": "u2", "userName": "Bob"}]
    finally:
        _cleanup(h.get("id"))


def test_update_illegal_status_transition_rejected():
    """非法状态迁移由聚合根状态机拒绝。"""
    h = cvs.create_review(name=_uniq())
    try:
        # 先转到 COMPLETED
        cvs.update_review(h["id"], {"status": "COMPLETED"})
        # COMPLETED -> PREPARED 非法
        with pytest.raises(InvalidReviewTransition):
            cvs.update_review(h["id"], {"status": "PREPARED"})
    finally:
        _cleanup(h.get("id"))


def test_soft_delete_and_redelete_rejected():
    """软删经 DDD，重复删除由聚合根拒绝。"""
    h = cvs.create_review(name=_uniq())
    try:
        assert cvs.delete_review(h["id"]) is True
        assert cvs.get_review(h["id"]) is None
        # 二次删除：软删后行不可见 -> 聚合抛"不存在或已删除"
        with pytest.raises(AggregateNotFound):
            cvs.delete_review(h["id"])
    finally:
        _cleanup(h.get("id"))


def test_copy_via_ddd_includes_links():
    """copy 经 DDD 复制含关联用例。"""
    h = cvs.create_review(name=_uniq())
    try:
        cvs.link_cases(h["id"], ["c1", "c2"])
        cp = cvs.copy_review(h["id"], new_name="mig 副本")
        assert cp is not None
        assert cp["id"] != h["id"]
        assert len(cvs.list_links(cp["id"])) == 2
    finally:
        _cleanup(h.get("id"))
        _cleanup(cp.get("id") if "cp" in dir() else None)


def test_link_unlink_update_result_via_ddd():
    """关联/解除/批量评审经 DDD，计数与状态正确。"""
    h = cvs.create_review(name=_uniq())
    try:
        assert cvs.link_cases(h["id"], ["c1", "c2", "c1"]) == 2
        # 批量评审
        assert cvs.update_link_status(h["id"], ["c1"], "PASS",
                                      reviewer="u1", comment="ok") == 1
        counts = cvs.get_review_case_status(h["id"])
        assert counts["passCount"] == 1
        assert counts["unReviewCount"] == 1
        # 解除
        assert cvs.unlink_cases(h["id"], ["c2"]) == 1
        assert len(cvs.list_links(h["id"])) == 1
    finally:
        _cleanup(h.get("id"))


def test_update_link_status_on_unlinked_case_guarded():
    """未关联用例不可被评审（聚合根守护）。"""
    h = cvs.create_review(name=_uniq())
    try:
        # 关联 c1，尝试对未关联的 c999 批量评审 => 更新数应为 0
        cvs.link_cases(h["id"], ["c1"])
        assert cvs.update_link_status(h["id"], ["c999"], "PASS") == 0
    finally:
        _cleanup(h.get("id"))
