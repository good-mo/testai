# app/routers/debug_compat.py（自 app/adapters/domains/debug.py 迁移）
"""业务域路由拆分：debug（Phase 3 重构）。"""

import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

from app.core.response import fail, ok, read_body
from app.core.helpers import as_model
from app.logging_config import get_logger
from app.models.debug import (
    DebugEchoBody,
    DebugEditPosBody,
    DebugExecuteBody,
    DebugIdBody,
    DebugImportCurlBody,
    DebugModuleAddBody,
    DebugModuleMoveBody,
    DebugModuleUpdateBody,
    DebugSaveBody,
)
from app.services.apitest_service import apitest_service
from app.services.curl_parser import parse_curl
from app.services.debug_service import debug_service

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-debug"])


def _debug_id() -> str:
    """生成唯一调试 ID。"""
    return f"debug-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"


def _to_debug(item: Dict[str, Any]) -> Dict[str, Any]:
    """将内部存储对象转换为前端期望的 DebugDetail 格式。"""
    request_data = item.get("request", {})
    # 如果 request 为空但顶层有请求字段，则从顶层提取
    if not request_data:
        request_data = {
            k: v for k, v in item.items()
            if k in ("authConfig", "body", "headers", "query", "rest", "otherConfig",
                     "polymorphicName", "uploadFileIds", "linkFileIds")
            and v is not None
        }
    return {
        "id": item.get("id", ""),
        "name": item.get("name", "未命名调试"),
        "protocol": item.get("protocol", "HTTP"),
        "method": item.get("method", "GET"),
        "path": item.get("path", item.get("url", "/")),
        "url": item.get("url", item.get("path", "/")),
        "projectId": item.get("projectId", item.get("project_id", "")),
        "moduleId": item.get("moduleId", item.get("module_id", "root")),
        "createTime": item.get("createTime", int(time.time() * 1000)),
        "createUser": item.get("createUser", "admin"),
        "updateTime": item.get("updateTime", int(time.time() * 1000)),
        "updateUser": item.get("updateUser", "admin"),
        "pos": item.get("num", item.get("pos", 1)),
        "num": item.get("num", 1),
        "request": request_data,
        "response": item.get("response", {}),
        "isNew": item.get("isNew", False),
        "unSaved": item.get("unSaved", False),
        # 同时输出顶层请求字段，供前端直接使用
        "authConfig": item.get("authConfig", item.get("request", {}).get("authConfig")),
        "body": item.get("body", item.get("request", {}).get("body")),
        "headers": item.get("headers", item.get("request", {}).get("headers")),
        "query": item.get("query", item.get("request", {}).get("query")),
        "rest": item.get("rest", item.get("request", {}).get("rest")),
        "otherConfig": item.get("otherConfig", item.get("request", {}).get("otherConfig")),
        "polymorphicName": item.get("polymorphicName", item.get("request", {}).get("polymorphicName")),
        "uploadFileIds": item.get("uploadFileIds", item.get("request", {}).get("uploadFileIds", [])),
        "linkFileIds": item.get("linkFileIds", item.get("request", {}).get("linkFileIds", [])),
    }


@router.get("/api/debug/delete")
def api_debug_delete_get(request: Request):
    """接口调试删除（GET兼容）。"""
    return ok()


@router.get("/api/debug/get")
def api_debug_get(id: str = ""):
    """接口调试详情。"""
    if id and debug_service.has(id):
        return ok(_to_debug(debug_service.get(id)))
    return ok({})


@router.post("/api/debug/get")
async def api_debug_get_post(request: Request):
    """接口调试详情 POST。"""
    body = as_model(await read_body(request), DebugIdBody)
    debug_id = body.effective_id
    if debug_id and debug_service.has(debug_id):
        return ok(_to_debug(debug_service.get(debug_id)))
    return ok({})


@router.post("/api/debug/edit/pos")
async def api_debug_edit_pos(request: Request):
    """接口调试拖拽排序。

    前端 dragDebug 发送 { projectId, moveMode, moveId, targetId, moduleId }。
    将调试项从源模块移动到目标模块。
    """
    body = as_model(await read_body(request), DebugEditPosBody)
    move_id = body.effective_move_id
    module_id = body.effective_module_id
    if move_id and module_id and debug_service.has(move_id):
        item = debug_service.get(move_id)
        item["moduleId"] = module_id
        item["updateTime"] = int(time.time() * 1000)
        debug_service.save(item)
    return ok()


