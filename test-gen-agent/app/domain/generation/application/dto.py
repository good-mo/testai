"""生成编排应用层输入/输出 DTO。

面向聚合操作接收显式 DTO（而非裸 dict），与 Web 层的 Pydantic
请求体解耦。此处用 dataclass 表达简单命令，保持零框架依赖。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """测试生成接口请求。"""

    source_code: str = Field("", description="源代码")
    file_path: str = Field("", description="源文件路径")
    test_type: str = Field("functional", description="测试类型")
    generate_script: bool = Field(True, description="是否生成脚本")

    model_config = {"extra": "allow"}


@dataclass
class CreateGenerationCommand:
    """创建并提交一次测试生成任务。"""

    file_path: str
    source_code: str = ""
    test_type: str = "functional"
    generate_script: bool = True
    source: str = "single"
    metadata: Optional[dict] = None
    operator: str = "system"


@dataclass
class UpdateArtifactsCommand:
    """提交生成产物（测试代码 / 运行结果 / 覆盖率 / 性能报告）。"""

    job_id: str
    generated_tests: Optional[str] = None
    test_result: Optional[dict] = None
    coverage_report: Optional[dict] = None
    performance_report: Optional[dict] = None
    saved_to: Optional[str] = None
    error: Optional[str] = None
    operator: str = "system"


@dataclass
class RecordStepCommand:
    """登记一次流程步骤执行结果。"""

    job_id: str
    node_name: str
    status: str = "done"
    error: str = ""
    detail: Any = None
    operator: str = "system"


@dataclass
class RetryCommand:
    """触发一次修复重试。"""

    job_id: str
    test_result: Optional[dict] = None
    diagnosis: str = ""
    reason: str = ""
    operator: str = "system"


@dataclass
class FinalizeCommand:
    """收口任务（成功/失败）。"""

    job_id: str
    outcome: str = "succeeded"          # succeeded / failed
    generated_tests: str = ""
    reason: str = ""
    operator: str = "system"


@dataclass
class CancelCommand:
    """取消任务。"""

    job_id: str
    operator: str = "system"


@dataclass
class JobListQuery:
    """生成任务列表查询。"""

    file_path: str = ""
    source: str = ""
    passed: Optional[bool] = None
    status: str = ""
    search: str = ""
    limit: int = 50
    offset: int = 0


@dataclass
class JobStats:
    """生成任务统计输出。"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    by_source: Dict[str, int] = field(default_factory=dict)
    avg_coverage: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "by_source": dict(self.by_source),
            "avg_coverage": self.avg_coverage,
        }


__all__ = [
    "ChatRequest",
    "CreateGenerationCommand",
    "UpdateArtifactsCommand",
    "RecordStepCommand",
    "RetryCommand",
    "FinalizeCommand",
    "CancelCommand",
    "JobListQuery",
    "JobStats",
]
