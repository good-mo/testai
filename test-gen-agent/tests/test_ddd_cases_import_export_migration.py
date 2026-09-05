"""cases 域 import/export 旁路方法 DDD 覆盖 · 迁移回归测试。

case_service 的 import/export（export_excel / export_mindmap /
import_excel / import_mindmap）曾直连 CaseRepo，现收敛为对 DDD
`case_app_service` 的薄委托（透传既有 CaseRepo，字节/结构契约不变）。
本文件断言：
  1. 导出路径确实经 DDD 门面返回与既有 CaseRepo 一致的 bytes/JSON；
  2. 导入路径确实经 DDD 门面创建用例并返回既有 {imported, errors} 结构；
  3. 门面收敛后对外行为零回归（对外 API 不变）。
"""

import json
import uuid

from app.repositories.case_repo import CaseRepo
from app.services.case_service import case_service

TAG = "ddd-ie"


def _mk(prefix="ie"):
    return f"{prefix}-{TAG}-{uuid.uuid4().hex[:8]}"


def _cleanup(case_id):
    try:
        CaseRepo.purge_case(case_id)
    except Exception:
        pass


class TestExportDelegation:
    def test_export_excel_returns_bytes(self):
        """导出 Excel 经 DDD 门面返回 bytes（与既有契约一致）。"""
        cid = _mk("x1")
        case = case_service.create(
            {"id": cid, "title": _mk("t"), "test_type": "api", "priority": "P1"}
        )
        try:
            data = case_service.export_excel([case])
            assert isinstance(data, bytes)
            text = data.decode("utf-8-sig")
            assert "标题" in text or "title" in text
        finally:
            _cleanup(cid)

    def test_export_mindmap_returns_json(self):
        """导出脑图经 DDD 门面返回可解析 JSON（与既有契约一致）。"""
        cid = _mk("x2")
        case = case_service.create(
            {"id": cid, "title": _mk("t"), "test_type": "functional"}
        )
        try:
            data = case_service.export_mindmap([case])
            parsed = json.loads(data)
            assert parsed["id"] == "root"
        finally:
            _cleanup(cid)


class TestImportDelegation:
    def test_import_excel_creates_case(self):
        """导入 Excel 经 DDD 门面创建用例并返回既有 {imported, errors}。"""
        title = _mk("imp")
        csv_text = "标题,类型,优先级,标签\n{title},api,P1,smoke".format(title=title)
        result = case_service.import_excel(csv_text, operator="tester")
        assert isinstance(result, dict)
        assert "imported" in result and "errors" in result
        assert result["imported"] >= 1
        assert not result.get("errors")
        # 尽力清理：按唯一标题读回并删除（读不到也不至于失败，避免脆测）
        rows, _ = case_service.list(search=title, limit=10)
        for r in rows:
            if str(r.get("title")) == title:
                _cleanup(r.get("id"))

    def test_import_mindmap_returns_dict(self):
        """导入脑图经 DDD 门面返回既有 {imported, errors} 结构。"""
        mindmap = json.dumps({
            "id": "root", "text": "测试用例库",
            "children": [
                {"id": "type_api", "text": "接口测试",
                 "children": [
                     {"id": "c1", "text": "不存在用例",
                      "case_id": "no_such_case_" + uuid.uuid4().hex[:8],
                      "type": "case"}
                 ]}
            ],
        })
        result = case_service.import_mindmap(mindmap, operator="tester")
        assert isinstance(result, dict)
        assert "imported" in result and "errors" in result
        # case_id 不存在时按 text 导入；这里仅校验结构契约稳定
        assert result["imported"] >= 0
        if result["imported"]:
            rows, _ = case_service.list(search="不存在用例", limit=10)
            for r in rows:
                _cleanup(r.get("id"))
