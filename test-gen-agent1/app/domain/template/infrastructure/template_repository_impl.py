"""模板聚合仓储实现（Adapter / Anti-Corruption Layer）。

将既有 TemplateRepo（四层 Repository）封装为面向聚合 Template 的仓储，
复用已验证的模板持久化逻辑。
"""
from __future__ import annotations

import json
from typing import List, Optional

from app.domain.template.domain.entities.template import Template
from app.repositories.template_repo import TemplateRepo


class TemplateRepoAdapter:
    """将既有 TemplateRepo 封装为面向聚合 Template 的仓储。"""

    # ── 读 ─────────────────────────────────────────────
    def list_templates(self, scope_type: str, scope_id: str,
                       scene: str = "") -> List[Template]:
        rows = TemplateRepo.list_templates(scope_type, scope_id, scene)
        templates = []
        for row in rows:
            d = dict(row)
            for k in ("custom_fields", "system_fields", "upload_img_file_ids"):
                if isinstance(d.get(k), str):
                    try:
                        d[k] = json.loads(d[k])
                    except (json.JSONDecodeError, TypeError):
                        d[k] = []
            d["scope_type"] = scope_type
            templates.append(Template.from_dict(d))
        return templates

    def get_template(self, template_id: str) -> Optional[Template]:
        row = TemplateRepo.get_template(template_id)
        if not row:
            return None
        d = dict(row)
        for k in ("custom_fields", "system_fields", "upload_img_file_ids"):
            if isinstance(d.get(k), str):
                try:
                    d[k] = json.loads(d[k])
                except (json.JSONDecodeError, TypeError):
                    d[k] = []
        return Template.from_dict(d)

    def count_in_scope(self, scope_type: str, scope_id: str,
                       scene: str) -> int:
        return TemplateRepo.count_in_scope(scope_type, scope_id, scene)

    # ── 写 ─────────────────────────────────────────────
    def upsert_template(self, template: Template) -> Optional[Template]:
        body = template.to_dict()
        # 平台默认标记：聚合侧用 platformDefault，四层仓库读 enablePlatformDefault，
        # 这里补一个别名键，保证 DDD 写路径与旧语义一致地持久化该标记。
        if "platformDefault" in body and "enablePlatformDefault" not in body:
            body["enablePlatformDefault"] = body["platformDefault"]
        row = TemplateRepo.upsert_template(
            str(template.id.value), body, template.scope_type.value
        )
        if not row:
            return None
        d = dict(row)
        # 反序列化 DB 中的 JSON 文本字段，保证 from_dict 能构造聚合（与读路径一致）
        for k in ("custom_fields", "system_fields", "upload_img_file_ids"):
            if isinstance(d.get(k), str):
                try:
                    d[k] = json.loads(d[k])
                except (json.JSONDecodeError, TypeError):
                    d[k] = []
        return Template.from_dict(d)

    def delete_template(self, template_id: str) -> bool:
        return TemplateRepo.delete_template(template_id)

    def set_default(self, scope_type: str, scope_id: str, scene: str,
                    template_id: str) -> bool:
        return TemplateRepo.set_default(scope_type, scope_id, scene, template_id)

    def seed_default(self, scope_type: str, scope_id: str, scene: str,
                     name: str) -> Optional[Template]:
        row = TemplateRepo.seed_default(scope_type, scope_id, scene, name)
        if not row:
            return None
        d = dict(row)
        for k in ("custom_fields", "system_fields", "upload_img_file_ids"):
            if isinstance(d.get(k), str):
                try:
                    d[k] = json.loads(d[k])
                except (json.JSONDecodeError, TypeError):
                    d[k] = []
        d["scope_type"] = scope_type
        return Template.from_dict(d)


__all__ = ["TemplateRepoAdapter"]
