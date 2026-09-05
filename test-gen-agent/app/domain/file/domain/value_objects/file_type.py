"""文件类型与文件元数据值对象。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class FileTypeEnum(str, Enum):
    IMAGE = "IMAGE"
    DOC = "DOC"
    XLS = "XLS"
    JAR = "JAR"
    CONFIG = "CONFIG"
    FILE = "FILE"


@dataclass(frozen=True)
class FileType(ValueObject):
    """文件类型值对象。"""

    value: str

    def __post_init__(self) -> None:
        v = str(self.value).upper()
        try:
            FileTypeEnum(v)
        except ValueError:
            raise DomainValidationError(
                f"非法文件类型 '{self.value}'，仅支持 {[e.value for e in FileTypeEnum]}"
            )
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class FileName(ValueObject):
    """净化后的安全文件名（阻断路径穿越）。"""

    value: str

    def __post_init__(self) -> None:
        import re
        name = str(self.value or "").strip()
        if not name:
            object.__setattr__(self, "value", "unnamed")
            return
        # 净化：只取 basename → 去非法字符 → 去首尾空白
        name = name.replace("\\", "/").split("/")[-1]
        name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name)
        if name.split(".")[0].upper() in {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }:
            name = f"_{name}"
        name = name.strip(" .\u3000")[:200].strip(" .")
        object.__setattr__(self, "value", name or "unnamed")

    def __str__(self) -> str:
        return self.value


__all__ = ["FileType", "FileTypeEnum", "FileName"]
