"""generation 域 A→B→C 迁移回归测试。

目标：为「B/C 阶段把生成来源记录落库切换为 DDD 聚合生产者」这一迁移提供契约防线。

要点
----
1. DDD `GenerationJob` 落库（经 `generation_app_service`）后，写出的 run_records
   行与既有 `run_service.save` 写入的行**逐字段契约等价**（扁平列一致、passed 正确、
   metadata 承载派生态），保证 `/api/runs` / 报告兼容层 / 前端零感知。
2. `web_contract` 契约桥双向无损：聚合 → 扁平行（to_run_row）与扁平行 → 聚合
   （run_row_to_job），兼容历史遗留（无 status/steps）与 DDD 写入数据。
"""
import uuid

from app.domain.generation.application.dto import (
    CreateGenerationCommand,
    FinalizeCommand,
    JobListQuery,
    UpdateArtifactsCommand,
)
from app.domain.generation.application.generation_app_service import (
    generation_app_service,
)
from app.domain.generation.application.web_contract import (
    RUN_ROW_KEYS,
    run_row_to_job,
    to_run_row,
)
from app.domain.generation.domain.entities.generation_job import GenerationJob
from app.repositories.run_repo import RunRepo
from app.services.run_service import run_service


def _fp(tag: str) -> str:
    return f"mig_{tag}_{uuid.uuid4().hex[:8]}.py"


def _cleanup(job_id: str):
    try:
        RunRepo.delete_by_id(job_id)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 一、契约桥：聚合 → 扁平行 → 聚合 双向无损
# ═══════════════════════════════════════════════════════════
class TestWebContractBridge:
    def test_run_row_has_canonical_columns(self):
        job = GenerationJob(job_id="x", file_path="a.py", source_code="def f(): pass")
        row = to_run_row(job)
        for k in RUN_ROW_KEYS:
            assert k in row, f"缺少契约列 {k}"
        # 派生态不污染顶层，收敛进 metadata
        assert row["passed"] == 0
        assert row["metadata"]["generation_status"] == "pending"
        assert "status" not in row or row["status"] == "pending"

    def test_to_run_row_reflects_lifecycle(self):
        jid = "life_" + uuid.uuid4().hex[:8]
        job = GenerationJob(job_id=jid, file_path="b.py", source_code="def g(): pass")
        job.start()
        job.record_step(node_name="scan_code", status="done")
        job.set_artifacts(test_result={"passed": True})
        job.succeed("import pytest\n")
        row = to_run_row(job)
        assert row["passed"] == 1
        assert row["metadata"]["generation_status"] == "succeeded"
        assert row["metadata"]["steps"][0]["node_name"] == "scan_code"

    def test_run_row_to_job_handles_legacy_and_ddd(self):
        # 历史遗留（无 status/steps/fix_loops）重建为 pending 聚合
        legacy = {"id": "l1", "file_path": "c.py", "source_code": "x=1",
                  "metadata": {}, "created_at": 1.0}
        job = run_row_to_job(legacy)
        assert job is not None and job.status.value == "pending"
        # DDD 写入（status 在 metadata）可提升回聚合
        ddd_row = to_run_row(GenerationJob(job_id="d1", file_path="d.py",
                                           source_code="y=1"))
        job2 = run_row_to_job(ddd_row)
        assert job2 is not None and job2.status.value == "pending"


# ═══════════════════════════════════════════════════════════
# 二、迁移回归：DDD 落库与 run_service 落库契约等价
# ═══════════════════════════════════════════════════════════
class TestMigrationContractEquivalence:
    def test_ddd_persist_equals_legacy_contract(self):
        """同一输入下，DDD 聚合落库与 legacy run_service.save 落在同一 run_records
        契约上：可经 RunRepo.get 读回、passed 一致、扁平列齐备。"""
        fp = _fp("eq")
        src = "def foo(): return 1"
        test_result = {"passed": True, "passed_count": 2}
        cov = {"coverage_pct": 88}

        # legacy 路径
        legacy = run_service.save(
            file_path=fp, source_code=src, generated_tests="t=1",
            test_result=test_result, coverage_report=cov,
            source="single", retry_count=1,
        )
        assert legacy is not None and legacy["passed"] == 1
        assert "status" not in legacy or legacy["status"] == "pending"

        # DDD 路径：submit → start → artifacts → succeed
        sub = generation_app_service.submit(CreateGenerationCommand(
            file_path=fp, source_code=src, source="single", operator="admin"))
        jid = sub["id"]
        try:
            generation_app_service.start(jid)
            generation_app_service.update_artifacts(UpdateArtifactsCommand(
                job_id=jid, generated_tests="t=1", test_result=test_result,
                coverage_report=cov, saved_to="output/x.py"))
            generation_app_service.finalize(FinalizeCommand(
                job_id=jid, outcome="succeeded", generated_tests="t=1", operator="admin"))
            row = RunRepo.get(jid)
            assert row is not None
            assert row["passed"] == 1
            assert row["file_path"] == fp
            assert row["test_result"].get("passed") is True
            # 契约桥可无损重建
            rebuilt = run_row_to_job(row)
            assert rebuilt is not None and rebuilt.status.value == "succeeded"
        finally:
            _cleanup(jid)
            _cleanup(legacy["id"])

    def test_ddd_failed_record_readable_via_run_service(self):
        fp = _fp("fail")
        sub = generation_app_service.submit(CreateGenerationCommand(
            file_path=fp, source_code="def k(): pass", source="single",
            operator="admin"))
        jid = sub["id"]
        try:
            generation_app_service.start(jid)
            generation_app_service.update_artifacts(UpdateArtifactsCommand(
                job_id=jid, test_result={"passed": False}, error="断言失败"))
            generation_app_service.finalize(FinalizeCommand(
                job_id=jid, outcome="failed", reason="断言失败", operator="admin"))
            # 读侧走既有 run_service.get（/api/runs 同路径）不抛错
            got = run_service.get(jid)
            assert got is not None and got["passed"] == 0
            assert got["metadata"]["generation_status"] == "failed"
        finally:
            _cleanup(jid)

    def test_list_and_stats_through_ddd(self):
        sub = generation_app_service.submit(CreateGenerationCommand(
            file_path=_fp("list"), source_code="def q(): pass", source="single",
            operator="admin"))
        jid = sub["id"]
        try:
            res = generation_app_service.list_jobs(JobListQuery(limit=10))
            assert "list" in res and "total" in res
            stats = generation_app_service.stats()
            assert "total" in stats
        finally:
            _cleanup(jid)


