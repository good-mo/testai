"""任务运行 / TaskCenter 与运行记录限界上下文（Bounded Context）。

聚合根：
  - `Task`（异步任务队列 TaskCenter 生命周期）
  - `RunRecord`（通用运行记录 / 报告，对应 run_service → RunRepo）
内聚：TaskStatus（状态机）、RunSource（来源）等值对象。
对应现有：`tasks/` `app/core/task_enums.py` `repositories/task_repo.py`
          `services/run_service.py` `repositories/run_repo.py`

    app/domain/runs/domain/          领域层（与存储/框架零依赖）
        entities/                     Task / RunRecord 聚合根
        value_objects/                TaskStatus / RunSource
        services/                     领域策略（run_record_policy）
        events.py                      领域事件
        repository.py                 聚合仓储接口（Repository Protocol）
        exceptions.py                 领域异常
    app/domain/runs/application/     应用层（用例编排，事务边界）
        run_app_service.py            Task 应用服务门面
        run_record_app_service.py     RunRecord 应用服务门面
        dto.py                        命令/查询 DTO
    app/domain/runs/infrastructure/  基础设施层（对接既有存储）
        run_repository_impl.py        Task 聚合仓储实现（防腐层）
        run_record_repository_impl.py RunRecord 聚合仓储实现（防腐层）

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
from app.domain.runs.application.run_app_service import RunAppService, run_app_service
from app.domain.runs.application.run_record_app_service import (
    RunRecordAppService,
    run_record_app_service,
)
from app.domain.runs.domain.entities.run_record import RunRecord
from app.domain.runs.domain.entities.task import Task

__all__ = [
    "RunAppService", "run_app_service",
    "RunRecordAppService", "run_record_app_service",
    "Task", "RunRecord",
]
