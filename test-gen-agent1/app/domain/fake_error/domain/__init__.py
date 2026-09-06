"""误报规则领域层。"""
from app.domain.fake_error.domain.entities.error_rule import FakeErrorRule
from app.domain.fake_error.domain.repository import FakeErrorRepository

__all__ = ["FakeErrorRule", "FakeErrorRepository"]