@router.post("/api/debug/transfer")
def api_debug_transfer():
    """调试文件转存。"""
    return ok()


@router.get("/api/debug/transfer/options")
def api_debug_transfer_options(project_id: str = ""):
    """调试文件转存目录。"""
    return ok([])


@router.post("/api/debug/upload/temp/file")
async def api_debug_upload_temp_file(request: Request):
    """调试临时文件上传。

    前端用 MSR.uploadFile 以 multipart 形式提交 file 字段。
    此处接收文件并保存到临时目录，返回 fileId/fileName 供前端引用。
    """
    try:
        form = await request.form()
        file_field = form.get("file")
        if file_field is not None:
            fname = getattr(file_field, "filename", "") or "temp"
            # 读取内容并保存到 uploads 目录
            content_bytes = await file_field.read()
            import os
            upload_dir = os.path.join(os.getcwd(), "uploads", "temp")
            os.makedirs(upload_dir, exist_ok=True)
            file_id = str(uuid.uuid4())
            # 用 fileId 作为存储名，保留原扩展名
            ext = os.path.splitext(fname)[1] if fname else ""
            saved_name = f"{file_id}{ext}"
            save_path = os.path.join(upload_dir, saved_name)
            with open(save_path, "wb") as f:
                f.write(content_bytes)
            return ok({"fileId": file_id, "fileName": fname, "path": f"/uploads/temp/{saved_name}"})
        return ok({"fileId": str(uuid.uuid4()), "fileName": "temp"})
    except Exception as e:
        logger.warning("文件上传失败: %s", e)
        return ok({"fileId": str(uuid.uuid4()), "fileName": "temp"})


@router.post("/api/debug")
async def api_debug(request: Request):
    """接口调试（本地执行入口）。

    localExecuteApiDebug 将 ExecuteRequestParams 发给本地执行服务，
    由本地执行服务在浏览器侧实际发起 HTTP 请求。
    本端点回传原始请求体（body 本身就是 ExecuteRequestParams），
    便于本地执行服务解析并执行。
    """
    raw = await read_body(request)
    as_model(raw, DebugEchoBody)  # 经建档模型校验（Extra=allow 不丢字段）
    # 回传 body（可能是 ExecuteRequestParams 结构），并附带成功状态
    if isinstance(raw, dict) and raw:
        return ok(raw)
    # 无有效请求体时返回空结构
    return ok({
        "status": 200,
        "success": True,
        "body": {},
    })


@router.post("/api/debug/import-curl")
async def api_debug_import_curl(request: Request):
    """导入 Curl 命令，返回可供前端构建 API 定义的结构化结果。"""
    body = as_model(await read_body(request), DebugImportCurlBody)
    curl_cmd = body.effective_curl
    if not curl_cmd or not isinstance(curl_cmd, str):
        # 前端 importByCurl 只发送 { curl }；空内容时给出兜底结构
        curl_cmd = ""
    if not curl_cmd.strip():
        # 未提供有效 curl 命令时返回空默认值，避免前端解构 null 抛错
        return ok({
            "method": "GET",
            "url": "",
            "headers": {},
            "body": None,
            "bodyType": "NONE",
            "queryParams": {},
        })
    try:
        parsed = parse_curl(curl_cmd)
    except Exception as e:  # noqa: BLE001 - 解析失败不应让整个接口 500
        logger.warning("curl 解析失败: %s", e)
        parsed = {
            "method": "GET",
            "url": curl_cmd.strip(),
            "headers": {},
            "body": None,
            "bodyType": "NONE",
            "queryParams": {},
        }
    return ok(parsed)


# ════════════════════════════════════════════════════════════
# 任务中心适配
# ════════════════════════════════════════════════════════════


