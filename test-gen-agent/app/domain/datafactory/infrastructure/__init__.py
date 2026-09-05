"""数据工厂上下文基础设施层：对接既有四层存储实现（DatafactoryRepo）。"""
from app.domain.datafactory.infrastructure.datafactory_repository_impl import (
    DataFactoryRepoAdapter,
    datafactory_repository,
)

__all__ = ["DataFactoryRepoAdapter", "datafactory_repository"]
