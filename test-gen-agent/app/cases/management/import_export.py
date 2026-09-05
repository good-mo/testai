# -*- coding: utf-8 -*-
"""app.cases.management.import_export 子模块（自 management.py 拆出，行为不变）。"""

import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List

from app.cases.management._base import CHANGE_IMPORTED, _get_base_case, _record_change
from app.repositories.case_repo import CaseRepo


def export_cases_excel(cases: List[Dict[str, Any]]) -> bytes:
    """将用例导出为 Excel 格式（CSV with BOM for Excel compatibility）。"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "标题", "描述", "类型", "优先级", "状态",
                     "标签", "文件路径", "需求关联", "创建时间"])
    for c in cases:
        tags = ",".join(c.get("tags") or [])
        writer.writerow([
            c.get("id", ""),
            c.get("title", ""),
            c.get("description", ""),
            c.get("test_type", "functional"),
            c.get("priority", "P2"),
            c.get("status", "draft"),
            tags,
            c.get("file_path", ""),
            c.get("requirement_ref", ""),
            datetime.fromtimestamp(c.get("created_at") or 0).strftime("%Y-%m-%d %H:%M:%S"),
        ])
    csv_data = output.getvalue()
    # 加 BOM 让 Excel 正确识别 UTF-8
    return ("\ufeff" + csv_data).encode("utf-8")

def export_cases_mindmap(cases: List[Dict[str, Any]]) -> str:
    """将用例导出为 XMind 兼容的 JSON 格式。"""
    from app.cases.management import get_case_mindmap
    mindmap = get_case_mindmap()
    return json.dumps(mindmap, ensure_ascii=False, indent=2)


def _create_imported_case(**kwargs) -> Dict[str, Any]:
    """按导入语义创建用例：写入主表并记录 created 变更与初始版本。

    原实现经旧 app.cases.repository.create_case 隐式完成这些副作用；
    现在统一委托 CaseRepo 并在编排层显式补齐，行为保持一致。
    """
    case = CaseRepo.create(kwargs)
    if case:
        try:
            cid = case.get("id", "")
            if cid:
                CaseRepo.record_change(cid, CaseRepo.CHANGE_CREATED,
                                       field="title", new_value=case.get("title", ""))
                CaseRepo.create_version(cid, created_by="system", change_desc="初始版本")
                CaseRepo.invalidate_mindmap_cache()
        except Exception:
            pass
    return case


def import_cases_from_excel(csv_text: str, operator: str = "") -> Dict[str, Any]:
    """从 Excel (CSV) 导入用例。"""
    reader = csv.DictReader(io.StringIO(csv_text))
    imported = 0
    errors = []
    for row in reader:
        try:
            title = (row.get("标题") or row.get("title") or "").strip()
            if not title:
                continue
            test_type = (row.get("类型") or row.get("test_type") or "functional").strip()
            priority = (row.get("优先级") or row.get("priority") or "P2").strip()
            tags_str = (row.get("标签") or row.get("tags") or "").strip()
            tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
            case = _create_imported_case(
                title=title,
                description=row.get("描述") or row.get("description") or "",
                file_path=row.get("文件路径") or row.get("file_path") or "",
                tags=tags,
                status="draft",
                priority=priority if priority in ("P0", "P1", "P2", "P3") else "P2",
                test_type=test_type,
                requirement_ref=row.get("需求关联") or row.get("requirement_ref") or "",
            )
            imported += 1
            _record_change(case.get("id", ""), CHANGE_IMPORTED, operator=operator)
        except Exception as e:
            errors.append(f"行 {reader.line_num}: {str(e)}")
    return {"imported": imported, "errors": errors}

def import_cases_from_xmind(mindmap_json: str, operator: str = "") -> Dict[str, Any]:
    """从 XMind JSON 导入用例。"""
    try:
        data = json.loads(mindmap_json)
    except json.JSONDecodeError as e:
        return {"imported": 0, "errors": [f"JSON 解析失败: {e}"]}

    imported = 0
    errors = []

    def walk_node(node, parent_type=""):
        nonlocal imported
        text = node.get("text", "")
        node_type = node.get("type", "")
        case_id = node.get("case_id", "")
        children = node.get("children", [])

        # 如果是用例节点，创建用例
        if node_type == "case" and case_id:
            existing = _get_base_case(case_id)
            if existing:
                return
            try:
                case = _create_imported_case(
                    title=text,
                    status="draft",
                    test_type=parent_type or "functional",
                )
                imported += 1
                _record_change(case.get("id", ""), CHANGE_IMPORTED, operator=operator)
            except Exception as e:
                errors.append(f"节点「{text}」: {str(e)}")
        elif case_id:
            existing = _get_base_case(case_id)
            if not existing:
                try:
                    case = _create_imported_case(title=text, status="draft")
                    imported += 1
                except Exception as e:
                    errors.append(f"节点「{text}」: {str(e)}")

        for child in children:
            walk_node(child, parent_type=node.get("id", "") or parent_type)

    walk_node(data)
    return {"imported": imported, "errors": errors}
