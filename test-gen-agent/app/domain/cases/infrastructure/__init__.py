"""用例上下文基础设施层。"""
from app.domain.cases.infrastructure.case_repository_impl import CaseRepository

CaseRepoAdapter = CaseRepository

__all__ = ["CaseRepoAdapter"]
