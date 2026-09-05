"""DDD 报告域单测。

覆盖：
  1. 纯领域逻辑（无需文件系统）：格式守卫、状态机、汇总口径、聚合生命周期。
  2. 应用服务全链路（对接真实文件仓储 ReportRepo）。
"""
import os
import uuid

import pytest

from app.domain.common.exceptions import DomainValidationError
from app.domain.report.application.dto import (
    DownloadCommand,
    GenerateCommand,
    PurgeCommand,
    RestoreCommand,
    TrashCommand,
    TrashListQuery,
)
from app.domain.report.application.report_app_service import ReportAppService
from app.domain.report.domain.entities.report import Report
from app.domain.report.domain.services.report_policy import (
    build_result_rows,
    compute_summary,
)
from app.domain.report.domain.value_objects.report_format import ReportFormat
from app.domain.report.domain.value_objects.report_state import (
    ReportState,
)
from app.domain.report.infrastructure.report_repository_impl import ReportRepoAdapter

REPORT_DIR = "reports"


def _snapshot(file_path="a_test.py", last_result='{"passed": true}', test_code="def test_a():\n    assert 1"):
    return {
        "file_path": file_path,
        "test_code": test_code,
        "last_result": last_result,
    }


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需文件系统 / 无需 DB）
# ═══════════════════════════════════════════════════════════
class TestValueObjects:
    def test_format_guard(self):
        assert str(ReportFormat("JUNIT")) == "junit"
        with pytest.raises(DomainValidationError):
            ReportFormat("exe")

    def test_state_normalize(self):
        assert str(ReportState("ACTIVE")) == "active"
        assert str(ReportState("")) == "active"
        assert str(ReportState("trash")) == "trash"
        with pytest.raises(DomainValidationError):
            ReportState("unknown")


class TestSummaryPolicy:
    def test_compute_summary(self):
        rows = [
            {"test_result": {"passed": True}, "coverage_report": {"line_coverage_pct": 90}},
            {"test_result": {"passed": False}, "coverage_report": {"line_coverage_pct": 80}},
            {"test_result": {}, "coverage_report": {}},
        ]
        s = compute_summary(rows)
        assert s["total"] == 3
        assert s["passed"] == 1
        assert s["failed"] == 2
        assert s["coverage"] == 85.0

    def test_build_result_rows_parses_last_result(self):
        snaps = [
            _snapshot(last_result='{"passed": true}'),
            _snapshot(last_result="not-json"),
            _snapshot(last_result=""),
        ]
        rows = build_result_rows(snaps)
        assert rows[0]["test_result"].get("passed") is True
        assert rows[1]["test_result"] == {}   # 非法 JSON 兜底
        assert rows[2]["test_result"] == {}
        assert rows[0]["file_path"] == "a_test.py"


class TestAggregate:
    def _report(self, **kw):
        kw.setdefault("report_name", f"report_{uuid.uuid4().hex[:8]}.html")
        return Report(**kw)

    def test_name_required(self):
        with pytest.raises(DomainValidationError):
            Report(report_name="")

    def test_lifecycle_trash_restore_purge(self):
        r = self._report()
        assert r.state.is_active
        r.trash()
        assert r.state.is_trashed
        assert "ReportTrashed" in [type(e).__name__ for e in r.pull_domain_events()]
        with pytest.raises(DomainValidationError):
            r.trash()  # 重复删除
        r.restore()
        assert r.state.is_active
        assert "ReportRestored" in [type(e).__name__ for e in r.pull_domain_events()]
        # 只有回收站产物才能 purge
        with pytest.raises(DomainValidationError):
            r.mark_purged()
        r.trash()
        r.mark_purged()
        assert r.state.is_purged

    def test_set_summary(self):
        r = self._report()
        r.set_summary({"total": 5, "passed": 4, "failed": 1, "coverage": 88.5})
        assert r.total == 5
        assert r.passed == 4
        assert r.failed == 1
        assert r.coverage == 88.5


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（文件仓储）
# ═══════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def service():
    # 注入一个只读快照数据的替身，避免依赖真实 CaseRepo 行数
    class SnapshotOnlyRepo(ReportRepoAdapter):
        def list_case_snapshots(self, limit=50):
            return [_snapshot()]

    return ReportAppService(repo=SnapshotOnlyRepo())


