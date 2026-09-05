"""DDD 生成编排域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：值对象守卫、状态机、步骤/修复循环登记、收口。
  2. 应用服务全链路（对接真实 RunRepo 存储）。
"""
import uuid

import pytest

from app.domain.common.exceptions import DomainValidationError
from app.domain.generation.application.dto import (
    CancelCommand,
    CreateGenerationCommand,
    FinalizeCommand,
    JobListQuery,
    RecordStepCommand,
    RetryCommand,
    UpdateArtifactsCommand,
)
from app.domain.generation.application.generation_app_service import (
    generation_app_service,
)
from app.domain.generation.domain.value_objects.coverage_gate import CoverageGate
from app.domain.generation.domain.value_objects.generation_status import (
    GenerationStatus,
    GenerationStatusEnum,
)
from app.domain.generation.domain.value_objects.job_source import JobSource

TAG = "dddg"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}.py"


def _job(**kw):
    from app.domain.generation.domain.entities.generation_job import GenerationJob
    kw.setdefault("job_id", uuid.uuid4().hex[:12])
    kw.setdefault("file_path", _mk())
    kw.setdefault("source_code", "def foo(): return 1")
    return GenerationJob(**kw)


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestValueObjects:
    def test_job_source_guard(self):
        assert str(JobSource("single")) == "single"
        assert str(JobSource("WEBSOCKET")) == "websocket"
        with pytest.raises(DomainValidationError):
            JobSource("unknown")

    def test_generation_status_normalize(self):
        assert str(GenerationStatus("RUNNING")) == "running"

    def test_status_state_machine(self):
        j = _job()
        assert str(j.status) == "pending"
        j.start()
        assert str(j.status) == "running"
        # running 重复 start 为幂等 no-op，不报错
        j.start()
        assert str(j.status) == "running"
        # 但不可从 running 直接回 pending（同一状态迁移校验）
        with pytest.raises(DomainValidationError):
            j._ensure_transition(GenerationStatus(GenerationStatusEnum.PENDING))
        j.succeed()
        assert str(j.status) == "succeeded"
        # 终态不可再流转
        with pytest.raises(DomainValidationError):
            j.fail()

    def test_cov_gate_threshold(self):
        assert CoverageGate({"passed_threshold": True}).passed_threshold
        assert not CoverageGate({"passed_threshold": False}).passed_threshold
        gate = CoverageGate({"line_coverage_pct": 90}, threshold=80)
        assert gate.passed_threshold
        assert not CoverageGate({"line_coverage_pct": 50}, threshold=80).passed_threshold


class TestAggregate:
    def test_required_file_path(self):
        from app.domain.generation.domain.entities.generation_job import GenerationJob
        with pytest.raises(DomainValidationError):
            GenerationJob(job_id="x", file_path="")

    def test_step_recording(self):
        j = _job()
        j.record_step(node_name="scan_code", status="done")
        assert len(j.steps) == 1
        assert j.steps[0].node_name == "scan_code"
        assert j.steps[0].status.value == "done"

    def test_test_failure_and_retry(self):
        j = _job()
        j.start()
        j.set_artifacts(test_result={"passed": False, "stderr": "assert 0"})
        j.record_test_failure(test_result={"passed": False}, diagnosis="断言失败")
        assert len(j.fix_loops) == 1
        j.do_retry(reason="断言失败")
        assert j.retry_count == 1
        assert len(j.pull_domain_events()) >= 1

    def test_events_collected(self):
        j = _job()
        j.start()
        ev_types = [type(e).__name__ for e in j.pull_domain_events()]
        assert "GenerationJobStarted" in ev_types

    def test_final_state_by_artifacts(self):
        j = _job()
        j.start()
        j.set_artifacts(test_result={"passed": True})
        j.succeed("import pytest\n")
        assert j.passed
        assert j.generated_tests


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（真实存储）
# ═══════════════════════════════════════════════════════════
@pytest.fixture
def fresh_job():
    from app.repositories.run_repo import RunRepo
    job = generation_app_service.submit(CreateGenerationCommand(
        file_path=_mk(), source_code="def f(): return 1",
        test_type="api", source="single", operator="admin",
    ))
    jid = job["id"]
    yield jid
    try:
        RunRepo.delete_by_id(jid)
    except Exception:
        pass


def test_submit_and_get(fresh_job):
    got = generation_app_service.get(fresh_job)
    assert got is not None and got["status"] == "pending"


def test_lifecycle(fresh_job):
    generation_app_service.start(fresh_job)
    generation_app_service.record_step(RecordStepCommand(
        job_id=fresh_job, node_name="generate_tests", status="done", operator="admin"))
    generation_app_service.update_artifacts(UpdateArtifactsCommand(
        job_id=fresh_job, test_result={"passed": True},
        generated_tests="import pytest\n", coverage_report={"passed_threshold": True},
    ))
    final = generation_app_service.finalize(FinalizeCommand(
        job_id=fresh_job, outcome="succeeded", operator="admin"))
    assert final["status"] == "succeeded"
    assert final["passed"]


def test_fail_path(fresh_job):
    generation_app_service.start(fresh_job)
    final = generation_app_service.finalize(FinalizeCommand(
        job_id=fresh_job, outcome="failed", reason="不可恢复错误", operator="admin"))
    assert final["status"] == "failed"
    assert final["error"] == "不可恢复错误"


def test_retry_flow(fresh_job):
    generation_app_service.start(fresh_job)
    r = generation_app_service.retry(RetryCommand(
        job_id=fresh_job, test_result={"passed": False},
        diagnosis="断言失败", operator="admin"))
    assert r["retry_count"] == 1
    assert len(r["fix_loops"]) == 1


def test_cancel(fresh_job):
    generation_app_service.start(fresh_job)
    c = generation_app_service.cancel(CancelCommand(job_id=fresh_job, operator="admin"))
    assert c["status"] == "cancelled"


def test_list_and_stats(fresh_job):
    generation_app_service.list_jobs(JobListQuery(limit=10))
    stats = generation_app_service.stats()
    assert "total" in stats
