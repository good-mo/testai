"""时间单位换算的语义化常量与工具（防腐：领域层不得裸写魔数 * 1000）。

约定
----
- 聚合内部与数据库列存 **秒**（epoch seconds, float/REAL）；
- 对外视图 / to_dict() 采用 **毫秒**（camelCase，如 createTime），便于前端展示；
- from_dict() 需兼容两种输入来源：
    · DB 原始行：snake_case 秒（如 create_time / created_at），原样使用；
    · to_dict() 回灌或已转 camelCase 的仓库行（如 createTime，毫秒），需除以 1000。
  否则「读聚合 → 改字段 → 存回」一次往返会把毫秒当秒回灌，时间被放大 1000 倍。

背景
----
历史上一批聚合根的 ``to_dict()`` 直接裸写 ``int(self._create_time * 1000)``
做 秒→毫秒 换算，而其 ``from_dict()`` 却把毫秒当秒回灌，导致「读→改→存」
后创建时间被放大 1000 倍。为杜绝这类魔数扩散，统一收敛到带语义的常量，
并由架构守护（architecture_guard）禁止聚合根再裸写 ``* 1000``。

使用
----
.. code-block:: python

    from app.domain.common.time_utils import MS_PER_SECOND, time_from_row

    def to_dict(self):
        return {"createTime": int(self._create_time * MS_PER_SECOND)}
"""
from __future__ import annotations

from typing import Optional

# 1 秒 = 1000 毫秒。用带语义的常量替代裸魔数，便于审查与统一演进。
MS_PER_SECOND = 1000


def seconds_to_ms(value: float) -> int:
    """把以「秒」为单位的 epoch 时间换算成「毫秒」，供持久化/序列化导出。"""
    return int(value * MS_PER_SECOND)


def time_from_row(data: dict, snake_key: str, camel_key: str,
                  default: Optional[float] = None) -> Optional[float]:
    """从行字典解析一个时间字段为**秒**。

    snake_key 命中说明来自 DB 原始行（秒），直接采用；
    否则取 camel_key（毫秒）并换算回秒。均缺失返回 default。
    """
    if snake_key in data and data.get(snake_key) is not None:
        return data[snake_key]
    raw = data.get(camel_key)
    if raw is None:
        return default
    try:
        return float(raw) / 1000.0
    except (TypeError, ValueError):
        return default


__all__ = ["MS_PER_SECOND", "seconds_to_ms", "time_from_row"]
