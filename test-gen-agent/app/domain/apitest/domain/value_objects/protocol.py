"""接口协议值对象。"""
from __future__ import annotations

from enum import Enum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class ProtocolEnum(str, Enum):
    HTTP = "HTTP"
    HTTPS = "HTTPS"
    TCP = "TCP"
    SQL = "SQL"
    DUBBO = "DUBBO"


class Protocol(ValueObject):
    """接口协议值对象（HTTP/TCP/SQL/DUBBO 等）。"""

    value: ProtocolEnum

    def __init__(self, value):
        if isinstance(value, ProtocolEnum):
            v = value
        else:
            raw = str(value).upper()
            # 兼容不带协议的入参（如空串）
            if not raw:
                raw = ProtocolEnum.HTTP.value
            try:
                v = ProtocolEnum(raw)
            except ValueError:
                raise DomainValidationError(
                    f"非法协议 '{value}'，支持 {[e.value for e in ProtocolEnum]}"
                )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value.value
