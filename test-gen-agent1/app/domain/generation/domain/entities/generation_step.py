"""生成流程步骤实体（GenerationStep）。

GenerationStep 是 GenerationJob 聚合内的子实体：表达一次 LangGraph 节点
（scan_code / generate_mocks / generate_tests / test_runner /
refinement_node / coverage_analysis / performance_test）的执行记录。

无独立仓储，随聚合一起存取，守护"单次步骤执行"的完整性。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from app.domain.common.exceptions import DomainValidationError


class StepState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class GenerationStep:
    """单个生成步骤执行记录（聚合内子实体）。

    非不可变：随执行推进由聚合根更新其状态。
    """

    node_name: str
    status: StepState = StepState.PENDING
    seq: int = 0
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    error: str = ""
    detail: Any = None

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            try:
                self.status = StepState(self.status.lower())
            except ValueError:
                raise DomainValidationError(
                    f"非法步骤状态 '{self.status}'，支持 {[s.value for s in StepState]}"
                )

    @property
    def duration(self) -> Optional[float]:
        if self.started_at is None or self.ended_at is None:
            return None
        return round(self.ended_at - self.started_at, 3)

    def mark_running(self) -> None:
        self.status = StepState.RUNNING
        self.started_at = self.started_at if self.started_at is not None else time.time()

    def mark_done(self, detail: Any = None) -> None:
        self.status = StepState.DONE
        self.detail = detail
        self.ended_at = time.time()

    def mark_failed(self, error: str = "") -> None:
        self.status = StepState.FAILED
        self.error = error or ""
        self.ended_at = time.time()

    def to_dict(self) -> dict:
        return {
            "node_name": self.node_name,
            "status": self.status.value,
            "seq": self.seq,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration": self.duration,
            "error": self.error,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GenerationStep":
        return cls(
            node_name=str(data.get("node_name", "")),
            status=data.get("status", "pending"),
            seq=int(data.get("seq") or 0),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            error=data.get("error", ""),
            detail=data.get("detail"),
        )


__all__ = ["GenerationStep", "StepState"]
