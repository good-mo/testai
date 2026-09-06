# -*- coding: utf-8 -*-
"""app.api_testing.management.imports 子模块（Postman/Swagger 导入，行为不变）。

Repository 下沉说明：
Postman / Swagger 导入编排已下沉到
app.repositories.apitest_repo.ApitestRepo.mgmt_import_from_postman /
mgmt_import_from_swagger，本模块退化为兼容门面。
"""

from app.repositories.apitest_repo import ApitestRepo


def import_from_postman(data: dict) -> dict:
    """从 Postman Collection JSON 导入接口定义（委托 ApitestRepo）。"""
    return ApitestRepo.mgmt_import_from_postman(data)


def import_from_swagger(data: dict) -> dict:
    """从 Swagger/OpenAPI JSON 导入接口定义（委托 ApitestRepo）。"""
    return ApitestRepo.mgmt_import_from_swagger(data)
