"""模板聚合仓储接口（Repository Port）。"""
from __future__ import annotations

from typing import List, Optional, Protocol

from app.domain.template.domain.entities.template import Template


class TemplateRepository(Protocol):
    """模板聚合仓储契约。"""

    def list_templates(self, scope_type: str, scope_id: str,
                       scene: str = "") -> List[Template]: ...
    def get_template(self, template_id: str) -> Optional[Template]: ...
    def count_in_scope(self, scope_type: str, scope_id: str, scene: str) -> int: ...
    def upsert_template(self, template: Template) -> Optional[Template]: ...
    def delete_template(self, template_id: str) -> bool: ...
    def set_default(self, scope_type: str, scope_id: str, scene: str,
                    template_id: str) -> bool: ...
    def seed_default(self, scope_type: str, scope_id: str, scene: str,
                     name: str) -> Optional[Template]: ...


__all__ = ["TemplateRepository"]
