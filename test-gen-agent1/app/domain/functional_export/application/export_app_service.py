"""功能用例导出应用服务（委托 cases/export 上下文）。

ExportAppService 以 `CaseExportJob` 聚合根承载导出作业语义：
构造时校验 kind 合法性并记录触发事件；导出成功后标记完成/失败。
实际文件生成与任务持久化委托 infrastructure ExportRepoAdapter。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.domain.functional_export.application.dto import ExportCasesCommand
from app.domain.functional_export.domain.entities.case_export import CaseExportJob
from app.domain.functional_export.infrastructure.export_repository_impl import (
    ExportRepoAdapter,
)


class ExportAppService:
    """功能用例导出用例编排服务。"""

    def __init__(self, repo=None):
        self._repo = repo or ExportRepoAdapter()

    def export_cases(self, cmd: ExportCasesCommand) -> dict:
        """发起功能用例导出作业。

        以 `CaseExportJob` 聚合承载导出语义：校验 kind、触发领域事件，
        随后委托 infra 执行实际文件生成。结果为 dict 含 fileId/count。
        """
        job = CaseExportJob(kind=cmd.kind, body=cmd.body, _created=True)
        result = self._repo.export_cases(cmd.body, cmd.kind)
        if result:
            job.mark_completed(
                file_id=result.get("fileId", ""),
                count=result.get("count", 0),
            )
        else:
            job.mark_failed()
        return result

    def task_status(self) -> Optional[Dict[str, Any]]:
        return self._repo.task_status()

    def download_path(self, file_id: str) -> Optional[str]:
        return self._repo.download_path(file_id)

    def download_task_meta(self, file_id: str) -> Optional[Dict[str, Any]]:
        return self._repo.download_task_meta(file_id)


export_app_service = ExportAppService()
