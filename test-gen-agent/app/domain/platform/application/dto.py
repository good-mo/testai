"""platform 域 DTO (Data Transfer Objects).

从 models/platform.py 迁移而来。
"""
# app/models/platform.py
"""平台域 Pydantic 请求体模型（授权 /license/*）。

platform.py 兼容路由为占位 stub：license 上传/校验端点尚未真正落地，
仅登记请求体结构，handler 不消费其中业务字段。模型保持全可选 +
`extra: allow`，并内置 lenient 归一化，确保历史前端任意载荷
（对象 / 裸字符串 / 空体）都不会被判 422/500。
"""

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class _LenientRequest(BaseModel):
    """历史兼容：容忍前端经 axios 拦截器发送的裸标量请求体。

    迁移背景：旧路由用 read_body() 读取请求体时会做归一化
    （裸字符串 "x" → {"id": "x"}、数组 → {"ids": [...]}、空体 → {}），
    见 app/core/response.py。本文件 License 模型沿用同一约定：
    license 上传以裸字符串发送授权码，故归一化收口到 license 字段。
    """

    @model_validator(mode="before")
    @classmethod
    def _lenient_coerce(cls, raw):
        if isinstance(raw, str):
            return {"license": raw}
        if isinstance(raw, list):
            return {"licenses": raw}
        if raw is None:
            return {}
        return raw


class LicenseAddRequest(_LenientRequest):
    """POST /license/add 授权码上传请求体。

    前端 addLicense(licenseCode) 把授权文件内容以裸字符串发送，
    经 lenient 归一化收口到 license 字段。
    """

    license: Optional[str] = Field(None, description="授权码 / 授权文件内容")
    licenseCode: Optional[str] = Field(None, description="授权码（别名）")
    id: Optional[str] = Field(None, description="兼容裸字符串归一化")
    model_config = {"extra": "allow"}


class LicenseValidateBody(_LenientRequest):
    """POST /license/validate 授权校验请求体（占位，暂无消费字段）。"""

    license: Optional[str] = Field(None, description="授权码")
    model_config = {"extra": "allow"}


__all__ = ["LicenseAddRequest", "LicenseValidateBody"]