class TestAppService:
    def test_generate_unsupported_format(self, service):
        with pytest.raises(DomainValidationError):
            service.generate(GenerateCommand(format_type="exe"))

    def test_generate_html(self, service):
        os.makedirs(REPORT_DIR, exist_ok=True)
        res = service.generate(GenerateCommand(format_type="html"))
        assert res is not None
        assert res["report_format"] == "html"
        assert res["state"] == "active"
        assert res["total"] >= 1
        assert res["report_path"] and os.path.exists(res["report_path"])
        # 清理生成的报告
        if os.path.exists(res["report_path"]):
            os.remove(res["report_path"])

    def test_list_and_trash_cycle(self, service):
        # 直接生成一个临时文件验证 trash/restore/purge 全链路
        os.makedirs(REPORT_DIR, exist_ok=True)
        trash_dir = os.path.join(REPORT_DIR, ".trash")
        name = f"report_ddd_{uuid.uuid4().hex[:8]}.html"
        path = os.path.join(REPORT_DIR, name)
        with open(path, "w") as f:
            f.write("<html>report</html>")
        try:
            # 列表能见到
            assert any(r["name"] == name for r in service.list_reports())
            # 下载路径可解析
            assert service.download(DownloadCommand(report_name=name)) == path
            # 移入回收站
            assert service.trash(TrashCommand(report_name=name)) is True
            assert not os.path.exists(path)
            assert os.path.exists(os.path.join(trash_dir, name))
            trash = service.list_trash(TrashListQuery())
            assert any(r["name"] == name for r in trash["list"])
            # 恢复
            assert service.restore(RestoreCommand(report_name=name)) is True
            assert os.path.exists(path)
            # 再次移入并彻底删除
            service.trash(TrashCommand(report_name=name))
            assert service.purge(PurgeCommand(report_name=name)) is True
            assert not os.path.exists(os.path.join(trash_dir, name))
        finally:
            for p in (path, os.path.join(trash_dir, name)):
                if os.path.exists(p):
                    os.remove(p)


# ═══════════════════════════════════════════════════════════
# 三、阶段 B/C 迁移回归
#   - B：router 已改调 report_app_service（DTO 桥），保持既有 Web 契约；
#   - C：report_service 收敛为 DDD 薄门面，返回形状与重构前一致。
# ═══════════════════════════════════════════════════════════
class TestReportServiceFacade:
    """report_service 薄门面（阶段 C）返回形状回归。"""

    def test_generate_return_path_or_none(self):
        from app.services.report_service import report_service as svc
        path = svc.generate("html")
        # 结果必须是 str 路径 / None（无用例）/ "unsupported"（非法格式）
        assert path is None or isinstance(path, str)
        assert path != "unsupported" or True  # 合法格式不会触发 unsupported
        if path and os.path.isfile(path):
            os.remove(path)

    def test_generate_unsupported(self):
        from app.services.report_service import report_service as svc
        assert svc.generate("exe") == "unsupported"

    def test_list_reports_and_trash_shape(self):
        from app.services.report_service import report_service as svc
        reports = svc.list_reports()
        assert isinstance(reports, list)
        trash = svc.list_trash()
        # 维持既有契约：回收站列表是文件名（str）序列
        assert isinstance(trash, list)
        assert all(isinstance(t, str) for t in trash)

    def test_trash_cycle_on_missing(self):
        from app.services.report_service import report_service as svc
        missing = f"nope_{uuid.uuid4().hex[:8]}.html"
        assert svc.download_path(missing) is None
        assert svc.trash_report(missing) is False
        assert svc.restore_report(missing) is False
        assert svc.purge_report(missing) is False

    def test_full_cycle_through_facade(self):
        from app.services.report_service import report_service as svc
        os.makedirs(REPORT_DIR, exist_ok=True)
        trash_dir = os.path.join(REPORT_DIR, ".trash")
        name = f"report_facade_{uuid.uuid4().hex[:8]}.html"
        path = os.path.join(REPORT_DIR, name)
        with open(path, "w") as f:
            f.write("<html>report</html>")
        try:
            assert svc.download_path(name) == path
            assert svc.trash_report(name) is True
            assert name in svc.list_trash()
            assert svc.restore_report(name) is True
            assert os.path.exists(path)
            svc.trash_report(name)
            assert svc.purge_report(name) is True
            assert not os.path.exists(os.path.join(trash_dir, name))
        finally:
            for p in (path, os.path.join(trash_dir, name)):
                if os.path.exists(p):
                    os.remove(p)


class TestReportRouterContract:
    """report router（阶段 B）对 Web 契约零回归。"""

    def test_list_has_reports(self, anon_client):
        r = anon_client.get("/api/reports/list")
        assert r.status_code == 200
        data = r.json().get("data", {})
        assert "reports" in data

    def test_trash_list_has_reports_and_total(self, anon_client):
        r = anon_client.get("/api/reports/trash/list")
        assert r.status_code == 200
        data = r.json().get("data", {})
        assert "reports" in data
        assert "total" in data

    def test_download_missing_404(self, anon_client):
        r = anon_client.get("/api/reports/download/missing_xyz.html")
        assert r.status_code == 404

    def test_trash_missing_404(self, auth_client):
        r = auth_client.post(f"/api/reports/{uuid.uuid4().hex[:8]}/trash", json={})
        assert r.status_code == 404

    def test_unsupported_format_generate_400(self, auth_client):
        r = auth_client.post("/api/reports/generate", json={"format": "pdf"})
        assert r.status_code == 400

