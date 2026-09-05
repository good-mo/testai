"""用例管理 限界上下文（Bounded Context）。

DDD 试点域。上下文内部按「领域层 / 应用层 / 基础设施层」组织：

    app/domain/cases/domain/          领域层（与基础设施无关）
        entities/                     TestCase 聚合根 + CaseVersion/CaseChangeLog 实体
        value_objects/                Priority/Status/TestType/Review 等值对象
        services/                     领域服务（跨聚合逻辑，如状态机）
        events.py                     领域事件
        repository.py                 聚合仓储接口（Repository Protocol）
        exceptions.py                 领域异常
    app/domain/cases/application/     应用层（用例编排，事务边界）
        case_app_service.py           应用服务（对外唯一门面）
        dto.py                        输入/输出传输对象
    app/domain/cases/infrastructure/  基础设施层（对接现有 CaseRepo 存储）
        case_repository_impl.py       聚合仓储实现

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
from app.domain.cases.domain.entities.case import TestCase
from app.domain.cases.domain.repository import CaseRepository

__all__ = ["TestCase", "CaseRepository"]
