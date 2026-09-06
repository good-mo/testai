"""用例评审聚合仓储实现（Adapter）。

把"面向聚合的仓储接口"翻译为既有 CaseReviewRepo（四层 Repository）
的命令，实现防腐层（Anti-Corruption Layer），复用已验证的存储逻辑，
同时让领域层获得聚合级读写语义。后续如需换存储仅替换本文件。
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from app.domain.case_review.domain.entities.case_review import CaseReview
from app.repositories.case_review_repo import CaseReviewRepo


class CaseReviewRepoAdapter:
    """将既有 CaseReviewRepo 封装为面向聚合的仓储。"""

    # ── 标识生成（沿用既有 uuid 主键策略）────────────
    def next_id(self) -> str:
        return str(uuid.uuid4())

    # ── 读：聚合重建 ────────────────────────────────
    def find_by_id(self, review_id: str) -> Optional[CaseReview]:
        if not review_id:
            return None
        row = CaseReviewRepo.get_review(review_id)
        if not row:
            return None
        # 合并关联用例
        links = CaseReviewRepo.list_links(review_id)
        row["links"] = links
        return CaseReview.from_dict(row)

    # ── 写：以聚合为粒度落库 ────────────────────────
    def save(self, review: CaseReview) -> CaseReview:
        """新建评审头（不含关联用例）。

        直接以聚合的 id 落库，而非调用 CaseReviewRepo.create_review
        （该方法内部自行生成 uuid4，无法指定 id）。后续若要接入
        CaseReviewRepo.create_review，可先落库再以返回 id 更新主键。
        """
        import json
        import time

        from app.core.database import Database

        d = review.to_dict()
        rid = review.id.value
        now = d.get("create_time", time.time())
        reviewers = d.get("reviewers") or []
        if isinstance(reviewers, str):
            try:
                reviewers = json.loads(reviewers)
            except Exception:
                reviewers = []
        tags = d.get("tags") or []
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = []

        conn = Database.get_conn("testcases.db")
        # 幂等：先删除可能存在的同 id 记录，再插入
        conn.execute("DELETE FROM case_review_headers WHERE id=?", (rid,))
        conn.execute("""
            INSERT INTO case_review_headers
                (id, name, num, module_id, project_id, status, review_pass_rule, pos,
                 start_time, end_time, tags, description, create_time, create_user,
                 update_time, update_user, deleted, reviewers_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)
        """, (
            rid, d.get("name", ""), int(d.get("num", 1)),
            d.get("module_id", "root"), d.get("project_id", ""),
            d.get("status", "UNDERWAY"), d.get("review_pass_rule", "SINGLE"),
            int(d.get("pos", 0)),
            float(d.get("start_time", 0) or 0),
            float(d.get("end_time", 0) or 0),
            json.dumps(tags, ensure_ascii=False),
            d.get("description", ""),
            now, d.get("create_user", "admin"),
            now, d.get("update_user", "admin"),
            json.dumps(reviewers, ensure_ascii=False),
        ))
        conn.commit()
        return self.find_by_id(rid) or review

    def update(self, review: CaseReview) -> bool:
        """更新评审头基本信息（不含关联变更，关联经独立方法）。"""
        import json

        from app.core.database import Database

        d = review.to_dict()
        rid = review.id.value
        now = d.get("update_time")
        import time as _time
        now = _time.time()
        # tags 与 reviewers 不在 _REVIEW_UPDATE_FIELDS 中，单独处理
        fields = {
            "name": d.get("name"),
            "description": d.get("description"),
            "module_id": d.get("module_id"),
            "project_id": d.get("project_id"),
            "status": d.get("status"),
            "review_pass_rule": d.get("review_pass_rule"),
            "start_time": d.get("start_time"),
            "end_time": d.get("end_time"),
        }
        # 清理 None 值
        fields = {k: v for k, v in fields.items() if v is not None}
        result = CaseReviewRepo.update_review(rid, fields)
        # tags / reviewers 单独更新（不在 _REVIEW_UPDATE_FIELDS 中）
        conn = Database.get_conn("testcases.db")
        tags = d.get("tags") or []
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = []
        reviewers = d.get("reviewers") or []
        if isinstance(reviewers, str):
            try:
                reviewers = json.loads(reviewers)
            except Exception:
                reviewers = []
        conn.execute("""
            UPDATE case_review_headers
            SET tags=?, reviewers_json=?, update_time=?
            WHERE id=?
        """, (
            json.dumps(tags, ensure_ascii=False),
            json.dumps(reviewers, ensure_ascii=False),
            now, rid,
        ))
        conn.commit()
        return result is not None

    def soft_delete(self, review_id: str, operator: str = "system") -> bool:
        """软删除评审会话。"""
        return CaseReviewRepo.delete_review(review_id, soft=True)

    def copy(self, source_id: str, new_name: str = "",
             operator: str = "system") -> Optional[CaseReview]:
        """复制评审（含关联用例）。"""
        copied = CaseReviewRepo.copy_review(source_id, new_name=new_name)
        if not copied:
            return None
        return self.find_by_id(copied["id"])

    def link_cases(self, review_id: str, case_ids: List[str]) -> int:
        """批量关联用例到评审。"""
        return CaseReviewRepo.link_cases(review_id, case_ids)

    def unlink_cases(self, review_id: str, case_ids: List[str]) -> int:
        """批量解除评审与用例的关联。"""
        return CaseReviewRepo.unlink_cases(review_id, case_ids)

    def update_link_status(self, review_id: str, case_ids: List[str],
                           result: str, reviewer: str = "",
                           comment: str = "") -> int:
        """批量更新评审-用例结果。"""
        return CaseReviewRepo.update_link_status(
            review_id, case_ids, result,
            reviewer=reviewer, comment=comment,
        )

    def list(self, *, keyword: str = "", project_id: str = "",
             status: str = "", limit: int = 500,
             offset: int = 0) -> Tuple[List[CaseReview], int]:
        """分页列出评审头。"""
        rows = CaseReviewRepo.list_reviews(
            keyword=keyword, project_id=project_id,
            status=status, limit=limit, offset=offset,
        )
        total = CaseReviewRepo.count_reviews(
            keyword=keyword, project_id=project_id, status=status,
        )
        reviews: List[CaseReview] = []
        for r in rows:
            r["links"] = CaseReviewRepo.list_links(r["id"])
            reviews.append(CaseReview.from_dict(r))
        return reviews, total

    def list_link_case_ids(self, review_id: str) -> set:
        """列出评审下已关联用例 id 集合。"""
        return CaseReviewRepo.list_link_case_ids(review_id)

    def list_links(self, review_id: str) -> list:
        """列出评审关联的用例记录（原始 link 行）。"""
        return CaseReviewRepo.list_links(review_id)

    def get_status_counts(self, review_id: str) -> dict:
        """评审下用例状态汇总计数。"""
        return CaseReviewRepo.get_review_case_status(review_id)

    def is_following(self, review_id: str, user_id: str) -> bool:
        """用户是否已关注该评审。"""
        return CaseReviewRepo.is_following(review_id, user_id)

    def toggle_follow(self, review_id: str, user_id: str) -> bool:
        """关注/取消关注评审。"""
        return CaseReviewRepo.toggle_follow(review_id, user_id)

    def count_by_module(self, project_id: str = "") -> dict:
        """每个评审模块下的评审数量统计。"""
        return CaseReviewRepo.count_reviews_by_module(project_id)


# 单例（进程内复用）
case_review_repo_adapter = CaseReviewRepoAdapter()
