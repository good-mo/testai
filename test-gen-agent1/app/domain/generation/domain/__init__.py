"""生成编排领域层（domain layer）。

仅表达业务概念与规则（GenerationJob 聚合、步骤/修复循环不变量），
不依赖 FastAPI / sqlite / 具体存储实现。
"""
from app.domain.generation.domain.entities.fix_loop import FixLoop
from app.domain.generation.domain.entities.generation_job import GenerationJob
from app.domain.generation.domain.entities.generation_step import GenerationStep
from app.domain.generation.domain.repository import GenerationJobRepository
from app.domain.generation.domain.value_objects.generation_status import (
    GenerationStatus,
    GenerationStatusEnum,
)
from app.domain.generation.domain.value_objects.generation_test_type import (
    GenerationTestType,
    GenerationTestTypeEnum,
)
from app.domain.generation.domain.value_objects.job_source import JobSource

__all__ = [
    "FixLoop",
    "GenerationJob",
    "GenerationJobRepository",
    "GenerationStatus",
    "GenerationStatusEnum",
    "GenerationStep",
    "GenerationTestType",
    "GenerationTestTypeEnum",
    "JobSource",
]
