"""用例评审（Case Review）限界上下文（Bounded Context）。

评审是一个独立于"用例单条评审"的会话级工作流：一个评审（Review）
承载多名评审人对一批用例进行评审，逐条记录评审结果并支持关注。

上下文内部按「领域层 / 应用层 / 基础设施层」组织：

    app/domain/case_review/domain/          领域层（与基础设施无关）
        entities/case_review.py              CaseReview 聚合根（评审头+关联用例）
        value_objects/                       ReviewStatus / CaseReviewResult / 等
        services/                            CaseReviewPolicy（会话状态策略）
        events.py                            领域事件
        repository.py                        聚合仓储接口（Repository Protocol）
        exceptions.py                        领域异常
    app/domain/case_review/application/     应用层（用例编排，事务边界）
        case_review_app_service.py           应用服务（对外唯一门面）
        dto.py                               输入/输出传输对象
    app/domain/case_review/infrastructure/  基础设施层（对接 CaseReviewRepo 存储）
        case_review_repository_impl.py       聚合仓储实现

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
from app.domain.case_review.domain.entities.case_review import CaseReview
from app.domain.case_review.domain.repository import CaseReviewRepository

__all__ = ["CaseReview", "CaseReviewRepository"]
