# app/core/bootstrap.py
"""应用启动引导逻辑（Phase D 瘦身：从 main.py 拆出的启动初始化）。

职责：
  - 应用启动时的种子数据初始化（幂等，保证首启有可展示数据）；
  - RSA 密钥预热等启动准备。

main.py 仅保留应用装配（路由 include / 中间件 / 静态资源 / SPA 回退），
业务初始化逻辑统一收口在本模块，便于单独维护与测试。
"""

import os

from app.logging_config import get_logger

logger = get_logger(__name__)


def _scripts_dir() -> str:
    """定位仓库 scripts/ 目录（bootstrap.py 位于 app/core/ 下）。"""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "scripts",
    )


def _load_script_module(module_name: str, file_name: str):
    """通过 importlib 从 scripts/ 目录加载种子脚本模块。

    返回模块对象；加载失败返回 None（调用方按幂等容错处理）。
    """
    import importlib.util

    scripts_dir = _scripts_dir()
    spec = importlib.util.spec_from_file_location(
        module_name, os.path.join(scripts_dir, file_name)
    )
    if spec is None or spec.loader is None:
        logger.warning("种子数据: 无法加载 %s", file_name)
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def init_seed_data() -> None:
    """应用启动时初始化基础种子数据（幂等操作）。

    确保缺陷管理、组织/项目/用户等基础模块在首次部署后有可展示的数据。
    此函数在启动时同步执行，所有操作均为幂等写入，重复调用不会产生脏数据。
    """
    try:
        # 1. 组织/用户/项目（经四层 Service 收口）
        from app.services.organization_service import organization_service
        result = organization_service.seed_tenant_data()
        logger.info(
            "种子数据-组织/项目: 组织 %d 个, 项目 %d 个",
            len(result.get("organizations", [])),
            len(result.get("projects", [])),
        )
    except Exception as e:
        logger.warning("种子数据-组织/项目初始化失败: %s", e)

    try:
        # 2. 缺陷数据（幂等）
        from app.repositories.defect_repo import DefectRepo as _DefectRepo
        list_defects = _DefectRepo.list
        existing = list_defects(limit=1)
        if existing:
            logger.info("种子数据-缺陷: 已存在 %d 条，跳过", len(existing))
        else:
            seed_defects()
    except Exception as e:
        logger.warning("种子数据-缺陷初始化失败: %s", e)

    try:
        # 3. 功能用例数据（幂等，缺失才插入）
        from app.repositories.case_repo import CaseRepo
        if CaseRepo.count_cases() > 0:
            logger.info("种子数据-功能用例: 已存在 %d 条，跳过", CaseRepo.count_cases())
        else:
            seed_functional_cases()
    except Exception as e:
        logger.warning("种子数据-功能用例初始化失败: %s", e)

    try:
        # 4. 测试计划与接口定义（幂等，缺失才插入）
        from app.services.test_plan_service import test_plan_service
        if test_plan_service.count_plans() == 0:
            seed_plans_and_definitions()
    except Exception as e:
        logger.warning("种子数据-测试计划/接口定义初始化失败: %s", e)

    try:
        # 5. 全量业务数据（幂等：接口测试/API测试/环境/数据工厂等）
        seed_full_data()
    except Exception as e:
        logger.warning("种子数据-全量业务数据初始化失败: %s", e)


def seed_functional_cases() -> None:
    """通过 importlib 加载 scripts/seed_demo_data.py 并执行功能用例种子插入。

    与缺陷/组织等种子数据保持一致，在应用启动时自动初始化一批功能用例，
    确保功能用例（featureCase）界面在首次部署后即可展示数据。
    """
    mod = _load_script_module("seed_demo_data", "seed_demo_data.py")
    if mod is None:
        return
    stats = mod.seed_cases()
    logger.info(
        "种子数据-功能用例: 插入 %d 条, 跳过 %d 条",
        stats.get("inserted", 0),
        stats.get("skipped", 0),
    )


def seed_plans_and_definitions() -> None:
    """通过 importlib 加载 scripts/seed_demo_data.py 并执行测试计划和接口定义种子插入。"""
    mod = _load_script_module("seed_demo_data", "seed_demo_data.py")
    if mod is None:
        return
    stats = mod.seed_plans()
    logger.info(
        "种子数据-测试计划: 插入 %d 条, 跳过 %d 条",
        stats.get("inserted", 0),
        stats.get("skipped", 0),
    )
    stats = mod.seed_definitions()
    logger.info(
        "种子数据-接口定义: 插入 %d 条, 跳过 %d 条",
        stats.get("inserted", 0),
        stats.get("skipped", 0),
    )


def seed_full_data() -> None:
    """通过 importlib 加载 scripts/seed_all_data.py 并执行全量业务数据种子插入。"""
    mod = _load_script_module("seed_all_data", "seed_all_data.py")
    if mod is None:
        return
    mod.seed_projects_and_members()
    mod.seed_case_management()
    mod.seed_defect_comments()
    mod.seed_api_test_data()
    mod.seed_api_testing_data()
    mod.seed_test_plan_data()
    mod.seed_environments_and_alerts()
    mod.seed_data_factory()
    mod.seed_trace_and_runs()
    mod.seed_script_health()
    mod.seed_resource_pools()
    mod.seed_tasks()
    mod.seed_user_groups()
    mod.seed_additional_data()
    logger.info("种子数据-全量业务: 执行完成")


def seed_defects() -> None:
    """通过 importlib 加载 scripts/seed_defects.py 并执行种子数据插入。"""
    mod = _load_script_module("seed_defects", "seed_defects.py")
    if mod is None:
        return
    stats = mod.seed_defects()
    logger.info(
        "种子数据-缺陷: 插入 %d 条, 跳过 %d 条",
        stats.get("inserted", 0),
        stats.get("skipped", 0),
    )


def preheat_rsa_keys() -> None:
    """预热 RSA 密钥：登录接口首次调用无需现场生成，避免首次登录卡顿。"""
    from app.auth.store import _ensure_rsa_keys
    _ensure_rsa_keys()


__all__ = [
    "init_seed_data",
    "seed_defects",
    "seed_functional_cases",
    "seed_full_data",
    "seed_plans_and_definitions",
    "preheat_rsa_keys",
]
