"""报告 限界上下文（Bounded Context）。

聚合根：`Report`
内聚：步骤(ReportStep)、导出(ReportFormat/ReportState)、汇总摘要 等值对象。
对应现有：`services/report_service.py` `repositories/report_repo.py`

    app/domain/report/domain/          领域层（与存储/框架零依赖）
        entities/                      Report 聚合根及子实体
        value_objects/                 值对象（ReportFormat/ReportState）
        services/                      ReportLifecyclePolicy + 汇总/口径策略
        events.py                      领域事件
        repository.py                  聚合仓储接口（Repository Protocol）
        exceptions.py                  领域异常
    app/domain/report/application/     应用层（用例编排，事务边界）
        report_app_service.py          应用服务门面
        dto.py                        输入/输出传输对象
    app/domain/report/infrastructure/  基础设施层（对接既有 ReportRepo 存储）
        report_repository_impl.py      聚合仓储实现（防腐层）

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
from app.domain.report.domain.entities.report import Report
from app.domain.report.domain.repository import ReportRepository

__all__ = ["Report", "ReportRepository"]
