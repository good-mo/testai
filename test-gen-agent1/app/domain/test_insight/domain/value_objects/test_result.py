"""测试执行结果值对象。

描述一次测试执行的总体结果，作为执行追溯(TraceRun)的守卫核心：
`passed` / `failed` / `error` / `unknown`，并提供向"通过率/权重"等
派生指标转换的能力。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Set

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class TestResultEnum(str, Enum):
    UNKNOWN = "unknown"   # 未知/未跑
    PASSED = "passed"     # 全部通过
    FAILED = "failed"     # 存在断言失败
    ERROR = "error"       # 执行报错（环境/异常中止）

    @property
    def label(self) -> str:
        return {
            TestResultEnum.UNKNOWN: "未知",
            TestResultEnum.PASSED: "通过",
            TestResultEnum.FAILED: "失败",
            TestResultEnum.ERROR: "报错",
        }[self]


VALID: Set[str] = {e.value for e in TestResultEnum}


@dataclass(frozen=True)
class TestResult(ValueObject):
    """测试执行结果值对象（带归一化与派生权重）。"""

    value: str

    def __post_init__(self) -> None:
        raw = self.value.value if isinstance(self.value, TestResultEnum) else self.value
        v = str(raw).strip().lower()
        if v not in VALID:
            raise DomainValidationError(
                f"非法测试结果 '{self.value}'，仅支持 {sorted(VALID)}"
            )
        object.__setattr__(self, "value", v)

    @property
    def enum(self) -> TestResultEnum:
        return TestResultEnum(self.value)

    @property
    def is_passed(self) -> bool:
        return self.value == TestResultEnum.PASSED.value

    @property
    def is_defective(self) -> bool:
        """是否代表一次"未通过"（失败或报错）的执行。"""
        return self.value in (TestResultEnum.FAILED.value, TestResultEnum.ERROR.value)

    def __str__(self) -> str:
        return self.value


# 预置常量，便于领域层直接引用
TEST_RESULT_UNKNOWN = TestResult(TestResultEnum.UNKNOWN)
TEST_RESULT_PASSED = TestResult(TestResultEnum.PASSED)
TEST_RESULT_FAILED = TestResult(TestResultEnum.FAILED)
TEST_RESULT_ERROR = TestResult(TestResultEnum.ERROR)
