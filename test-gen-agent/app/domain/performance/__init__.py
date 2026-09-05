"""性能测试 限界上下文（Bounded Context）。

聚合根：`PerformanceTest`
内聚：性能指标(PerformanceMetrics)、SLO(SLOThreshold/SLOValidationResult)、
状态机(PerformanceStatus) 等值对象。
对应现有：`performance/`（企业级性能测试引擎 benchmark/metrics/runner）

    app/domain/performance/domain/          领域层（与存储/框架零依赖）
        entities/performance_test.py        PerformanceTest 聚合根
        value_objects/                      PerformanceMetrics/SLO/Status
        services/performance_policy.py      SLO 校验策略
        events.py                           领域事件
        repository.py                       聚合仓储接口（Port）
        exceptions.py                       领域异常
    app/domain/performance/application/     应用层（用例编排，事务边界）
        performance_app_service.py          应用服务门面
        dto.py                              输入/输出传输对象
    app/domain/performance/infrastructure/  基础设施层（既有引擎适配）
        performance_repository_impl.py      内存仓储 + EngineBenchmarkRunner

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与既有引擎。
"""
from app.domain.performance.domain.entities.performance_test import PerformanceTest
from app.domain.performance.domain.repository import PerformanceRepository

__all__ = ["PerformanceTest", "PerformanceRepository"]