@router.post("/api/debug/debug")
async def api_debug_execute(request: Request):
    """执行调试请求。

    前端发送 ExecuteRequestParams：
    {
        id, reportId, environmentId, name, moduleId, protocol, method,
        path, request: {url, method, headers[], query[], body{...}, ...},
        projectId, frontendDebug, isNew
    }
    后端提取实际 URL / method / headers / query / body 后发起 HTTP 请求，
    返回与前端 response 结构兼容的结果。若 frontendDebug=true，
    则原样回传请求体供本地执行服务消费。
    """
    raw = await read_body(request)
    body = as_model(raw, DebugExecuteBody)
    body_dict = body.model_dump(exclude_none=True)

    # 本地执行模式：原样返回请求体，由前端转发到本地执行服务
    if body_dict.get("frontendDebug") or (isinstance(raw, dict) and raw.get("frontendDebug")):
        return ok(raw if isinstance(raw, dict) and raw else body_dict)

    # 从嵌套 request 中提取实际请求
    req = body.request or {}
    if not isinstance(req, dict):
        req = {}

    method = (body.method or req.get("method") or "GET").upper()
    url = body.path or req.get("url") or req.get("path") or ""
    # 提取 headers：可能为 [{key, value, enable}] 数组或 dict
    headers_raw = req.get("headers") or []
    headers = {}
    if isinstance(headers_raw, dict):
        headers = {k: str(v) for k, v in headers_raw.items() if k and v is not None}
    else:
        for h in headers_raw:
            if isinstance(h, dict) and h.get("enable", True):
                hk = h.get("key", "")
                hv = h.get("value", "")
                if hk and hv is not None:
                    headers[hk] = str(hv)

    # 提取 query 参数
    query_raw = req.get("query") or []
    query_params = {}
    if isinstance(query_raw, dict):
        query_params = {k: str(v) for k, v in query_raw.items() if k}
    else:
        for q in query_raw:
            if isinstance(q, dict) and q.get("enable", True):
                qk = q.get("key", "")
                qv = q.get("value", "")
                if qk and qv is not None:
                    query_params[qk] = str(qv)

    # 提取 body
    body_data = req.get("body") or {}
    body_type = "json"
    request_body = ""

    if isinstance(body_data, dict):
        btype = body_data.get("bodyType", "")
        # json body
        json_body = body_data.get("jsonBody") or {}
        if json_body:
            request_body = json_body.get("jsonValue", "") if isinstance(json_body, dict) else str(json_body)
            body_type = "json"
        elif btype == "JSON":
            request_body = json_body.get("jsonValue", "")
            body_type = "json"
        # xml body
        elif body_data.get("xmlBody"):
            xml_v = body_data["xmlBody"]
            request_body = xml_v.get("value", "") if isinstance(xml_v, dict) else str(xml_v)
            body_type = "xml"
        # raw body
        elif body_data.get("rawBody"):
            raw_v = body_data["rawBody"]
            request_body = raw_v.get("value", "") if isinstance(raw_v, dict) else str(raw_v)
            body_type = "raw"
        # form-urlencoded body
        elif body_data.get("wwwFormBody"):
            form_v = body_data.get("wwwFormBody", {}).get("formValues", [])
            parts = []
            for f in form_v:
                if isinstance(f, dict) and f.get("enable", True):
                    k = f.get("key", "")
                    v = f.get("value", "")
                    if k:
                        parts.append(f"{k}={v}")
            request_body = "&".join(parts)
            body_type = "form"

    # 使用统一 debug_api_call 发起请求
    try:
        import asyncio
        result = await asyncio.to_thread(
            _execute_http_call,
            method=method,
            url=url,
            headers=headers,
            params=query_params,
            body=request_body,
            body_type=body_type,
            timeout=30,
        )
        return ok(result)
    except Exception as e:
        logger.error("执行调试失败: %s", e)
        return fail(str(e), code=500)


