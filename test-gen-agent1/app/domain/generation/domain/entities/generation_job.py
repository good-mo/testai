"""生成任务聚合根 GenerationJob。

聚合边界内的组成：
  - GenerationJob（聚合根）
  - 若干子实体：GenerationStep[]（流程步骤执行记录）、FixLoop[]（修复重试轮）
  - 值对象：GenerationStatus / GenerationTestType / JobSource / CoverageGate

职责：守护一次测试生成任务的完整性与业务不变量：
  - 提交必须携带非空 file_path 与（生成脚本时）source_code；
  - 状态迁移须符合状态机（pending → running → succeeded/failed/cancelled）；
  - 触发一次修复重试须登记 FixLoop 并推进 retry_count；
  - 收口成功/失败需满足前置状态约束。

所有变更必须经由聚合根方法触发，命令校验通过后记录领域事件，供应用层
落库 + 发布，从而与运行记录/审计/报告刷新等副作用解耦。
"""
from __future__ import annotations

import json
import time
from typing import Any, List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.generation.domain.entities.fix_loop import FixLoop
from app.domain.generation.domain.entities.generation_step import GenerationStep
from app.domain.generation.domain.events import (
    GenerationJobCancelled,
    GenerationJobCreated,
    GenerationJobFailed,
    GenerationJobStarted,
    GenerationJobSucceeded,
    GenerationRetried,
    GenerationStepCompleted,
)
from app.domain.generation.domain.value_objects.generation_status import (
    GenerationStatus,
    GenerationStatusEnum,
)
from app.domain.generation.domain.value_objects.generation_test_type import (
    GenerationTestType,
    GenerationTestTypeEnum,
)
from app.domain.generation.domain.value_objects.job_source import JobSource


