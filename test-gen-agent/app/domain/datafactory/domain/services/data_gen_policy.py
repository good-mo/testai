"""数据生成策略领域服务。

把「按字段定义生成单个值」的算法建模为无状态领域服务，聚合与仓储复用，
避免生成逻辑散落。字段定义形如 {"strategy": ..., "value": ...}，见
value_objects.field_strategy。

本服务保持纯函数（除随机/时间等副作用的确定性可控），便于单测。
"""
from __future__ import annotations

import random
import time
import uuid
from typing import Any, Dict

from app.domain.common.exceptions import DomainValidationError
from app.domain.datafactory.domain.value_objects.field_strategy import FieldStrategy


class DataGenPolicy:
    """数据生成策略（无状态领域服务）。"""

    def generate_value(self, field_spec: Dict[str, Any], seq: int,
                       registry: Dict[str, Any]) -> Any:
        """依据字段定义生成一个值。

        :param field_spec: 字段定义字典（含 strategy/value/choices/min/max 等）
        :param seq:       当前记录序号（从 1 起），供 sequence 使用
        :param registry:  引用表（"模板名.字段名" -> 值），供 reference 使用
        """
        if not isinstance(field_spec, dict):
            return field_spec
        strategy = FieldStrategy(str(field_spec.get("strategy", "fixed")).lower())
        value = field_spec.get("value", "")
        s = strategy.value

        if s == "fixed":
            return value
        if s == "sequence":
            if isinstance(value, str) and "{n}" in value:
                return value.replace("{n}", str(seq))
            return f"{value}{seq}"
        if s == "uuid":
            return uuid.uuid4().hex
        if s == "random":
            choices = field_spec.get("choices") or []
            if choices:
                return random.choice(list(choices))
            low = int(field_spec.get("min", 0))
            high = int(field_spec.get("max", 1000))
            return random.randint(low, high)
        if s == "timestamp":
            fmt = field_spec.get("format", "%Y-%m-%d %H:%M:%S")
            return time.strftime(fmt, time.localtime(time.time() + seq))
        if s == "reference":
            ref_key = field_spec.get("ref", "")
            if ref_key in registry:
                return registry[ref_key]
            return None
        raise DomainValidationError(f"不支持的字段生成策略 '{s}'")

    def generate_batch(self, schema: Dict[str, Any], batch_size: int,
                       dep_data: Dict[str, Any]) -> list:
        """按 schema 生成 batch_size 条记录。schema 非空校验与依赖注入在外部做。"""
        items = []
        for i in range(batch_size):
            item: Dict[str, Any] = {}
            registry = dict(dep_data or {})
            for field, spec in (schema or {}).items():
                item[field] = self.generate_value(spec, i + 1, registry)
            items.append(item)
        return items

    @staticmethod
    def resolve_dep_schema(dep_name: str, dep_schema: Dict[str, Any],
                           generator: "DataGenPolicy") -> Dict[str, Any]:
        """将某个依赖模板字段表展平为引用注册表。

        每个依赖模板取首条引用字段快照，供当前模板 reference 策略使用。
        """
        registry: Dict[str, Any] = {}
        seq = 1
        for field, spec in (dep_schema or {}).items():
            if isinstance(spec, dict):
                registry[f"{dep_name}.{field}"] = generator.generate_value(
                    spec, seq, {})
            else:
                registry[f"{dep_name}.{field}"] = spec
        return registry


# 无状态单例（进程内复用）
data_gen_policy = DataGenPolicy()

__all__ = ["DataGenPolicy", "data_gen_policy"]
