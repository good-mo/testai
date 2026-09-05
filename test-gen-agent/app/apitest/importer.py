# app/apitest/importer.py
"""接口导入模块（兼容门面）。

Repository 下沉说明：
Postman / Swagger / HAR 导入解析与建定义逻辑已下沉到
app.repositories.apitest_repo.ApitestRepo（L3 Repository 层），本模块退化为
兼容门面，直接委托 ApitestRepo，保证对外行为零回归。
"""
from typing import Any, Dict

from app.repositories.apitest_repo import ApitestRepo


def import_postman(content: str, project_id: str = "") -> Dict[str, Any]:
    """从 Postman Collection JSON 导入接口定义（委托 ApitestRepo）。"""
    return ApitestRepo.import_postman(content, project_id)


def import_swagger(content: str, project_id: str = "") -> Dict[str, Any]:
    """从 Swagger 2.0 / OpenAPI 3.x JSON 导入接口定义（委托 ApitestRepo）。"""
    return ApitestRepo.import_swagger(content, project_id)


def import_har(content: str, project_id: str = "") -> Dict[str, Any]:
    """从 HAR (HTTP Archive) 文件导入接口定义（委托 ApitestRepo）。"""
    return ApitestRepo.import_har(content, project_id)


def import_content(content: str, format: str = "auto",
                   project_id: str = "") -> Dict[str, Any]:
    """自动识别格式导入（委托 ApitestRepo）。"""
    return ApitestRepo.import_content(content, format, project_id)
