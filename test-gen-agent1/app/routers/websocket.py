# app/routers/websocket.py
"""业务域路由：websocket WebSocket 兼容路由。迁移自 app/adapters/domains/websocket.py，WebSocket handler 原样保留。"""

import json

from fastapi import APIRouter, WebSocket

from app.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["adapter-websocket"])


@router.websocket("/ws/api")
async def ws_api_base(websocket: WebSocket):
    """WebSocket API 基础连接。"""
    await websocket.accept()
    try:
        await websocket.send_text(json.dumps({"type": "connected"}))
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong", "data": data}))
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/api/{report_id}")
async def ws_api_report(websocket: WebSocket, report_id: str):
    """WebSocket API with report ID（前端 getSocket(reportId) 使用）。"""
    await websocket.accept()
    try:
        # 发送连接确认
        await websocket.send_text(json.dumps({"type": "connected", "report_id": report_id}))
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong", "data": data, "report_id": report_id}))
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass


# ════════════════════════════════════════════════════════════
# AI 配置
# ════════════════════════════════════════════════════════════


@router.websocket("/ws/debug")
async def ws_debug(websocket: WebSocket):
    """WebSocket 调试连接。"""
    await websocket.accept()
    try:
        await websocket.send_text(json.dumps({"type": "connected", "service": "debug"}))
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong", "data": data}))
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/debug/{report_id}")
async def ws_debug_report(websocket: WebSocket, report_id: str):
    """WebSocket 调试连接（带报告ID）。"""
    await websocket.accept()
    try:
        await websocket.send_text(json.dumps({"type": "connected", "report_id": report_id, "service": "debug"}))
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong", "data": data, "report_id": report_id}))
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/export")
async def ws_export(websocket: WebSocket):
    """WebSocket 导出连接。"""
    await websocket.accept()
    try:
        await websocket.send_text(json.dumps({"type": "connected", "service": "export"}))
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong", "data": data}))
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/export/{report_id}")
async def ws_export_report(websocket: WebSocket, report_id: str):
    """WebSocket 导出连接（带报告ID）。

    功能用例导出：前端先连上 /ws/export/{reportId}，随后通过 HTTP 触发
    /functional/case/export/* 生成文件并登记到导出任务注册表。本处理器
    轮询该注册表，就绪后推送 EXEC_RESULT（含 fileId/taskId/count）。
    """
    await websocket.accept()
    try:
        await websocket.send_text(json.dumps({"type": "connected", "report_id": report_id, "service": "export"}))
        task = await _wait_task_async(report_id)
        if task:
            payload = {
                "msgType": "EXEC_RESULT",
                "reportId": report_id,
                "fileId": task.get("fileId", report_id),
                "taskId": task.get("taskId", ""),
                "isSuccessful": bool(task.get("is_successful", True)),
                "count": int(task.get("count", 0) or 0),
            }
            await websocket.send_text(json.dumps(payload))
            # 已消费：从注册表移除，允许后续重复发起导出
            from app.services.export_task_service import remove_task
            remove_task(report_id)
        # 保持连接直至前端关闭（前端收到 EXEC_RESULT 后主动 close）
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong", "data": data, "report_id": report_id}))
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass


async def _wait_task_async(report_id: str, timeout: float = 30.0):
    """在事件循环中等待导出任务就绪，避免阻塞其它协程。"""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _wait_task_sync, report_id, timeout)


def _wait_task_sync(report_id: str, timeout: float):
    from app.services.export_task_service import wait_task
    return wait_task(report_id, timeout=timeout, interval=0.3)


# ════════════════════════════════════════════════════════════
# 消息通知
# ════════════════════════════════════════════════════════════

