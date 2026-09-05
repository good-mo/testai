"""项目编程语言值对象。

限定项目声明的主语言范围，避免脏数据落入 projects.language。
"""
from __future__ import annotations

from enum import Enum

from app.domain.common.exceptions import DomainValidationError
from app.domain.common.value_objects import ValueObject


class ProjectLanguageEnum(str, Enum):
    PYTHON = "python"
    JAVA = "java"
    GO = "go"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    PHP = "php"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    RUBY = "ruby"
    SCALA = "scala"
    SHELL = "shell"
    SQL = "sql"
    OTHER = "other"


class ProjectLanguage(ValueObject):
    """项目主语言（不可变值对象）。"""

    def __init__(self, value):
        if isinstance(value, ProjectLanguageEnum):
            v = value
        else:
            raw = str(value or "").strip().lower()
            if raw in ("", "none"):
                raw = ProjectLanguageEnum.PYTHON.value
            try:
                v = ProjectLanguageEnum(raw)
            except ValueError:
                v = ProjectLanguageEnum.OTHER
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ProjectLanguage):
            return self.value is other.value
        if isinstance(other, str):
            return self.value.value == other
        return NotImplemented
