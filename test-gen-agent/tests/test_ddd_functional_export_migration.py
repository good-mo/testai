"""DDD functional_export 域阶段 C 薄门面接线回归测试。

背景
----
`app/domain/functional_export/` DDD 层就绪后，本测试锁定阶段 C 薄门面接线契约：
`app/services/functional_export_service.py` 已收敛为对 `export_app_service` 的
**薄委托门面** —— export_cases_excel / export_cases_xmind / task_status /
download_path / download_task_meta 全部经 DDD 应用门面（聚合根 `CaseExportJob`
校验导出 kind 并承载触发语义）。

对外函数签名与返回 schema 与重构前一致（导出目录/文件路径/任务登记语义零变化），
routers 调用方零改动。本测试断言确实走 DDD 门面。
"""
import uuid

from app.domain.functional_export.application.dto import ExportCasesCommand
from app.domain.functional_export.application.export_app_service import (
    export_app_service as ddd,
)
from app.services.functional_export_service import (
    download_path,
    download_task_meta,
    export_cases_excel,
    export_cases_xmind,
    task_status,
)


# ═══════════════════════════════════════════════════════════
# 一、薄门面确实委托 DDD 应用服务
# ═══════════════════════════════════════════════════════════
def test_export_cases_delegates_to_ddd(monkeypatch):
    """export_cases_excel/xmind 委托 DDD app_service，参数经 DTO 翻译。"""
    seen = []
    orig_export = ddd.export_cases

    def fake_export(cmd):
        assert isinstance(cmd, ExportCasesCommand)
        seen.append(cmd.kind)
        return {"fileId": "f1", "taskId": "t1", "count": 0}

    monkeypatch.setattr(ddd, "export_cases", fake_export)
    body = {"selectAll": True}
    export_cases_excel(body)
    assert "excel" in seen
    export_cases_xmind(body)
    assert "xmind" in seen
    assert len(seen) == 2


def test_task_status_delegates_to_ddd(monkeypatch):
    """task_status 委托 DDD app_service。"""
    seen = []
    orig = ddd.task_status

    def fake():
        seen.append(True)
        return orig()

    monkeypatch.setattr(ddd, "task_status", fake)
    task_status()
    assert seen == [True]


def test_download_delegates_to_ddd(monkeypatch):
    """download_path / download_task_meta 委托 DDD app_service。"""
    seen = []

    def fake_path(fid):
        seen.append(("path", fid))
        return None

    def fake_meta(fid):
        seen.append(("meta", fid))
        return None

    monkeypatch.setattr(ddd, "download_path", fake_path)
    monkeypatch.setattr(ddd, "download_task_meta", fake_meta)

    download_path("f1")
    assert ("path", "f1") in seen
    download_task_meta("f1")
    assert ("meta", "f1") in seen


# ═══════════════════════════════════════════════════════════
# 二、端到端：门面不阻塞真实导出/下载
# ═══════════════════════════════════════════════════════════
def test_export_real_flow():
    """经薄门面发起真实导出（excel 格式），返回含 fileId。"""
    body = {"selectAll": False, "selectIds": []}
    result = export_cases_excel(body)
    assert isinstance(result, dict)
    assert "fileId" in result
    fid = result["fileId"]
    p = download_path(fid)
    assert p is not None
    meta = download_task_meta(fid)
    assert meta is not None and "fileId" in meta
