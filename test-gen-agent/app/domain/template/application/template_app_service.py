"""模板应用服务（Application Service / Use Case 门面）。

修复说明：
  - 修改 import：从 TemplateRepoAdapter 改为 TemplateRepositoryImpl
  - 使用模块级单例 template_repository
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.domain.common.domain_events import event_bus
from app.domain.template.application.dto import (
    DeleteTemplateCommand,
    GetTemplateCommand,
    ListTemplatesCommand,
    SaveTemplateCommand,
    SetDefaultCommand,
)
from app.domain.template.domain.entities.template import Template

# ── 修复：改 import ──────────────────────────────────────────
from app.domain.template.infrastructure.template_repository_impl import (
    TemplateRepositoryImpl,
    template_repository,
)

# 默认模板名称（范围内无模板时播种）
DEFAULT_NAMES = {
    "FUNCTIONAL": "功能用例默认模板",
    "API": "接口默认模板",
    "UI": "UI 默认模板",
    "TEST_PLAN": "测试计划默认模板",
    "BUG": "缺陷默认模板",
}


class TemplateAppService:
    """模板用例编排服务。"""

    def __init__(self, repo=None):
        # ── 修复：使用新的 Repository 单例 ──────────────────
        self._repo = repo or template_repository

    def list_templates(self, cmd: ListTemplatesCommand) -> List[dict]:
        """列出指定作用域下的模板；空时自动播种默认模板。"""
        scene = cmd.scene or "FUNCTIONAL"
        templates = self._repo.list_templates(cmd.scope_type, cmd.scope_id, scene)
        if not templates:
            seeded = self._repo.seed_default(
                cmd.scope_type, cmd.scope_id, scene,
                DEFAULT_NAMES.get(scene, "默认模板"),
            )
            if seeded:
                templates = [seeded]
        return [t.to_dict() for t in templates]

    def get_template(self, cmd: GetTemplateCommand) -> Optional[dict]:
        t = self._repo.get_template(cmd.template_id)
        return t.to_dict() if t else None

    def save_template(self, cmd: SaveTemplateCommand) -> Optional[dict]:
        """新增或更新模板。新增时首条自动设为默认。"""
        template_id = cmd.template_id or str(uuid.uuid4())
        name = cmd.name.strip() or "未命名模板"

        # 检查是否新增（判断范围首条）
        is_new = self._repo.get_template(template_id) is None

        t = Template(
            template_id=template_id,
            name=name,
            remark=cmd.remark,
            scene=cmd.scene,
            scope_type=cmd.scope_type,
            scope_id=cmd.scope_id,
            internal=cmd.internal,
            enable_default=cmd.enable_default,
            enable_third_part=cmd.enable_third_part,
            ref_id=cmd.ref_id,
            platform_default=cmd.platform_default,
            custom_fields=cmd.custom_fields,
            system_fields=cmd.system_fields,
            upload_img_file_ids=cmd.upload_img_file_ids,
            create_user=cmd.create_user,
            update_user=cmd.update_user,
        )

        saved = self._repo.upsert_template(t)
        if not saved:
            return None

        # 首条模板自动设为默认
        if is_new and self._repo.count_in_scope(
            cmd.scope_type, cmd.scope_id, cmd.scene or "FUNCTIONAL"
        ) == 1:
            self._repo.set_default(
                cmd.scope_type, cmd.scope_id, cmd.scene or "FUNCTIONAL",
                str(template_id),
            )
            saved._enable_default = True

        self._publish(t)
        return saved.to_dict()

    def delete_template(self, cmd: DeleteTemplateCommand) -> bool:
        t = self._repo.get_template(cmd.template_id)
        if t:
            t.mark_deleted(cmd.template_id)
            self._publish(t)
        return self._repo.delete_template(cmd.template_id)

    def set_default(self, cmd: SetDefaultCommand) -> bool:
        ok = self._repo.set_default(
            cmd.scope_type, cmd.scope_id, cmd.scene, cmd.template_id
        )
        if ok:
            t = self._repo.get_template(cmd.template_id)
            if t:
                t.set_default()
                self._publish(t)
        return ok

    # ── 便捷方法（供路由直接调用，避免构造 Command）─────────
    def add_template(self, scope_type: str, body: dict) -> Optional[dict]:
        """新增模板（兼容旧接口）。"""
        cmd = self._body_to_command(scope_type, body)
        return self.save_template(cmd)

    def update_template(self, scope_type: str, template_id: str, body: dict) -> Optional[dict]:
        """更新模板（兼容旧接口）。"""
        cmd = self._body_to_command(scope_type, body, template_id=template_id)
        return self.save_template(cmd)

    def get_template_by_id(self, scope_type: str, template_id: str) -> Optional[dict]:
        """按 ID 获取模板（兼容旧接口）。"""
        return self.get_template(GetTemplateCommand(scope_type=scope_type, template_id=template_id))

    def list_templates_raw(self, scope_type: str, scope_id: str, scene: str = "") -> List[dict]:
        """列出模板（兼容旧接口）。"""
        return self.list_templates(ListTemplatesCommand(scope_type=scope_type, scope_id=scope_id, scene=scene or "FUNCTIONAL"))

    def delete_template_by_id(self, template_id: str) -> bool:
        """按 ID 删除模板（兼容旧接口）。"""
        return self.delete_template(DeleteTemplateCommand(template_id=template_id))

    def set_default_raw(self, scope_type: str, scope_id: str, scene: str, template_id: str) -> bool:
        """设为默认（兼容旧接口）。"""
        return self.set_default(SetDefaultCommand(scope_type=scope_type, scope_id=scope_id, scene=scene, template_id=template_id))

    @staticmethod
    def _body_to_command(scope_type: str, body: dict,
                         template_id: Optional[str] = None) -> SaveTemplateCommand:
        """把前端 body 翻译为 SaveTemplateCommand。"""
        import json as _json

        def _str(v, default: str = "") -> str:
            return v if isinstance(v, str) else default

        def _bool(v) -> bool:
            if isinstance(v, bool):
                return v
            return bool(v)

        def _loads(raw, default=None):
            if raw is None:
                return list(default) if default is not None else []
            if isinstance(raw, (list, tuple)):
                return list(raw)
            if isinstance(raw, str):
                try:
                    return _json.loads(raw)
                except Exception:
                    return []
            return []

        scope_id = body.get("scopeId") or body.get("scope_id") or ""
        return SaveTemplateCommand(
            scope_type=scope_type,
            template_id=template_id or body.get("id"),
            name=_str(body.get("name", ""), ""),
            remark=_str(body.get("remark", "")),
            scene=_str(body.get("scene", ""), "FUNCTIONAL") or "FUNCTIONAL",
            scope_id=_str(scope_id, ""),
            internal=_bool(body.get("internal", False)),
            enable_default=_bool(body.get("enableDefault", body.get("enable_default", False))),
            enable_third_part=_bool(body.get("enableThirdPart", body.get("enable_third_part", False))),
            platform_default=_bool(body.get("enablePlatformDefault", body.get("platform_default", False))),
            ref_id=_str(body.get("refId") or body.get("ref_id") or ""),
            custom_fields=_loads(body.get("customFields", body.get("custom_fields"))),
            system_fields=_loads(body.get("systemFields", body.get("system_fields"))),
            upload_img_file_ids=_loads(body.get("uploadImgFileIds", body.get("upload_img_file_ids"))),
            create_user=_str(body.get("createUser") or body.get("create_user") or "admin"),
            update_user=_str(body.get("updateUser") or body.get("update_user") or "admin"),
        )

    # ── 内部助手 ───────────────────────────────────
    @staticmethod
    def _publish(template: Template) -> None:
        for ev in template.pull_domain_events():
            event_bus.dispatch(ev)


# 单例门面
template_app_service = TemplateAppService()

__all__ = ["TemplateAppService", "template_app_service"]