class GenerationJob(AggregateRoot):
    """测试生成任务聚合根。"""

    def __init__(
        self,
        *,
        job_id: str,
        file_path: str = "",
        source_code: str = "",
        source: str = "single",
        test_type: str = GenerationTestTypeEnum.FUNCTIONAL.value,
        generate_script: bool = True,
        status: str = GenerationStatusEnum.PENDING.value,
        generated_tests: str = "",
        test_result: Optional[dict] = None,
        coverage_report: Optional[dict] = None,
        performance_report: Optional[dict] = None,
        retry_count: int = 0,
        saved_to: str = "",
        error: str = "",
        metadata: Optional[dict] = None,
        steps: Optional[list] = None,
        fix_loops: Optional[list] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        version: int = 0,
    ):
        if not (file_path or "").strip():
            raise DomainValidationError("生成任务的 file_path 不能为空")
        self.id = Identifier.of(job_id)
        self._file_path = (file_path or "").strip()
        self._source_code = source_code or ""
        self._source = JobSource(source)
        self._test_type = GenerationTestType(test_type)
        self._generate_script = bool(generate_script)
        self._status = GenerationStatus(status)
        self._generated_tests = generated_tests or ""
        self._test_result = dict(test_result or {})
        self._coverage_report = dict(coverage_report or {})
        self._performance_report = dict(performance_report or {})
        self._retry_count = int(retry_count or 0)
        self._saved_to = saved_to or ""
        self._error = error or ""
        self._metadata = dict(metadata or {})
        self._steps: List[GenerationStep] = []
        for idx, s in enumerate(steps or []):
            step = GenerationStep.from_dict(s) if isinstance(s, dict) else s
            if step.seq == 0:
                step.seq = idx + 1
            self._steps.append(step)
        self._fix_loops: List[FixLoop] = [
            FixLoop.from_dict(f) if isinstance(f, dict) else f
            for f in (fix_loops or [])
        ]
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._domain_events = []
        self.version = int(version)

    # ── 只读属性 ─────────────────────────────────────
    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def source_code(self) -> str:
        return self._source_code

    @property
    def source(self) -> JobSource:
        return self._source

    @property
    def test_type(self) -> GenerationTestType:
        return self._test_type

    @property
    def generate_script(self) -> bool:
        return self._generate_script

    @property
    def status(self) -> GenerationStatus:
        return self._status

    @property
    def generated_tests(self) -> str:
        return self._generated_tests

    @property
    def test_result(self) -> dict:
        return dict(self._test_result)

    @property
    def coverage_report(self) -> dict:
        return dict(self._coverage_report)

    @property
    def performance_report(self) -> dict:
        return dict(self._performance_report)

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def saved_to(self) -> str:
        return self._saved_to

    @property
    def error(self) -> str:
        return self._error

    @property
    def metadata(self) -> dict:
        return dict(self._metadata)

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    @property
    def passed(self) -> bool:
        return bool((self._test_result or {}).get("passed"))

    @property
    def steps(self) -> List[GenerationStep]:
        return list(self._steps)

    @property
    def fix_loops(self) -> List[FixLoop]:
        return list(self._fix_loops)

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 业务命令（守护不变量）────────────────────────
    def confirm_created(self, operator: str = "system") -> None:
        """记录创建事实（供应用层创建后发布）。"""
        self.record_event(GenerationJobCreated(
            self.id.value, self._file_path, self._source.value, operator,
        ))

    def start(self, operator: str = "system") -> None:
        """开始执行：pending → running。"""
        target = GenerationStatus(GenerationStatusEnum.RUNNING)
        self._ensure_transition(target)
        if self._status.value is not target.value:
            self._status = target
            self.record_event(GenerationJobStarted(self.id.value, operator))
        self._touch()

    def record_step(self, *, node_name: str, status: str = "done",
                    error: str = "", detail: Any = None,
                    operator: str = "system") -> GenerationStep:
        """登记一次流程步骤执行完成（若同节点已存在则更新为最近一次）。"""
        if not node_name:
            raise DomainValidationError("步骤 node_name 不能为空")
        step = next((s for s in self._steps if s.node_name == node_name), None)
        if step is None:
            step = GenerationStep(node_name=node_name, seq=len(self._steps) + 1)
            self._steps.append(step)
        if status == "failed":
            step.mark_failed(error)
        elif status == "done":
            step.mark_done(detail)
        else:
            step.mark_running()
        self.record_event(GenerationStepCompleted(
            self.id.value, node_name, step.status.value, operator,
        ))
        self._touch()
        return step

    def record_test_failure(self, *, test_result: dict, diagnosis: str = "",
                            error_snippet: str = "") -> bool:
        """登记一次测试失败并登记一条修复轮次。

        返回是否应继续重试（由调用方结合策略决定是否再次调用 do_retry）。
        """
        self._test_result = dict(test_result or {})
        if not (self._test_result or {}).get("passed", True):
            attempt = self._retry_count + 1
            self._fix_loops.append(FixLoop(
                attempt=attempt, diagnosis=diagnosis,
                error_snippet=(error_snippet or "")[-500:],
            ))
        self._touch()
        return not bool((self._test_result or {}).get("passed"))

    def do_retry(self, reason: str = "", operator: str = "system") -> int:
        """推进一次修复重试（retry_count +1）并登记事件。"""
        self._retry_count += 1
        self.record_event(GenerationRetried(self.id.value, self._retry_count,
                                            reason, operator))
        self._touch()
        return self._retry_count

    def set_artifacts(self, *, generated_tests: str = None,
                      test_result: dict = None, coverage_report: dict = None,
                      performance_report: dict = None, saved_to: str = None,
                      error: str = None) -> None:
        """提交生成产物（测试代码/运行结果/覆盖率/性能报告）。"""
        if generated_tests is not None:
            self._generated_tests = generated_tests
        if test_result is not None:
            self._test_result = dict(test_result)
        if coverage_report is not None:
            self._coverage_report = dict(coverage_report)
        if performance_report is not None:
            self._performance_report = dict(performance_report)
        if saved_to is not None:
            self._saved_to = saved_to
        if error is not None:
            self._error = error
        self._touch()

    def succeed(self, generated_tests: str = "", operator: str = "system") -> None:
        """成功收口：running → succeeded（终态）。"""
        target = GenerationStatus(GenerationStatusEnum.SUCCEEDED)
        self._ensure_transition(target)
        if generated_tests:
            self._generated_tests = generated_tests
        self._status = target
        self.record_event(GenerationJobSucceeded(self.id.value,
                                                 self._generated_tests, operator))
        self._touch()

    def fail(self, reason: str = "", operator: str = "system") -> None:
        """失败收口：running/pending → failed（终态）。"""
        target = GenerationStatus(GenerationStatusEnum.FAILED)
        self._ensure_transition(target)
        self._status = target
        self._error = reason or self._error
        self.record_event(GenerationJobFailed(self.id.value, reason, operator))
        self._touch()

    def cancel(self, operator: str = "system") -> None:
        """取消任务：pending/running → cancelled（终态）。"""
        target = GenerationStatus(GenerationStatusEnum.CANCELLED)
        self._ensure_transition(target)
        self._status = target
        self.record_event(GenerationJobCancelled(self.id.value, operator))
        self._touch()

    def _ensure_transition(self, target: GenerationStatus) -> None:
        from app.domain.generation.domain.services.generation_policy import (
            GenerationPolicy,
        )
        GenerationPolicy().ensure_transition_allowed(self._status, target)

    # ── 持久化 ───────────────────────────────────────
    def snapshot(self) -> dict:
        """导出可落库/可返回给上层视图层的字典。"""
        return self.to_dict()

    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "file_path": self._file_path,
            "source_code": self._source_code,
            "source": self._source.value,
            "test_type": self._test_type.value.value,
            "generate_script": self._generate_script,
            "status": self._status.value.value,
            "generated_tests": self._generated_tests,
            "test_result": dict(self._test_result),
            "coverage_report": dict(self._coverage_report),
            "performance_report": dict(self._performance_report),
            "retry_count": self._retry_count,
            "passed": self.passed,
            "saved_to": self._saved_to,
            "error": self._error,
            "metadata": dict(self._metadata),
            "steps": [s.to_dict() for s in self._steps],
            "fix_loops": [f.to_dict() for f in self._fix_loops],
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "version": self.version,
        }

    @staticmethod
    def from_dict(data: dict) -> "GenerationJob":
        """从持久化字典/仓储返回行重建聚合。"""
        meta = data.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta or "{}")
            except Exception:
                meta = {}
        # 兼容旧数据：coverage/test_type 存于 metadata JSON
        coverage = data.get("coverage_report") or meta.get("coverage_report") or {}
        if isinstance(coverage, str):
            try:
                coverage = json.loads(coverage or "{}")
            except Exception:
                coverage = {}
        perf = data.get("performance_report") or meta.get("performance_report") or {}
        if isinstance(perf, str):
            try:
                perf = json.loads(perf or "{}")
            except Exception:
                perf = {}
        tr = data.get("test_result") or meta.get("test_result") or {}
        if isinstance(tr, str):
            try:
                tr = json.loads(tr or "{}")
            except Exception:
                tr = {}
        return GenerationJob(
            job_id=str(data.get("id") or data.get("job_id") or ""),
            file_path=data.get("file_path", ""),
            source_code=data.get("source_code", ""),
            source=data.get("source", "single"),
            test_type=data.get("test_type", "functional"),
            generate_script=bool(data.get("generate_script", True)),
            status=data.get("status", "pending"),
            generated_tests=data.get("generated_tests", ""),
            test_result=tr,
            coverage_report=coverage,
            performance_report=perf,
            retry_count=int(data.get("retry_count") or 0),
            saved_to=data.get("saved_to", ""),
            error=data.get("error", ""),
            metadata=meta,
            steps=data.get("steps") or [],
            fix_loops=data.get("fix_loops") or [],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            version=int(data.get("version") or 0),
        )


__all__ = ["GenerationJob"]
