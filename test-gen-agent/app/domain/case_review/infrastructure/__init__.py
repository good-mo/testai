"""用例评审上下文基础设施层：对接既有 CaseReviewRepo 存储。"""
from app.domain.case_review.infrastructure.case_review_repository_impl import (
    CaseReviewRepoAdapter,
)

__all__ = ["CaseReviewRepoAdapter"]
