"""生成编排上下文值对象集。"""
from app.domain.generation.domain.value_objects.coverage_gate import CoverageGate
from app.domain.generation.domain.value_objects.generation_status import (
    GenerationStatus,
    GenerationStatusEnum,
)
from app.domain.generation.domain.value_objects.generation_test_type import (
    GenerationTestType,
    GenerationTestTypeEnum,
)
from app.domain.generation.domain.value_objects.job_source import VALID as JOB_SOURCES
from app.domain.generation.domain.value_objects.job_source import JobSource

__all__ = [
    "CoverageGate",
    "GenerationStatus",
    "GenerationStatusEnum",
    "GenerationTestType",
    "GenerationTestTypeEnum",
    "JobSource",
    "JOB_SOURCES",
]
