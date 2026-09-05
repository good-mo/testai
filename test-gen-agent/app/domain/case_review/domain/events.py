"""用例评审领域事件。

事件表达"评审聚合内发生的事实"，供应用层在事务提交后发布，
驱动审计日志、通知、指标统计等跨域副作用解耦。
"""
from __future__ import annotations

from app.domain.common.domain_events import DomainEvent


class CaseReviewCreated(DomainEvent):
    """创建评审会话。"""

    def __init__(self, review_id: str, name: str = "", operator: str = "system"):
        super().__init__(aggregate_id=review_id)
        self.name = name
        self.operator = operator


class CaseReviewUpdated(DomainEvent):
    """更新评审基本信息。"""

    def __init__(self, review_id: str, operator: str = "system"):
        super().__init__(aggregate_id=review_id)
        self.operator = operator


class CaseReviewStatusChanged(DomainEvent):
    """评审会话状态迁移。"""

    def __init__(self, review_id: str, old_status: str, new_status: str,
                 operator: str = "system"):
        super().__init__(aggregate_id=review_id)
        self.old_status = old_status
        self.new_status = new_status
        self.operator = operator


class CaseReviewDeleted(DomainEvent):
    """删除评审会话（软删除）。"""

    def __init__(self, review_id: str, operator: str = "system"):
        super().__init__(aggregate_id=review_id)
        self.operator = operator


class CaseReviewCopied(DomainEvent):
    """复制评审会话。"""

    def __init__(self, source_id: str, target_id: str, operator: str = "system"):
        super().__init__(aggregate_id=source_id)
        self.target_id = target_id
        self.operator = operator


class CaseLinkedToReview(DomainEvent):
    """向评审会话关联用例。"""

    def __init__(self, review_id: str, case_ids: list, operator: str = "system"):
        super().__init__(aggregate_id=review_id)
        self.case_ids = case_ids
        self.operator = operator


class CaseUnlinkedFromReview(DomainEvent):
    """解除评审会话与用例的关联。"""

    def __init__(self, review_id: str, case_ids: list, operator: str = "system"):
        super().__init__(aggregate_id=review_id)
        self.case_ids = case_ids
        self.operator = operator


class CaseReviewResultUpdated(DomainEvent):
    """更新评审中单个用例的评审结果。"""

    def __init__(self, review_id: str, case_id: str, result: str,
                 reviewer: str = "", operator: str = "system"):
        super().__init__(aggregate_id=review_id)
        self.case_id = case_id
        self.result = result
        self.reviewer = reviewer
        self.operator = operator


class CaseReviewFollowToggled(DomainEvent):
    """用户关注/取消关注评审。"""

    def __init__(self, review_id: str, user_id: str, following: bool):
        super().__init__(aggregate_id=review_id)
        self.user_id = user_id
        self.following = following
