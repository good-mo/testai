"""脚本聚合根 Script（UI 测试脚本健康度）。

聚合边界：
  - Script（聚合根）：脚本元数据 + 健康度
  - 定位器列表（locators）为聚合内子值对象
  - 执行记录（execution history）为关联记录（由仓储管理）
"""
from __future__ import annotations

import time
from typing import List, Optional

from app.domain.common.entities import AggregateRoot, Identifier
from app.domain.common.exceptions import DomainValidationError
from app.domain.script.domain.events import (
    ScriptAutoRepaired,
    ScriptDeleted,
    ScriptExecutionRecorded,
    ScriptRegistered,
    ScriptUpdated,
)
from app.domain.script.domain.services.script_policy import (
    calc_health_score,
    determine_status,
)
from app.domain.script.domain.value_objects.script_status import ScriptFramework, ScriptStatus


class Script(AggregateRoot):
    """脚本健康度聚合根。"""

    def __init__(
        self,
        *,
        script_id: str,
        name: str,
        file_path: str = "",
        framework: str = "pytest",
        description: str = "",
        locators: Optional[list] = None,
        total_runs: int = 0,
        success_runs: int = 0,
        fail_runs: int = 0,
        last_run_at: Optional[float] = None,
        last_status: str = "",
        health_score: float = 100.0,
        status: str = "healthy",
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        _registered: bool = False,
    ):
        if not script_id:
            raise DomainValidationError("脚本 ID 不能为空")
        if not (name or "").strip():
            raise DomainValidationError("脚本名称不能为空")
        self.id = Identifier.of(script_id)
        self._name = (name or "").strip()
        self._file_path = file_path or ""
        self._framework = ScriptFramework(framework)
        self._description = description or ""
        self._locators = [dict(x) for x in (locators or [])]
        self._total_runs = max(0, int(total_runs or 0))
        self._success_runs = max(0, int(success_runs or 0))
        self._fail_runs = max(0, int(fail_runs or 0))
        self._last_run_at = last_run_at
        self._last_status = last_status or ""
        self._health_score = float(health_score or 100.0)
        self._status = ScriptStatus(status)
        self._created_at = created_at if created_at is not None else time.time()
        self._updated_at = updated_at if updated_at is not None else self._created_at
        self._domain_events = []
        self.version = 0
        if _registered:
            self.record_event(ScriptRegistered(
                self.id.value, self._name, self._framework.value))

    # ── 只读属性 ─────────────────────────────────────
    @property
    def name(self) -> str:
        return self._name

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def framework(self) -> ScriptFramework:
        return self._framework

    @property
    def description(self) -> str:
        return self._description

    @property
    def locators(self) -> List[dict]:
        return [dict(x) for x in self._locators]

    @property
    def total_runs(self) -> int:
        return self._total_runs

    @property
    def success_runs(self) -> int:
        return self._success_runs

    @property
    def fail_runs(self) -> int:
        return self._fail_runs

    @property
    def last_run_at(self) -> Optional[float]:
        return self._last_run_at

    @property
    def last_status(self) -> str:
        return self._last_status

    @property
    def health_score(self) -> float:
        return self._health_score

    @property
    def status(self) -> ScriptStatus:
        return self._status

    @property
    def created_at(self) -> float:
        return self._created_at

    @property
    def updated_at(self) -> float:
        return self._updated_at

    # ── 业务命令 ─────────────────────────────────────
    def update_meta(self, **kwargs) -> None:
        """更新脚本元数据。"""
        if "name" in kwargs:
            if not (kwargs.get("name") or "").strip():
                raise DomainValidationError("脚本名称不能为空")
            self._name = kwargs["name"].strip()
        if "file_path" in kwargs:
            self._file_path = kwargs["file_path"] or ""
        if "framework" in kwargs:
            self._framework = ScriptFramework(kwargs["framework"])
        if "description" in kwargs:
            self._description = kwargs["description"] or ""
        if "locators" in kwargs:
            self._locators = [dict(x) for x in (kwargs["locators"] or [])]
        self._touch()
        self.record_event(ScriptUpdated(self.id.value, "meta"))

    def mark_deleted(self) -> None:
        self.record_event(ScriptDeleted(self.id.value))

    def record_execution(self, success: bool = True, duration: float = 0,
                         error_type: str = "", error_message: str = "",
                         locator_failures: Optional[list] = None) -> float:
        """记录一次脚本执行，更新健康度。

        Returns:
            新的健康度评分。
        """
        self._total_runs += 1
        if success:
            self._success_runs += 1
        else:
            self._fail_runs += 1
        self._last_run_at = time.time()
        self._last_status = "success" if success else "failed"
        self._health_score = calc_health_score(
            self._total_runs, self._success_runs, self._fail_runs,
            self._health_score, success,
        )
        self._status = ScriptStatus(determine_status(self._health_score))
        self._touch()
        self.record_event(ScriptExecutionRecorded(
            self.id.value, success, self._health_score, self._status.value))

        # 定位器失败时自动修复
        if locator_failures:
            for failure in locator_failures:
                self._auto_repair(failure.get("name", ""))
        return self._health_score

    def auto_repair(self, locator_name: str, repaired: bool = False,
                    new_strategy: str = "", new_selector: str = "") -> bool:
        """尝试修复定位器。

        Args:
            locator_name: 定位器名称
            repaired: 是否修复成功（由外部策略判断后调用）
            new_strategy: 新策略（如 data-testid）
            new_selector: 新选择器

        Returns:
            True 表示修复成功。
        """
        if not repaired:
            return False
        for loc in self._locators:
            if loc.get("name") == locator_name:
                loc["current_strategy"] = new_strategy or loc.get("current_strategy", "")
                loc["current_selector"] = new_selector or loc.get("current_selector", "")
                loc["status"] = "repaired"
                loc["updated_at"] = time.time()
                self._touch()
                self.record_event(ScriptAutoRepaired(
                    self.id.value, locator_name, new_strategy))
                return True
        return False

    def _auto_repair(self, locator_name: str) -> None:
        """尝试自动修复一个失效定位器（使用推荐策略）。"""
        # 实际修复逻辑在 domain policy 与 infra 协作，此处标记
        pass

    def _touch(self) -> None:
        self._updated_at = time.time()

    # ── 序列化 ─────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id": self.id.value,
            "name": self._name,
            "file_path": self._file_path,
            "framework": self._framework.value,
            "description": self._description,
            "locators": self._locators,
            "total_runs": self._total_runs,
            "success_runs": self._success_runs,
            "fail_runs": self._fail_runs,
            "last_run_at": self._last_run_at,
            "last_status": self._last_status,
            "health_score": self._health_score,
            "status": self._status.value,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Script":
        return Script(
            script_id=str(data.get("id") or data.get("script_id") or ""),
            name=data.get("name", ""),
            file_path=data.get("file_path", ""),
            framework=data.get("framework", "pytest"),
            description=data.get("description", ""),
            locators=data.get("locators"),
            total_runs=data.get("total_runs", 0),
            success_runs=data.get("success_runs", 0),
            fail_runs=data.get("fail_runs", 0),
            last_run_at=data.get("last_run_at"),
            last_status=data.get("last_status", ""),
            health_score=data.get("health_score", 100.0),
            status=data.get("status", "healthy"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


__all__ = ["Script"]
