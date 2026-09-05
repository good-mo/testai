"""TestInsight 测试洞察 限界上下文（Bounded Context）。

上下文内部按「领域层 / 应用层 / 基础设施层」组织：
    app/domain/test_insight/domain/          领域层（与基础设施无关）
        entities/trace_run.py                TraceRun 聚合根（执行追溯）
        value_objects/                       TestResult / Attribution / RiskLevel / Coverage
        services/                            RiskPolicy / ValuePolicy（无状态策略）
        events.py                            领域事件
        repository.py                        聚合仓储接口（Repository Protocol）
        exceptions.py                        领域异常
    app/domain/test_insight/application/     应用层（用例编排）
        test_insight_app_service.py          应用服务（对外门面）
        dto.py                               输入/输出传输对象
    app/domain/test_insight/infrastructure/ 基础设施层（对接既有 InsightRepo）
        test_insight_repository_impl.py      聚合仓储实现（防腐层）

依赖规则：domain 不依赖 application / infrastructure；
application 依赖 domain；infrastructure 依赖 domain 与现有存储层。
"""
from app.domain.test_insight.domain.entities.trace_run import TraceRun
from app.domain.test_insight.domain.repository import TestInsightRepository

__all__ = ["TraceRun", "TestInsightRepository"]
