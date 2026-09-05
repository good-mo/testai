"""误报规则（错误注入）限界上下文。

聚合根：`FakeErrorRule`（误报规则/错误注入规则）
对应现有：`services/fake_error_service.py` `repositories/fake_error_repo.py`
"""
from app.domain.fake_error.application.fake_error_app_service import (
    FakeErrorAppService,
    fake_error_app_service,
)
from app.domain.fake_error.domain.entities.error_rule import FakeErrorRule

__all__ = ["FakeErrorAppService", "fake_error_app_service", "FakeErrorRule"]
