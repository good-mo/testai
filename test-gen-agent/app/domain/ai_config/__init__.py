"""AI 配置限界上下文（Bounded Context）。

聚合根：`AiConfig`（AI 用例生成配置）
对应现有：`services/ai_config_service.py` `repositories/ai_config_repo.py`
         `repositories/ai_conversation_repo.py`

    app/domain/ai_config/domain/          领域层（与存储/框架零依赖）
        entities/ai_config.py              AiConfig 聚合根
        events.py                          领域事件
        repository.py                      聚合仓储接口（Repository Protocol）
        exceptions.py                      领域异常
    app/domain/ai_config/application/     应用层（用例编排，事务边界）
        ai_config_app_service.py           应用服务门面
        dto.py                             命令/查询 DTO
    app/domain/ai_config/infrastructure/  基础设施层（对接既有 Repo 存储）
        ai_config_repository_impl.py       聚合仓储实现（防腐层）

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
from app.domain.ai_config.application.ai_config_app_service import (
    AiConfigAppService,
    ai_config_app_service,
)
from app.domain.ai_config.domain.entities.ai_config import AiConfig

__all__ = ["AiConfigAppService", "ai_config_app_service", "AiConfig"]
