"""缺陷管理 限界上下文（Bounded Context）。

上下文内部按「领域层 / 应用层 / 基础设施层」组织：
    app/domain/defects/domain/            领域层（与基础设施无关）
        entities/defect.py                 Defect 聚合根
        value_objects/                     Severity / DefectStatus（状态机）
        services/                          DefectLifecyclePolicy（状态机策略）
        events.py                          领域事件
        repository.py                      聚合仓储接口（Repository Protocol）
        exceptions.py                      领域异常
    app/domain/defects/application/        应用层（用例编排）
        defect_app_service.py              应用服务（对外门面）
        dto.py                             输入/输出传输对象
    app/domain/defects/infrastructure/     基础设施层（对接既有 DefectRepo）
        defect_repository_impl.py          聚合仓储实现

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
from app.domain.defects.domain.entities.defect import Defect
from app.domain.defects.domain.repository import DefectRepository

__all__ = ["Defect", "DefectRepository"]
