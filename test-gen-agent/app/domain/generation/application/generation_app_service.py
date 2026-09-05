"""生成编排应用服务（Application Service / Use Case 门面）。

职责：
  1. 作为路由器与领域层之间的唯一用例编排入口；
  2. 承载事务边界：加载聚合 → 执行领域命令 → 保存聚合 → 发布领域事件 →
     驱动运行记录/报告刷新等副作用；
  3. 将领域异常透传给上层（由 Web 层统一翻译为 HTTP 响应）。

保持瘦：只做编排，不写业务规则（业务规则在领域层聚合/策略内）。
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.domain.common.domain_events import DomainEvent, event_bus
from app.domain.common.exceptions import AggregateNotFound
from app.domain.generation.application.dto import (
    CancelCommand,
    CreateGenerationCommand,
    FinalizeCommand,
    JobListQuery,
    JobStats,
    RecordStepCommand,
    RetryCommand,
    UpdateArtifactsCommand,
)
from app.domain.generation.application.web_contract import to_run_row
from app.domain.generation.domain.entities.generation_job import GenerationJob
from app.domain.generation.domain.repository import GenerationJobRepository
from app.domain.generation.domain.services.generation_policy import GenerationPolicy
from app.domain.generation.infrastructure.generation_repository_impl import (
    generation_repository,
)

logger = logging.getLogger(__name__)


class GenerationAppService:
    """测试生成任务用例编排服务。"""

    def __init__(self, repo: GenerationJobRepository = None):
        self._repo: GenerationJobRepository = repo or generation_repository
        self._policy = GenerationPolicy()

    # ── 聚合级操作 ─────────────────────────────────
    def submit(self, cmd: CreateGenerationCommand) -> Optional[dict]:
        """提交一次生成任务：建聚合（pending）→ 保存 → 发布创建事件。"""
        job = GenerationJob(
            job_id=self._repo.next_id(),
            file_path=cmd.file_path,
            source_code=cmd.source_code,
            source=cmd.source,
            test_type=cmd.test_type,
            generate_script=cmd.generate_script,
            metadata=cmd.metadata,
        )
        job.confirm_created(cmd.operator)
        self._repo.save(job)
        self._publish(job)
        return job.to_dict()

    def get(self, job_id: str) -> Optional[dict]:
        job = self._repo.find_by_id(job_id)
        return job.to_dict() if job else None

    def start(self, job_id: str, operator: str = "system") -> Optional[dict]:
        """开始执行任务：pending → running。"""
        job = self._find_or_raise(job_id)
        job.start(operator)
        self._repo.update(job)
        self._publish(job)
        return job.to_dict()

    def record_step(self, cmd: RecordStepCommand) -> Optional[dict]:
        """登记一次步骤执行结果。"""
        job = self._find_or_raise(cmd.job_id)
        job.record_step(node_name=cmd.node_name, status=cmd.status,
                        error=cmd.error, detail=cmd.detail, operator=cmd.operator)
        self._repo.update(job)
        self._publish(job)
        return job.to_dict()

    def update_artifacts(self, cmd: UpdateArtifactsCommand) -> Optional[dict]:
        """提交生成产物。"""
        job = self._find_or_raise(cmd.job_id)
        job.set_artifacts(
            generated_tests=cmd.generated_tests,
            test_result=cmd.test_result,
            coverage_report=cmd.coverage_report,
            performance_report=cmd.performance_report,
            saved_to=cmd.saved_to,
            error=cmd.error,
        )
        self._repo.update(job)
        return job.to_dict()

    def retry(self, cmd: RetryCommand) -> Optional[dict]:
        """登记一次测试失败与修复重试推进。"""
        job = self._find_or_raise(cmd.job_id)
        if cmd.test_result is not None:
            job.record_test_failure(
                test_result=cmd.test_result, diagnosis=cmd.diagnosis)
        # 只要测试未通过且仍在可重试状态，即推进一次 retry
        if not (job.test_result or {}).get("passed", True):
            job.do_retry(reason=cmd.reason, operator=cmd.operator)
        self._repo.update(job)
        self._publish(job)
        return job.to_dict()

    def finalize(self, cmd: FinalizeCommand) -> Optional[dict]:
        """收口任务（succeeded / failed）。"""
        job = self._find_or_raise(cmd.job_id)
        if cmd.outcome == "failed":
            job.fail(reason=cmd.reason, operator=cmd.operator)
        else:
            job.succeed(generated_tests=cmd.generated_tests, operator=cmd.operator)
        self._repo.update(job)
        self._publish(job)
        return job.to_dict()

    def cancel(self, cmd: CancelCommand) -> Optional[dict]:
        job = self._find_or_raise(cmd.job_id)
        job.cancel(cmd.operator)
        self._repo.update(job)
        self._publish(job)
        return job.to_dict()

    def delete(self, job_id: str) -> bool:
        return bool(self._repo.delete_by_id(job_id))

    # ── 查询（读模型）───────────────────────────────
    def list_jobs(self, query: JobListQuery) -> dict:
        items, total = self._repo.list_jobs(
            file_path=query.file_path, source=query.source,
            passed=query.passed, status=query.status, search=query.search,
            limit=query.limit, offset=query.offset,
        )
        return {"list": [j.to_dict() for j in items], "total": total}

    def stats(self) -> dict:
        raw = self._repo.stats()
        return JobStats(
            total=raw.get("total", 0),
            passed=raw.get("passed", 0),
            failed=raw.get("failed", 0),
            by_source=raw.get("by_source", {}),
            avg_coverage=float(raw.get("avg_coverage", 0.0)),
        ).to_dict()

    def persist_completed_run(
        self,
        *,
        file_path: str,
        source_code: str = "",
        generated_tests: str = "",
        test_result: Optional[dict] = None,
        coverage_report: Optional[dict] = None,
        performance_report: Optional[dict] = None,
        retry_count: int = 0,
        saved_to: str = "",
        error: str = "",
        source: str = "single",
        metadata: Optional[dict] = None,
        operator: str = "system",
    ) -> Optional[dict]:
        """一次性落库一条**已完成**的生成来源记录（阶段 B · 接入）。

        供同步 /api/generate 与 /ws/generate 等"整段跑完后一次性收口"的场景
        使用：把一次已完成的生成运行经聚合生命周期（confirm → start →
        set_artifacts → succeed/fail）落库，避免与旁路（task/结构化）相互阻塞。

        返回经契约桥 `web_contract.to_run_row` 投影的 run_records 扁平行，
        与既有 `run_service.save` 写出的行**逐字段契约等价**（见迁移回归测试），
        因此 /api/runs、报告兼容层、前端零感知。失败时返回 None 由调用方降级。
        """
        try:
            tr = dict(test_result or {})
            job = GenerationJob(
                job_id=self._repo.next_id(),
                file_path=file_path,
                source_code=source_code or "",
                source=source,
                retry_count=int(retry_count or 0),
                metadata=metadata,
            )
            job.confirm_created(operator)
            self._repo.save(job)
            job.start(operator)
            job.set_artifacts(
                generated_tests=generated_tests or None,
                test_result=tr or None,
                coverage_report=coverage_report or None,
                performance_report=performance_report or None,
                saved_to=saved_to or None,
                error=error or None,
            )
            if bool(tr.get("passed")):
                job.succeed(generated_tests=generated_tests or "", operator=operator)
            else:
                job.fail(reason=error or "generation run failed", operator=operator)
            self._repo.update(job)
            self._publish(job)
            return to_run_row(job)
        except Exception:
            logger.exception("DDD 生成来源记录落库失败 [file_path=%s]", file_path)
            return None

    # ── 内部助手 ────────────────────────────────────
    def _find_or_raise(self, job_id: str) -> GenerationJob:
        job = self._repo.find_by_id(job_id)
        if job is None:
            raise AggregateNotFound(f"生成任务不存在: {job_id}")
        return job

    def _publish(self, job: GenerationJob) -> None:
        events: List[DomainEvent] = job.pull_domain_events()
        for ev in events:
            event_bus.dispatch(ev)


# 单例门面（进程内复用）
generation_app_service = GenerationAppService()


__all__ = ["GenerationAppService", "generation_app_service"]