def _execute_http_call(method: str = "GET", url: str = "", headers: dict = None,
                       params: dict = None, body: str = "", body_type: str = "json",
                       timeout: int = 30) -> dict:
    """在独立线程中执行 HTTP 请求，返回兼容前端的 RequestTaskResult。"""
    import time as _t
    import urllib.error
    import urllib.parse
    import urllib.request

    headers = headers or {}
    params = params or {}
    start = _t.time()
    response_code = 0
    response_body = ""
    response_headers = ""
    is_success = False
    error_msg = ""

    try:
        # 构造 URL
        target_url = url
        if params:
            qs = urllib.parse.urlencode(params)
            sep = '&' if '?' in target_url else '?'
            target_url = f"{target_url}{sep}{qs}"

        # 构造请求
        req_headers = dict(headers)
        data_bytes = None
        if body and method in ('POST', 'PUT', 'PATCH'):
            data_bytes = body.encode('utf-8')
            ct = None
            for hk, hv in req_headers.items():
                if hk.lower() == 'content-type':
                    ct = hv
                    break
            if not ct:
                if body_type == 'json':
                    req_headers['Content-Type'] = 'application/json'
                elif body_type == 'form':
                    req_headers['Content-Type'] = 'application/x-www-form-urlencoded'
                elif body_type == 'xml':
                    req_headers['Content-Type'] = 'application/xml'

        req = urllib.request.Request(target_url, data=data_bytes,
                                     headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                response_body = resp.read().decode('utf-8', errors='replace')
                response_code = resp.status
                response_headers = str(dict(resp.headers.items()))
                is_success = True
        except urllib.error.HTTPError as e:
            response_body = e.read().decode('utf-8', errors='replace') if hasattr(e, 'read') else ''
            response_code = e.code
            response_headers = str(dict(e.headers.items())) if e.headers else ""
            error_msg = f"HTTP {e.code}: {e.reason}"
        except Exception as e:
            error_msg = str(e)

        duration_ms = round((_t.time() - start) * 1000, 2)
        return {
            "requestResults": [
                {
                    "body": response_body,
                    "headers": response_headers,
                    "url": target_url,
                    "method": method,
                    "isSuccessful": is_success,
                    "fakeErrorCode": error_msg if error_msg else "",
                    "responseResult": {
                        "body": response_body,
                        "contentType": headers.get("Accept", ""),
                        "headers": response_headers,
                        "dnsLookupTime": 0,
                        "downloadTime": 0,
                        "latency": 0,
                        "responseCode": response_code,
                        "responseTime": duration_ms,
                        "responseSize": len(response_body.encode('utf-8', errors='replace')),
                        "socketInitTime": 0,
                        "sslHandshakeTime": 0,
                        "tcpHandshakeTime": 0,
                        "transferStartTime": 0,
                        "vars": "",
                        "extractResults": [],
                        "assertions": [],
                    },
                }
            ],
            "console": error_msg or "",
            "status": "SUCCESS" if is_success else "ERROR",
            "isSuccessful": is_success,
        }
    except Exception as e:
        duration_ms = round((_t.time() - start) * 1000, 2)
        return {
            "requestResults": [
                {
                    "body": "",
                    "headers": "",
                    "url": url,
                    "method": method,
                    "isSuccessful": False,
                    "fakeErrorCode": str(e),
                    "responseResult": {
                        "body": "",
                        "contentType": "",
                        "headers": "",
                        "dnsLookupTime": 0,
                        "downloadTime": 0,
                        "latency": 0,
                        "responseCode": 0,
                        "responseTime": duration_ms,
                        "responseSize": 0,
                        "socketInitTime": 0,
                        "sslHandshakeTime": 0,
                        "tcpHandshakeTime": 0,
                        "transferStartTime": 0,
                        "vars": "",
                        "extractResults": [],
                        "assertions": [],
                    },
                }
            ],
            "console": str(e),
            "status": "ERROR",
            "isSuccessful": False,
        }


@router.post("/api/debug/add")
async def api_debug_add(request: Request):
    """新增调试。"""
    raw = await read_body(request)
    body = as_model(raw, DebugSaveBody)
    debug_id = _debug_id()
    sent = body.model_dump(exclude_unset=True)

    # 提取请求字段 - 前端可能以顶层字段发送，也可能嵌套在 request 中
    request_data = body.effective_request()

    item = {
        "id": debug_id,
        "name": body.name if body.name else "未命名调试",
        "protocol": body.protocol,
        "method": body.method,
        "path": body.path or body.url or "/",
        "url": body.url or body.path or "/",
        "projectId": body.projectId or body.project_id or "",
        "moduleId": body.moduleId or body.module_id or "root",
        "request": request_data,
        "response": body.response or {},
        "createTime": int(time.time() * 1000),
        "updateTime": int(time.time() * 1000),
        "num": debug_service.next_num(),
        "isNew": False,
    }
    # 同时保存顶层请求字段（仅客户端实发字段，等价旧 `if key in body` 判断）
    for key in ("authConfig", "body", "headers", "query", "rest", "otherConfig", "polymorphicName", "uploadFileIds", "linkFileIds"):
        if key in sent:
            item[key] = sent[key]

    debug_service.save(item)
    return ok(_to_debug(item))


@router.post("/api/debug/update")
async def api_debug_update(request: Request):
    """更新调试。"""
    raw = await read_body(request)
    body = as_model(raw, DebugSaveBody)
    debug_id = body.id or ""
    sent = body.model_dump(exclude_unset=True)

    # 重新构建 request 数据
    request_data = body.effective_request()

    if debug_id and debug_service.has(debug_id):
        item = debug_service.get(debug_id)
        # 更新基础字段（仅客户端实发字段）
        for key in ("name", "protocol", "method", "path", "url", "projectId", "moduleId", "response"):
            if key in sent:
                item[key] = sent[key]
        # 更新请求数据
        if request_data:
            item["request"] = request_data
        # 同时保存顶层请求字段
        for key in ("authConfig", "body", "headers", "query", "rest", "otherConfig", "polymorphicName", "uploadFileIds", "linkFileIds"):
            if key in sent:
                item[key] = sent[key]
        item["updateTime"] = int(time.time() * 1000)
        debug_service.save(item)
        return ok(_to_debug(item))

    # 不存在则创建新的
    item = {
        "id": debug_id or _debug_id(),
        "name": body.name if body.name else "未命名调试",
        "protocol": body.protocol,
        "method": body.method,
        "path": body.path or body.url or "/",
        "url": body.url or body.path or "/",
        "projectId": body.projectId or body.project_id or "",
        "moduleId": body.moduleId or body.module_id or "root",
        "request": request_data,
        "response": body.response or {},
        "createTime": int(time.time() * 1000),
        "updateTime": int(time.time() * 1000),
        "num": debug_service.next_num(),
        "isNew": False,
    }
    for key in ("authConfig", "body", "headers", "query", "rest", "otherConfig", "polymorphicName", "uploadFileIds", "linkFileIds"):
        if key in sent:
            item[key] = sent[key]
    debug_service.save(item)
    return ok(_to_debug(item))


@router.get("/api/debug/get/{debug_id}")
def api_debug_get_by_path(debug_id: str):
    """获取调试详情。"""
    if debug_service.has(debug_id):
        return ok(_to_debug(debug_service.get(debug_id)))
    return ok({})


@router.post("/api/debug/delete")
async def api_debug_delete(request: Request):
    """删除调试。"""
    body = as_model(await read_body(request), DebugIdBody)
    debug_id = body.effective_id
    if debug_id and debug_service.has(debug_id):
        debug_service.delete(debug_id)
    return ok(None)


def _find_module_node(nodes: List[Dict], module_id: str) -> Optional[Dict]:
    """递归在模块树中查找指定 ID 的模块节点。"""
    for node in nodes:
        if node.get("id") == module_id:
            return node
        if node.get("children"):
            found = _find_module_node(node["children"], module_id)
            if found:
                return found
    return None


@router.get("/api/debug/module/tree")
def api_debug_module_tree():
    """获取调试模块树。"""
    tree = apitest_service.build_module_tree("debug", include_api=False)
    # 将内存中的调试项挂到模块树下的 API 节点
    for item in debug_service.all_items():
        module_id = item.get("moduleId", "root")
        # 递归查找模块节点
        target = _find_module_node(tree, module_id)
        if target is None:
            # 创建虚拟模块节点
            virtual = {
                "id": module_id,
                "name": "全部模块",
                "type": "MODULE",
                "parentId": "root",
                "children": [],
                "count": 0,
                "path": "/全部模块",
            }
            # 挂到根节点下
            if tree:
                tree[0].setdefault("children", []).append(virtual)
            else:
                tree.append(virtual)
            target = virtual
        target.setdefault("children", []).append({
            "id": item["id"],
            "name": item.get("name", "未命名调试"),
            "type": "API",
            "parentId": module_id,
            "children": [],
            "count": 0,
            "attachInfo": {
                "method": item.get("method", "GET"),
                "protocol": item.get("protocol", "HTTP"),
            },
            "path": item.get("path", "/"),
        })
        target["count"] = target.get("count", 0) + 1
    return ok(tree)


@router.post("/api/debug/module/add")
async def api_debug_module_add(request: Request):
    """添加调试模块。"""
    body = as_model(await read_body(request), DebugModuleAddBody)
    module = apitest_service.add_module(
        scope="debug",
        name=body.effective_name,
        parent_id=body.effective_parent_id,
        project_id=body.effective_project_id,
    )
    return ok(module)


@router.post("/api/debug/module/count", operation_id="api_debug_module_count_post")
@router.get("/api/debug/module/count", operation_id="api_debug_module_count_get")
def api_debug_module_count():
    """获取调试模块数量。

    返回 { moduleId: count, all: total, root: total } 映射，
    与 /api/definition/module/count 格式一致（前端 modulesCount 按 key 取值）。
    """
    modules = apitest_service.list_modules("debug")
    debug_items = debug_service.all_items()
    # 统计每个模块下的调试项数量
    count_by_module: Dict[str, int] = {}
    for item in debug_items:
        mod_id = item.get("moduleId", "root")
        count_by_module[mod_id] = count_by_module.get(mod_id, 0) + 1
    total = len(debug_items)

    result: Dict[str, Any] = {"all": total, "root": total}
    for m in modules:
        mid = m.get("id", "")
        result[mid] = count_by_module.get(mid, 0)
    return ok(result)


@router.post("/api/debug/module/update")
async def api_debug_module_update(request: Request):
    """更新调试模块。"""
    body = as_model(await read_body(request), DebugModuleUpdateBody)
    mod_id = body.effective_id
    mod_name = body.name
    if mod_id and mod_name:
        try:
            apitest_service.update_module(mod_id, name=mod_name)
        except Exception as e:
            logger.warning("更新调试模块失败 %s: %s", mod_id, e)
    return ok({
        "id": mod_id,
        "name": mod_name,
        "type": "MODULE",
        "parentId": body.effective_parent_id,
        "children": [],
        "count": 0,
    })


@router.get("/api/debug/module/delete")
def api_debug_module_delete(id: str = ""):
    """删除调试模块（GET 查询参数形式，前端调用兼容）。"""
    if id:
        try:
            apitest_service.delete_module(id)
        except Exception as e:
            logger.warning("删除调试模块失败 %s: %s", id, e)
    return ok(None)


@router.post("/api/debug/module/move")
async def api_debug_module_move(request: Request):
    """移动调试模块。

    前端 moveDebugModule 发送 { dragNodeId, dropNodeId, dropPosition }。
    """
    body = as_model(await read_body(request), DebugModuleMoveBody)
    drag_id = body.effective_drag_id
    drop_id = body.effective_drop_id
    drop_pos = int(body.dropPosition)
    if drag_id:
        try:
            apitest_service.move_module(drag_id, drop_id, drop_pos)
        except Exception as e:
            logger.warning("移动调试模块失败: %s", e)
    return ok(None)


# ════════════════════════════════════════════════════════════
# 缺失接口补充 - Mock 管理
# ════════════════════════════════════════════════════════════


@router.post("/api/debug/file/copy")
def api_debug_file_copy(request: Request):
    """接口调试文件复制。"""
    return ok(None)


# ════════════════════════════════════════════════════════════
# 路径参数兼容路由（自 path_param_fixes.py 迁移）
# ════════════════════════════════════════════════════════════

@router.get("/api/debug/module/delete/{deleteId}")
@router.post("/api/debug/module/delete/{deleteId}")
def api_debug_module_delete_path(deleteId: str):
    """/api/debug/module/delete 带路径参数（前端 RESTful 调用兼容）。"""
    try:
        apitest_service.delete_module(deleteId)
    except Exception:
        pass
    return ok({"id": deleteId, "deleted": True})


@router.get("/api/debug/transfer/options/{projectId}")
@router.post("/api/debug/transfer/options/{projectId}")
def api_debug_transfer_options_path(projectId: str):
    """/api/debug/transfer/options 带项目ID路径参数（前端 RESTful 调用兼容）。"""
    return ok([])
