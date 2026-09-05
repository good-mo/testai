"""生成编排领域服务：跨聚合/跨对象的不变量策略。

领域服务承载不适合放入单个实体方法、且依赖多个对象或外部上下文读取的
业务规则。本服务将"状态迁移是否允许 / 是否应重试 / 是否可恢复 /
覆盖率是否达标"独立成可测试策略，供聚合与路由流程复用，避免规则散落
在 graph 流程各处。
"""
from __future__ import annotations

from app.domain.common.exceptions import DomainValidationError
from app.domain.generation.domain.value_objects.coverage_gate import CoverageGate
from app.domain.generation.domain.value_objects.generation_status import (
    GenerationStatus,
    GenerationStatusEnum,
)


class GenerationPolicy:
    """生成编排无状态领域服务。"""

    # 默认重试预算（与既有 graph 路由默认一致）
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_MAX_COVERAGE_RETRIES = 5
    DEFAULT_COVERAGE_THRESHOLD = 80.0

    def ensure_transition_allowed(self, current: GenerationStatus,
                                  target: GenerationStatus) -> None:
        """校验状态迁移合法性，非法时抛领域异常。"""
        if current.value is target.value:
            return
        if not current.can_transition_to(target):
            raise DomainValidationError(
                f"不允许从状态 '{current}' 迁移到 '{target}'"
            )

    def should_retry(self, *, passed: bool, retry_count: int,
                     fatal: bool = False, max_retries: int = None) -> bool:
        """判定测试失败后是否应再发起一次修复重试。

        命中任一条件即不重试：已通过、致命错误不可恢复、已达上限。
        """
        if passed:
            return False
        if fatal:
            return False
        budget = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES
        if retry_count >= budget:
            return False
        return True

    def should_improve_coverage(self, gate: CoverageGate, *, retry_count: int,
                                max_coverage_retries: int = None) -> bool:
        """判定覆盖率未达标时是否继续补测。"""
        if gate.has_error:
            return False
        if gate.passed_threshold:
            return False
        budget = (max_coverage_retries
                  if max_coverage_retries is not None
                  else self.DEFAULT_MAX_COVERAGE_RETRIES)
        if retry_count >= budget:
            return False
        return True

    def can_succeed(self, job_status: GenerationStatus) -> bool:
        """仅在 running/pending 状态可成功收口（终态不再变更）。"""
        if job_status.is_terminal:
            raise DomainValidationError(f"任务已处于终态 '{job_status}'，不可再标记成功")
        return True

    def infer_final_status(self, *, generated_tests: str,
                           test_result: dict, generate_script: bool) -> GenerationStatusEnum:
        """根据生成产物与运行结果推断最终状态。

        不生成脚本（仅结构化）视为成功；否则看测试是否通过。
        """
        if not generate_script:
            return GenerationStatusEnum.SUCCEEDED
        test_result = test_result or {}
        passed = bool(test_result.get("passed"))
        return GenerationStatusEnum.SUCCEEDED if passed else GenerationStatusEnum.FAILED


# 单例（进程内复用）
generation_policy = GenerationPolicy()


__all__ = ["GenerationPolicy", "generation_policy"]
