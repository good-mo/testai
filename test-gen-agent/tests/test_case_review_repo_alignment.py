"""
用例评审 case_review 域 Repository 功能回归测试
=====================================================
验证 app.repositories.case_review_repo.CaseReviewRepo（case_review 域
唯一权威，旧 app.cases.review_store 兼容门面已删除）对评审头 / 评审-
用例关联 / 关注的 CRUD 输出形态稳定。
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from app.core.database import Database  # noqa: E402
from app.repositories.case_review_repo import (  # noqa: E402
    RESULT_PASS,
    STATUS_UNDERWAY,
    CaseReviewRepo,
)


def _uniq(prefix="REV"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _cleanup(review_id):
    """清理指定评审及其关联（含软删除标记清理）。"""
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


def test_create_and_read():
    """创建评审后可读取，字段与形态一致。"""
    r = CaseReviewRepo.create_review(
        name=_uniq(), description="repo 建", project_id="p1",
        module_id="m1", status=STATUS_UNDERWAY,
        review_pass_rule="SINGLE", reviewers=[{"userId": "u1", "userName": "u1"}],
    )
    try:
        got = CaseReviewRepo.get_review(r["id"])
        assert got is not None
        assert got["name"] == r["name"]
        assert got["description"] == "repo 建"
    finally:
        _cleanup(r["id"])


def test_links_and_status():
    """关联用例 + 更新结果状态正常。"""
    rev = CaseReviewRepo.create_review(name=_uniq(), project_id="p2")
    try:
        case_a, case_b = _uniq("case"), _uniq("case")
        added = CaseReviewRepo.link_cases(rev["id"], [case_a, case_b])
        assert added == 2
        # 再次关联应跳过
        assert CaseReviewRepo.link_cases(rev["id"], [case_a]) == 0
        assert len(CaseReviewRepo.list_links(rev["id"])) == 2
        assert set(CaseReviewRepo.list_link_case_ids(rev["id"])) == {case_a, case_b}
        updated = CaseReviewRepo.update_link_status(
            rev["id"], [case_a, case_b], RESULT_PASS,
            reviewer="u1", comment="ok")
        assert updated == 2
        counts = CaseReviewRepo.get_review_case_status(rev["id"])
        assert counts["passCount"] == 2
        assert counts["reviewedCount"] == 2
        assert CaseReviewRepo.unlink_cases(rev["id"], [case_a]) == 1
        assert set(CaseReviewRepo.list_link_case_ids(rev["id"])) == {case_b}
    finally:
        _cleanup(rev["id"])


def test_follow_and_module_count():
    """关注开关 + 模块归属统计正常。"""
    rev = CaseReviewRepo.create_review(name=_uniq(), project_id="p3", module_id="mdl-x")
    try:
        uid = "u-follow-1"
        assert CaseReviewRepo.is_following(rev["id"], uid) is False
        assert CaseReviewRepo.toggle_follow(rev["id"], uid) is True
        assert CaseReviewRepo.is_following(rev["id"], uid) is True
        assert CaseReviewRepo.toggle_follow(rev["id"], uid) is False
        assert CaseReviewRepo.is_following(rev["id"], uid) is False
        cnt = CaseReviewRepo.count_reviews_by_module("p3")
        assert cnt["all"] >= 1
        assert cnt.get("mdl-x", 0) >= 1
    finally:
        _cleanup(rev["id"])


def test_update_delete_and_copy():
    """更新 / 复制 / 删除功能正常。"""
    rev = CaseReviewRepo.create_review(name=_uniq(), project_id="p4", module_id="m4")
    try:
        case = _uniq("case")
        CaseReviewRepo.link_cases(rev["id"], [case])
        new_name = _uniq("renamed")
        upd = CaseReviewRepo.update_review(rev["id"], {"name": new_name})
        assert upd["name"] == new_name
        dup = CaseReviewRepo.copy_review(rev["id"])
        assert dup is not None and dup["id"] != rev["id"]
        assert len(CaseReviewRepo.list_links(dup["id"])) == 1
        _cleanup(dup["id"])
        assert CaseReviewRepo.delete_review(rev["id"], soft=True) is True
        assert CaseReviewRepo.get_review(rev["id"]) is None
    finally:
        _cleanup(rev["id"])
