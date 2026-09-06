"""DDD 数据工厂域单测。

覆盖：
  1. 纯领域逻辑（无 DB）：类别守卫、模板不变量、字段生成策略、批次清理。
  2. 应用服务全链路（对接真实 DatafactoryRepo 存储）。
"""
import uuid

import pytest

from app.domain.common.exceptions import DomainValidationError
from app.domain.datafactory.application.datafactory_app_service import (
    datafactory_app_service,
)
from app.domain.datafactory.application.dto import (
    CleanupCommand,
    CreateTemplateCommand,
    GenerateCommand,
    TemplateListQuery,
    UpdateTemplateCommand,
)
from app.domain.datafactory.domain.value_objects.category import Category, CategoryEnum
from app.domain.datafactory.domain.value_objects.field_strategy import FieldStrategy
from app.domain.datafactory.domain.value_objects.template_status import TemplateStatus

TAG = "dddfac"  # 测试标识，便于清理


def _mk() -> str:
    return f"{TAG}_{uuid.uuid4().hex[:8]}"


def _template(**kw):
    from app.domain.datafactory.domain.entities.data_template import DataTemplate
    kw.setdefault("template_id", _mk())
    kw.setdefault("name", "模板")
    return DataTemplate(**kw)


# ═══════════════════════════════════════════════════════════
# 一、纯领域逻辑（无需数据库）
# ═══════════════════════════════════════════════════════════
class TestValueObjects:
    def test_category_normalize(self):
        assert str(Category("USER")) == "user"
        assert str(Category("")) == "custom"
        with pytest.raises(DomainValidationError):
            Category("unknown")

    def test_category_enum_valid(self):
        assert CategoryEnum.PRODUCT.value in {e.value for e in CategoryEnum}

    def test_field_strategy_guard(self):
        assert str(FieldStrategy("UUID")) == "uuid"
        with pytest.raises(DomainValidationError):
            FieldStrategy("magic")

    def test_template_status(self):
        assert TemplateStatus("Active").is_active
        assert not TemplateStatus("inactive").is_active


class TestAggregate:
    def test_name_required(self):
        with pytest.raises(DomainValidationError):
            _template(name="")

    def test_rename(self):
        t = _template()
        t.rename("新模板", "u")
        assert t.name == "新模板"

    def test_rename_empty_rejected(self):
        t = _template()
        with pytest.raises(DomainValidationError):
            t.rename("", "u")

    def test_illegal_schema_type(self):
        with pytest.raises(DomainValidationError):
            _template(schema=["not", "dict"])

    def test_illegal_strategy_in_schema(self):
        with pytest.raises(DomainValidationError):
            _template(schema={"f": {"strategy": "nope"}})

    def test_bare_value_normalized_to_fixed(self):
        t = _template(schema={"a": "hello"})
        assert t.schema["a"]["strategy"] == "fixed"

    def test_set_schema_and_status(self):
        t = _template()
        t.set_schema({"name": {"strategy": "sequence", "value": "u_{n}"}}, "u")
        assert "name" in t.schema
        t.set_status("inactive", "u")
        assert not t.is_active

    def test_delete_emits_event(self):
        t = _template()
        t.delete("u")
        names = [type(e).__name__ for e in t.pull_domain_events()]
        assert "DataTemplateDeleted" in names

    def test_created_emits_event(self):
        from app.domain.datafactory.domain.entities.data_template import DataTemplate
        t = DataTemplate(template_id=_mk(), name="x", _created=True)
        names = [type(e).__name__ for e in t.pull_domain_events()]
        assert "DataTemplateCreated" in names


class TestGenPolicy:
    def test_fixed(self):
        from app.domain.datafactory.domain.services.data_gen_policy import data_gen_policy
        assert data_gen_policy.generate_value({"strategy": "fixed", "value": "abc"}, 1, {}) == "abc"

    def test_sequence(self):
        from app.domain.datafactory.domain.services.data_gen_policy import data_gen_policy
        assert data_gen_policy.generate_value(
            {"strategy": "sequence", "value": "user_{n}"}, 3, {}) == "user_3"

    def test_uuid(self):
        from app.domain.datafactory.domain.services.data_gen_policy import data_gen_policy
        v = data_gen_policy.generate_value({"strategy": "uuid"}, 1, {})
        assert isinstance(v, str) and len(v) > 10

    def test_reference_from_registry(self):
        from app.domain.datafactory.domain.services.data_gen_policy import data_gen_policy
        assert data_gen_policy.generate_value(
            {"strategy": "reference", "ref": "用户模板.user_id"}, 1,
            {"用户模板.user_id": "u-1"}) == "u-1"


# ═══════════════════════════════════════════════════════════
# 二、应用服务全链路（真实存储）
# ═══════════════════════════════════════════════════════════
@pytest.fixture
def fresh_template_id():
    tmpl = datafactory_app_service.create_template(CreateTemplateCommand(
        name=_mk(), category="user", tags=["ddd"],
        schema_def={"username": {"strategy": "sequence", "value": "t{n}"}},
    ))
    tid = tmpl["id"]
    yield tid
    from app.repositories.datafactory_repo import DatafactoryRepo
    DatafactoryRepo.delete_template(tid)


def test_create_and_get(fresh_template_id):
    got = datafactory_app_service.get_template(fresh_template_id)
    assert got is not None
    assert got["status"] == "active"


def test_update(fresh_template_id):
    r = datafactory_app_service.update_template(UpdateTemplateCommand(
        template_id=fresh_template_id, name=_mk(), category="order", operator="admin"))
    assert r["name"].startswith(TAG)
    assert r["category"] == "order"


def test_list_templates(fresh_template_id):
    res = datafactory_app_service.list_templates(TemplateListQuery(limit=100))
    assert res["total"] >= 1


def test_delete_template(fresh_template_id):
    assert datafactory_app_service.delete_template(fresh_template_id, "admin")
    assert datafactory_app_service.get_template(fresh_template_id) is None


def test_generate_data(fresh_template_id):
    res = datafactory_app_service.generate(GenerateCommand(
        template_id=fresh_template_id, batch_size=3, env_key="test"))
    assert len(res["data"]) == 3
    assert res["data"][0]["username"].startswith("t")


def test_cleanup_batch(fresh_template_id):
    gen = datafactory_app_service.generate(GenerateCommand(
        template_id=fresh_template_id, batch_size=2, env_key="test"))
    bid = gen["id"]
    assert datafactory_app_service.cleanup_batch(CleanupCommand(batch_id=bid))
    assert datafactory_app_service.stats()["active_batches"] >= 0


def test_cleanup_by_env(fresh_template_id):
    datafactory_app_service.generate(GenerateCommand(
        template_id=fresh_template_id, batch_size=1, env_key="cleanup_env"))
    n = datafactory_app_service.cleanup_by_env("cleanup_env")
    assert n >= 1


def test_stats(fresh_template_id):
    st = datafactory_app_service.stats()
    assert "template_count" in st and "active_batches" in st