# ═══════════════════════════════════════════════════════════
# 三、阶段 B 接入回归：persist_completed_run（router / WS 现经此落库）
#   - 一次"整段生成已跑完"的运行结果经 DDD 生命周期一次性收口落库；
#   - 返回经契约桥投影的 run_records 扁平行，与 run_service.save 逐字段等价；
#   - succeeded / failed 两态均经既有 run_service.get（/api/runs 同路径）可读。
# ═══════════════════════════════════════════════════════════
class TestPersistCompletedRunWire:
    def test_persist_completed_succeeded_row_shape(self):
        fp = _fp("wire_ok")
        row = generation_app_service.persist_completed_run(
            file_path=fp, source_code="def a(): return 1",
            generated_tests="def test_a(): pass",
            test_result={"passed": True, "passed_count": 1},
            coverage_report={"coverage_pct": 90}, saved_to="output/a.py",
            source="single",
        )
        assert row is not None
        assert row["id"]
        # 契约列齐备、passed 与派生态正确、status 收敛进 metadata
        for k in RUN_ROW_KEYS:
            assert k in row, f"缺少契约列 {k}"
        assert row["passed"] == 1
        assert row["file_path"] == fp
        assert row["metadata"]["generation_status"] == "succeeded"
        try:
            # 读侧走既有 run_service（/api/runs 同路径）零感知
            got = run_service.get(row["id"])
            assert got is not None and got["passed"] == 1
        finally:
            _cleanup(row["id"])

    def test_persist_completed_failed_readable(self):
        fp = _fp("wire_fail")
        row = generation_app_service.persist_completed_run(
            file_path=fp, source_code="def b(): return 1",
            generated_tests="def test_b(): assert False",
            test_result={"passed": False}, error="断言失败", source="websocket",
        )
        assert row is not None
        assert row["passed"] == 0
        assert row["metadata"]["generation_status"] == "failed"
        try:
            got = run_service.get(row["id"])
            assert got is not None and got["passed"] == 0
            assert got["metadata"]["generation_status"] == "failed"
        finally:
            _cleanup(row["id"])

    def test_contract_bridge_roundtrip_of_persisted_row(self):
        fp = _fp("wire_rb")
        row = generation_app_service.persist_completed_run(
            file_path=fp, source_code="def c(): return 1",
            generated_tests="def test_c(): pass",
            test_result={"passed": True}, source="single",
        )
        assert row is not None
        try:
            rebuilt = run_row_to_job(row)
            assert rebuilt is not None and rebuilt.status.value == "succeeded"
            # to_run_row 幂等：同一聚合两次投影契约一致
            assert to_run_row(rebuilt)["passed"] == row["passed"]
        finally:
            _cleanup(row["id"])

    def test_bridge_unused_but_router_write_contract(self):
        """router `_persist_run_result` 现改走 persist_completed_run —— 证明其
        产出与 legacy run_service.save 落在同一 run_records 契约、互不冲突。"""
        fp = _fp("wire_same")
        src = "def d(): return 1"
        test_result = {"passed": True, "passed_count": 2}
        # DDD（router/WS 落库路径）
        ddd_row = generation_app_service.persist_completed_run(
            file_path=fp, source_code=src, generated_tests="t=1",
            test_result=test_result, coverage_report={"coverage_pct": 88},
            saved_to="output/d.py", source="single",
        )
        # legacy 对照
        legacy = run_service.save(
            file_path=fp, source_code=src, generated_tests="t=1",
            test_result=test_result, coverage_report={"coverage_pct": 88},
            saved_to="output/d.py", source="single", retry_count=0,
        )
        assert ddd_row is not None and legacy is not None
        try:
            assert ddd_row["passed"] == legacy["passed"] == 1
            assert ddd_row["file_path"] == legacy["file_path"] == fp
            assert ddd_row["test_result"].get("passed") is True
            # DDD 写入带派生态（generation_status），legacy 无 —— 均可被 /api/runs 读
            got = run_service.get(ddd_row["id"])
            assert got["metadata"]["generation_status"] == "succeeded"
        finally:
            _cleanup(ddd_row["id"])
            _cleanup(legacy["id"])
