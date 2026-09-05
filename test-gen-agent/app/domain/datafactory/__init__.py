"""数据工厂 限界上下文（Bounded Context）。

聚合根：`DataTemplate`
内聚：数据批次 DataBatch、字段生成策略(DataGenPolicy) 等领域概念。
对应现有：`app/datafactory/` `app/repositories/datafactory_repo.py`
        `app/services/datafactory_service.py`

    app/domain/datafactory/domain/          领域层（与存储/框架零依赖）
        entities/                      DataTemplate 聚合根 + DataBatch
        value_objects/                  Category / TemplateStatus / FieldStrategy
        services/                      DataGenPolicy（字段生成策略）
        events.py                      领域事件
        repository.py                  聚合仓储接口（Repository Protocol）
        exceptions.py                  领域异常
    app/domain/datafactory/application/     应用层（用例编排，事务边界）
        datafactory_app_service.py          应用服务门面
        dto.py                            输入/输出传输对象
    app/domain/datafactory/infrastructure/  基础设施层（对接现有存储实现）
        datafactory_repository_impl.py      聚合仓储实现（防腐层）

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
from app.domain.datafactory.domain.entities.data_batch import DataBatch
from app.domain.datafactory.domain.entities.data_template import DataTemplate
from app.domain.datafactory.domain.repository import DataFactoryRepository

__all__ = ["DataTemplate", "DataBatch", "DataFactoryRepository"]
