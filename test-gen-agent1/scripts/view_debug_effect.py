#!/usr/bin/env python3
"""
查看 /api/debug/get/{debug_id} 接口效果
=======================================
针对 ISSUE 中「/api/debug/get/{debug_id} 应该返回什么数据」的疑问，
提供一个命令行工具：通过 FastAPI TestClient 实际调用该接口，
并格式化展示返回的 JSON 数据。

功能：
  - 查看任意 debug_id 的返回效果（存在则返回完整 DebugDetail，不存在返回空 data）
  - --list    列出当前所有已保存的调试项（含其 id，方便复制查询）
  - --demo    演示完整流程：先添加一条调试数据 → 再调用 get 接口查看其返回效果
  - --add-only 仅添加一条演示调试数据，打印其 id（不查询）

用法：
    python3 scripts/view_debug_effect.py 5dae636d-df64-4597-a332-f461637f6cfe
    python3 scripts/view_debug_effect.py --list
    python3 scripts/view_debug_effect.py --demo
    python3 scripts/view_debug_effect.py --add-only
"""
import argparse
import json
import os
import sys

# 将项目根目录加入 sys.path，确保可导入 app 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


def _make_client():
    """构建已认证的 TestClient。"""
    from app.main import app
    client = TestClient(app)
    r = client.post("/login", json={"username": "admin", "password": "admin123"})
    if r.status_code != 200:
        raise RuntimeError(f"登录失败: {r.status_code} {r.text}")
    session = r.json()["data"]
    client.headers.update({
        "X-AUTH-TOKEN": session["sessionId"],
        "CSRF-TOKEN": session["csrfToken"],
    })
    return client


def _pretty(data):
    """格式化输出 JSON。"""
    return json.dumps(data, ensure_ascii=False, indent=2)


def _add_debug(client, name="演示调试"):
    """添加一条调试数据，返回其 id。"""
    r = client.post("/api/debug/add", json={
        "name": name,
        "method": "GET",
        "path": "/api/apitest/stats",
        "url": "/api/apitest/stats",
        "projectId": "demo-project",
        "moduleId": "root",
        "request": {"method": "GET", "path": "/api/apitest/stats"},
        "response": {"body": {"code": 200, "message": "success"}},
    })
    if r.status_code != 200:
        raise RuntimeError(f"添加调试失败: {r.status_code} {r.text}")
    data = r.json().get("data") or {}
    return data.get("id")


def _view(client, debug_id):
    """调用 /api/debug/get/{debug_id} 并打印返回效果。"""
    url = f"/api/debug/get/{debug_id}"
    r = client.get(url)
    print(f"\n{'=' * 60}")
    print(f"请求: GET {url}")
    print(f"HTTP 状态码: {r.status_code}")
    print(f"{'=' * 60}")
    payload = r.json()
    print(f"返回 JSON:\n{_pretty(payload)}")
    print(f"{'=' * 60}")
    data = payload.get("data")
    if data:
        print(f"接口说明: 找到调试项 '{data.get('name', '')}' (id={data.get('id')})，返回其完整详情。")
    else:
        print("接口说明: 该 debug_id 不存在或未保存，命中 `return ... data: {}` 分支，返回空对象。")
        print("          提示: 调试数据需先通过 /api/debug/add 创建，生成的 id 形如 debug-<时间戳>-<hex>。")
    return r.status_code


def _list(client):
    """列出所有已保存的调试项。"""
    from app.services.debug_service import debug_service
    items = debug_service.all_items()
    if not items:
        print("当前没有已保存的调试数据。可通过 --demo 添加一条演示数据。")
        return
    print("当前已保存的调试项:")
    for item in items:
        print(f"  id={item.get('id')}  name={item.get('name')}  method={item.get('method')}  path={item.get('path')}")


def main():
    parser = argparse.ArgumentParser(description="查看 /api/debug/get/{debug_id} 接口返回效果")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("debug_id", nargs="?", help="要查询的调试 id")
    group.add_argument("--list", action="store_true", help="列出当前所有已保存的调试项")
    group.add_argument("--demo", action="store_true", help="演示完整流程: 添加调试 → 查看返回效果")
    group.add_argument("--add-only", action="store_true", help="仅添加一条演示调试数据，打印其 id")
    args = parser.parse_args()

    client = _make_client()

    if args.list:
        _list(client)
        return

    if args.add_only:
        new_id = _add_debug(client, name="演示调试-add-only")
        print(f"已添加演示调试数据，id={new_id}")
        print(f"可运行: python3 scripts/view_debug_effect.py {new_id} 来查看其返回效果")
        return

    if args.demo:
        new_id = _add_debug(client)
        print(f"已添加一条演示调试数据，id={new_id}")
        _view(client, new_id)
        return

    if not args.debug_id:
        parser.print_help()
        return

    _view(client, args.debug_id)


if __name__ == "__main__":
    main()
