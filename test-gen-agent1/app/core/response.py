# app/core/response.py
"""
统一响应格式
============
Phase 4 重构目标：替换各路由中手写的 JSONResponse，统一输出
{code, message, data} 格式。
"""

import json

from fastapi import Request
from fastapi.responses import JSONResponse


def ok(data=None, message: str = "success", code: int = 200) -> JSONResponse:
    """成功响应。"""
    return JSONResponse(
        {"code": code, "message": message, "data": data},
        status_code=code,
    )


def fail(message: str = "error", code: int = 400, data=None) -> JSONResponse:
    """失败响应。"""
    return JSONResponse(
        {"code": code, "message": message, "data": data},
        status_code=code if code >= 400 else 400,
    )


def page_result(items: list, total: int, current: int = 1, page_size: int = 10) -> JSONResponse:
    """分页结果响应。"""
    return ok({
        "list": items,
        "total": total,
        "current": current,
        "pageSize": page_size,
    })

def stub(message: str = "占位接口 stub：尚未接入真实业务", data=None) -> JSONResponse:
    """占位（stub）接口响应：返回明确标识，避免「假成功」。

    背景：历史遗留大量兼容 shim 路由仅 `return ok(None)` / 读请求体后
    `return ok()` —— 前端提示「操作成功」但后端什么都没做，测试只看 200
    也覆盖不到。这里提供统一出口：占位路由一律返回 `ok()` 包装的
    `{"stub": true, "message": ...}`，让调用方与测试能从响应体辨识这是
    占位，而不是被误当成真实业务已完成。

    语义上仍返回 HTTP 200 + `code: 200`（不破坏前端既有成功分支），
    仅补充 `stub` 标识，避免对线上既有 200 成功流程造成回归。
    """
    payload: dict = {"stub": True, "message": message}
    if data is not None:
        payload["data"] = data
    return ok(payload, message=message)


__all__ = ["ok", "fail", "page_result", "stub"]


# ── 请求体归一化 ──────────────────────────────────────────────
async def read_body(request: Request) -> dict:
    """安全读取 JSON 请求体，始终返回 dict。

    为什么要归一化：
      前端 axios 拦截器（`frontend/src/api/http/index.ts` 的
      `beforeRequestHook`）对非 GET 请求有一条规则 —— 如果没有显式
      `data`，就把 `params` 当成请求体：

          config.data = { ...params };

      但很多前端调用点写成 `params: poolId`（一个字符串），于是请求体
      就是裸字符串 `"xxxx"` 而不是 `{"id": "xxxx"}`。后端若直接
      `body.get("id")` 会抛 `AttributeError: 'str' object has no attribute
      'get'`，表现为接口 500。

      这里统一把三种常见形态归一化成 dict：
        - `{"id": "x"}`  → 原样返回
        - `"x"`          → `{"id": "x"}`
        - `["a", "b"]`   → `{"ids": ["a", "b"]}`

    任何失败（空体 / 非 JSON / 表单）都返回空字典，绝不抛异常。
    """
    try:
        raw = await request.body()
        if not raw:
            return {}
        data = await request.json()
    except Exception:
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        return {"id": data}
    if isinstance(data, list):
        return {"ids": data}
    return {}


# 由服务端生成的字段：绝不能由客户端指定。
# read_body() 会把裸字符串 "x" 归一化成 {"id": "x"}、数组归一化成
# {"ids": [...]}，这类路由若直接 `**body` 展开传给 service/store，
# 就等于让客户端塞入 id/ids —— 轻则 `unexpected keyword argument`
# 报 500，重则 `_update()` 用 data.keys() 直接拼 SQL SET 子句，
# 触发 `no such column: id/ids`。
AUTO_GENERATED_FIELDS = ("id", "ids")


async def read_writable_body(request: Request) -> dict:
    """读取「写操作」请求体：归一化后再剔除客户端传入的服务端字段。

    适用场景：路由拿到 body 后会 `**body` 展开传给 service / store 的
    创建与更新接口（如 `create_definition(**body)`）。这类接口的主键由
    服务端生成，若客户端塞了 id/ids 会得到 500（create）或
    `no such column`（update 直接拼 SQL）。

    不适用于「批量操作」路由 —— 它们本就要从 body 里读 ids
    （`body.get("ids")`），必须继续用 read_body()。
    """
    body = await read_body(request)
    for field in AUTO_GENERATED_FIELDS:
        body.pop(field, None)
    return body


async def read_form_or_json(request: Request) -> dict:
    """读取表单或 JSON 请求体，兼容前端「上传表单」与普通 JSON 两种提交。

    背景：
      前端文件上传封装 `MSR.uploadFile`（frontend/src/api/http/Axios.ts）会把
      整个业务对象以 `JSON.stringify` 后的 Blob 塞进名为 `request` 的
      multipart/form-data 字段里，真正的业务附件文件放在其余字段。缺陷、
      环境管理等“创建/编辑并携带附件”的页面都走这一通道。

      这类请求的 Content-Type 是 multipart/form-data，后端若只
      `await request.json()` 会解析失败（read_body 返回空 dict），导致
      `body.get("id")` 取不到主键 —— 更新接口会把“缺陷/环境不存在”误判成
      404、创建接口则存成“未命名标题”。这里统一兼容两种 Content-Type。

    返回始终为 dict；解析失败返回空字典，绝不抛异常。
    """
    content_type = request.headers.get("content-type", "").lower()
    if "multipart/form-data" in content_type:
        try:
            form = await request.form()
        except Exception:
            return {}
        request_field = form.get("request")
        if request_field is None:
            return {}
        # 前端把 request 塞成 JSON Blob → Starlette 解析为带 read() 的文件字段
        if hasattr(request_field, "read"):
            try:
                raw = await request_field.read()
                return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
            except (json.JSONDecodeError, TypeError, AttributeError):
                return {}
        # 少数实现以纯文本 form 字段提交
        try:
            return json.loads(request_field)
        except (json.JSONDecodeError, TypeError):
            return {}
    return await read_body(request)



__all__ = ["ok", "fail", "page_result", "stub", "read_body", "read_writable_body", "read_form_or_json"]
