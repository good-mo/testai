# app/services/report_service.py
"""报告中心业务逻辑层（report 域 DDD 接入 · 阶段 C 薄门面）。

业务规则已下沉到 report 域领域层（`app/domain/report/`：格式守卫、状态机、
汇总口径），本四层 Service 收敛为对 DDD 应用服务 `report_app_service` 的
**薄委托门面**，仅保留历史方法签名以兼容既有调用方 / 便于回滚。对外语义
与返回形状与重构前保持一致（复用 DDD 聚合 to_dict 的 name 承载文件名）。

> 推荐调用方直接使用 `report_app_service`；本类仅作过渡兼容层保留。
"""
from __future__ import annotations

from typing import Optional

from app.domain.report.application.dto import (
    DownloadCommand,
    GenerateCommand,
    PurgeCommand,
    RestoreCommand,
    TrashCommand,
    TrashListQuery,
)
from app.domain.report.application.report_app_service import (
    report_app_service as _ddd_service,
)


class ReportService:
    """报告中心服务（report 域 DDD 薄门面）。"""

    def generate(self, format_type: str = "html"):
        """生成测试报告。

        Returns:
            str: 报告文件路径（成功时）
            None: 无用例数据
            "unsupported": 不支持的格式
        """
        try:
            result = _ddd_service.generate(GenerateCommand(format_type=format_type))
        except Exception:
            return "unsupported"
        if not result:
            return None
        return result.get("report_path")

    def list_reports(self) -> list:
        """列出已生成的报告。"""
        return _ddd_service.list_reports()

    def download_path(self, filename: str) -> Optional[str]:
        """获取报告下载路径。"""
        return _ddd_service.download(DownloadCommand(report_name=filename))

    def trash_report(self, filename: str) -> bool:
        """将报告移入回收站。"""
        try:
            _ddd_service.trash(TrashCommand(report_name=filename))
            return True
        except Exception:
            return False

    def list_trash(self) -> list:
        """列出回收站中的报告（返回文件名列表，维持既有契约）。"""
        result = _ddd_service.list_trash(TrashListQuery())
        return [item.get("name") for item in result.get("list", [])]

    def restore_report(self, filename: str) -> bool:
        """从回收站恢复报告。"""
        try:
            _ddd_service.restore(RestoreCommand(report_name=filename))
            return True
        except Exception:
            return False

    def purge_report(self, filename: str) -> bool:
        """从回收站彻底删除报告。"""
        try:
            _ddd_service.purge(PurgeCommand(report_name=filename))
            return True
        except Exception:
            return False


report_service = ReportService()
