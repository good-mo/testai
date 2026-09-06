"""DDD 运行记录 / 报告（RunRecord）域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：来源合法性、报告名非空守卫、passed 派生、rename。
  2. 应用服务全链路（对接真实 RunRepo / run_records 存储）：save / get /
     list / count / stats / update / rename / delete / delete_batch / clear。
  3. run_service 薄门面委托：保持既有方法签名与返回形状契约。
"""
import uuid

import pytest

from app.domain.common.exceptions import DomainValidationError
from app.domain.runs.application.dto import (
    ClearRunRecordsCommand,
    RenameRunRecordCommand,
    RunRecordListQuery,
    SaveRunRecordCommand,
    UpdateRunRecordCommand,
)
from app.domain.runs.application.run_record_app_service import (
    run_record_app_service,
)
from app.domain.runs.domain.entities.run_record import RunRecord
from app.domain.runs.domain.value_objects.run_source import (
    VALID_SOURCES,
    RunSource,
)

TAG = "dddrunrec"


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:6]}"


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestRunSource:
    def test_valid_sources(self):
        assert VALID_SOURCES == {"single", "project", "websocket", "task"}
        assert str(RunSource("single")) == "single"
        assert str(RunSource("WEBSOCKET")) == "websocket"

    def test_invalid_source(self):
        with pytest.raises(DomainValidationError):
            RunSource("bad_source")


class TestRunRecordAggregate:
    def test_passed_derived_from_test_result(self):
        r = RunRecord(record_id=_mk(), file_path="demo.py",
                      test_result={"passed": True})
        assert r.passed is True
        r2 = RunRecord(record_id=_mk(), file_path="demo.py",
                       test_result={"passed": False})
        assert r2.passed is False

    def test_rename_updates_file_path(self):
        r = RunRecord(record_id=_mk(), file_path="a.py")
        r.rename("b.py")
        assert r.file_path == "b.py"

    def test_rename_empty_guard(self):
        r = RunRecord(record_id=_mk(), file_path="a.py")
        with pytest.raises(DomainValidationError):
            r.rename("   ")

    def test_set_results_represents_passed(self):
        r = RunRecord(record_id=_mk(), file_path="a.py",
                      test_result={"passed": False})
        r.set_results(test_result={"passed": True})
        assert r.passed is True

    def test_to_persist_row_passed_int(self):
        r = RunRecord(record_id=_mk(), file_path="a.py",
                      test_result={"passed": True})
        row = r.to_persist_row()
        assert row["passed"] == 1
        assert row["file_path"] == "a.py"


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（对接真实 RunRepo 存储）
# ═══════════════════════════════════════════════════════════
class TestRunRecordAppService:
    def test_save_get_list(self):
        tag = _mk()
        d = run_record_app_service.save(SaveRunRecordCommand(
            file_path=f"{tag}_demo.py", source="single",
            test_result={"passed": True, "total": 3},
            coverage_report={"coverage_pct": 90.0},
        ))
        assert d is not None and d["id"]
        rid = d["id"]
        try:
            got = run_record_app_service.get(rid)
            assert got["file_path"] == f"{tag}_demo.py"
            assert got["passed"] is True
            assert got["coverage_report"]["coverage_pct"] == 90.0

            res = run_record_app_service.list(
                RunRecordListQuery(file_path=tag, limit=50))
            assert res["total"] >= 1
            assert any(r["id"] == rid for r in res["list"])
        finally:
            run_record_app_service.delete(rid)

    def test_count_and_stats(self):
        tag = _mk()
        run_record_app_service.save(SaveRunRecordCommand(
            file_path=f"{tag}_a.py", test_result={"passed": True}))
        run_record_app_service.save(SaveRunRecordCommand(
            file_path=f"{tag}_b.py", test_result={"passed": False}))
        try:
            cnt = run_record_app_service.count(RunRecordListQuery(file_path=tag))
            assert cnt >= 2
            stats = run_record_app_service.stats()
            assert stats["total"] >= 2
        finally:
            run_record_app_service.clear(ClearRunRecordsCommand(source="single"))

    def test_update_and_rename(self):
        tag = _mk()
        d = run_record_app_service.save(SaveRunRecordCommand(
            file_path=f"{tag}_a.py", test_result={"passed": True}))
        rid = d["id"]
        try:
            run_record_app_service.update(UpdateRunRecordCommand(
                record_id=rid, error="boom", metadata={"k": "v"}))
            got = run_record_app_service.get(rid)
            assert got["error"] == "boom"
            assert got["metadata"]["k"] == "v"

            run_record_app_service.rename(RenameRunRecordCommand(
                record_id=rid, new_name=f"{tag}_renamed.py"))
            assert run_record_app_service.get(rid)["file_path"] == f"{tag}_renamed.py"
        finally:
            run_record_app_service.delete(rid)

    def test_delete_and_batch_delete(self):
        tag = _mk()
        ids = []
        for i in range(3):
            d = run_record_app_service.save(SaveRunRecordCommand(
                file_path=f"{tag}_b{i}.py"))
            ids.append(d["id"])
        deleted = run_record_app_service.delete_batch(ids)
        assert deleted == 3
        for rid in ids:
            assert run_record_app_service.get(rid) is None

    def test_clear(self):
        tag = _mk()
        run_record_app_service.save(SaveRunRecordCommand(file_path=f"{tag}_c.py"))
        cleared = run_record_app_service.clear(ClearRunRecordsCommand(source="single"))
        assert cleared >= 1


# ═══════════════════════════════════════════════════════════
# 三、run_service 薄门面契约（保持既有形状）
# ═══════════════════════════════════════════════════════════
class TestRunServiceCompatibility:
    def test_run_service_delegation(self):
        from app.services.run_service import run_service

        tag = _mk()
        d = run_service.save(file_path=f"{tag}.py", source="single",
                             test_result={"passed": True})
        assert isinstance(d, dict) and d["id"]
        assert d["passed"] == 1  # 既有契约：passed 归一为 0/1
        rid = d["id"]
        try:
            # list 返回 list（既有契约）
            records = run_service.list(file_path=tag, limit=50)
            assert isinstance(records, list) and len(records) >= 1
            # count 返回 int
            assert isinstance(run_service.count(file_path=tag), int)
            # get 返回 dict
            got = run_service.get(rid)
            assert got and got["id"] == rid
            # get_stats 返回 dict
            stats = run_service.get_stats()
            assert isinstance(stats, dict) and "total" in stats
            # rename_report
            assert run_service.rename_report(rid, f"{tag}_new.py") is True
            assert run_service.get(rid)["file_path"] == f"{tag}_new.py"
            # delete_report
            assert run_service.delete_report(rid) is True
        finally:
            run_service.clear()
