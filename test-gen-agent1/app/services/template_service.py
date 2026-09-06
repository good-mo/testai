# app/services/template_service.py
"""模板业务逻辑层（template 域 DDD 接入 · 阶段 C 薄门面）。

业务规则（默认模板播种、首条自动默认、字段结构）已下沉到 template 域领域层
`app/domain/template/`。本 Service 收敛为对 DDD 应用服务 `template_app_service`
的薄委托门面，仅保留既有方法签名以兼容 project_compat_extra / system_compat_extra
等调用方。返回结构与重构前一致（DDD 聚合 to_dict 采用前端模板契约）。

> 推荐调用方直接使用 `template_app_service`；本类仅作过渡兼容层保留。
"""
from __future__ import annotations

import json
from typing import List, Optional

from app.domain.template.application.dto import (
    DeleteTemplateCommand,
    GetTemplateCommand,
    ListTemplatesCommand,
    SaveTemplateCommand,
    SetDefaultCommand,
)
from app.domain.template.application.template_app_service import (
    template_app_service as _ddd,
)


def _str(v, default: str = "") -> str:
    return v if isinstance(v, str) else default


def _bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return bool(v)


def _loads(raw, default=None):
    """兼容前端可能以 JSON 字符串传入的数组字段。"""
    if raw is None:
        return list(default) if default is not None else []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return []
    return []


class TemplateService:
    """模板服务（template 域 DDD 薄门面，返回前端可直接消费的结构）。"""

    DEFAULT_NAMES = {
        "FUNCTIONAL": "功能用例默认模板",
        "API": "接口默认模板",
        "UI": "UI 默认模板",
        "TEST_PLAN": "测试计划默认模板",
        "BUG": "缺陷默认模板",
    }

    @staticmethod
    def _body_to_command(scope_type: str, body: dict,
                         template_id: Optional[str] = None) -> SaveTemplateCommand:
        """把前端 ActionTemplateManage body 翻译为 DDD SaveTemplateCommand。"""
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

    def list_templates(self, scope_type: str, scope_id: str, scene: str = "") -> List[dict]:
        return _ddd.list_templates(ListTemplatesCommand(
            scope_type=scope_type, scope_id=scope_id, scene=scene or "FUNCTIONAL",
        ))

    def get_template(self, scope_type: str, template_id: str) -> Optional[dict]:
        return _ddd.get_template(GetTemplateCommand(
            scope_type=scope_type, template_id=template_id,
        ))

    def add_template(self, scope_type: str, body: dict) -> Optional[dict]:
        """新增模板；范围内首条自动设为默认（语义由 DDD 守护）。"""
        if not body.get("name"):
            body = dict(body)
            body["name"] = "未命名模板"
        cmd = self._body_to_command(scope_type, body)
        return _ddd.save_template(cmd)

    def update_template(self, scope_type: str, template_id: str, body: dict) -> Optional[dict]:
        """更新模板。"""
        cmd = self._body_to_command(scope_type, body, template_id=template_id)
        return _ddd.save_template(cmd)

    def delete_template(self, template_id: str) -> bool:
        return _ddd.delete_template(DeleteTemplateCommand(template_id=template_id))

    def set_default(self, scope_type: str, scope_id: str, scene: str, template_id: str) -> bool:
        return _ddd.set_default(SetDefaultCommand(
            scope_type=scope_type, scope_id=scope_id, scene=scene,
            template_id=template_id,
        ))


template_service = TemplateService()
