"""
完整业务流程测试（test_full_business_flow.py）
============================================
从前端界面出发，按照完整的业务流程走一遍所有界面功能。

覆盖界面和业务流程：
一、登录 → 工作台 → 项目概览 → 我的用例/缺陷/计划
二、功能用例管理：创建模块 → 创建用例 → 查看详情 → 编辑 → 软删除 → 回收站 → 恢复
三、接口测试-接口定义：创建模块 → 创建接口 → 查看 → 编辑 → 删除
四、接口测试-接口用例：创建用例 → 关联接口 → 查看 → 编辑 → 删除
五、接口测试-场景编排：创建场景 → 添加步骤 → 查看 → 编辑 → 删除
六、接口测试-Mock：创建 Mock → 查看 → 编辑 → 删除
七、接口测试-调试：执行接口调试
八、用例评审：创建评审 → 关联用例 → 查看详情
九、测试计划：创建计划 → 关联用例 → 查看详情 → 归档
十、缺陷管理：创建缺陷 → 查看 → 编辑 → 软删除 → 回收站
十一、项目设置：基本信息/成员/版本/文件/环境
十二、系统设置：用户/组织/参数/资源池
十三、任务中心
十四、AI用例生成
十五、报告中心
"""
import os
import sys
import uuid

sys.path.insert(0, '/workspace')
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "local")

from fastapi.testclient import TestClient

PREFIX = "BFLOW-"
PROJECT_ID = "project-demo"

def _data(resp):
    """提取响应 data 字段。"""
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body

def _unique(prefix=""):
    """生成唯一名称。"""
    return f"{PREFIX}{prefix}-{uuid.uuid4().hex[:8]}"

def main():
    from app.main import app
    with TestClient(app) as client:
        # 1. 登录
        r = client.post("/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, f"登录失败: {r.text}"
        session = r.json()["data"]
        client.headers.update({
            "X-AUTH-TOKEN": session["sessionId"],
            "CSRF-TOKEN": session["csrfToken"],
        })

        results = []
        failures = []

        def test(module, test_fn):
            try:
                test_fn(client)
                results.append(f"✅ {module}")
                print(f"✅ {module}")
            except Exception as e:
                failures.append((module, str(e)))
                results.append(f"❌ {module}: {e}")
                print(f"❌ {module}: {e}")

        # ═══════════════════════════════════════════════
        # 一、登录流程
        # ═══════════════════════════════════════════════
        def test_login_flow(client):
            """登录界面 → 认证方式 → 登录 → 获取个人信息。"""
            # 获取认证方式列表
            r = client.get("/authentication/get-list")
            assert r.status_code == 200, f"获取认证方式失败: {r.text}"
            auth_list = _data(r)
            assert auth_list is not None

            # 获取公钥
            r = client.get("/get-key")
            assert r.status_code == 200, f"获取公钥失败: {r.text}"
            assert _data(r) is not None

            # 登录状态检查
            r = client.get("/is-login")
            assert r.status_code == 200, f"登录状态检查失败: {r.text}"

            # 获取个人信息
            r = client.get("/personal/get")
            assert r.status_code == 200, f"获取个人信息失败: {r.text}"
            assert _data(r) is not None

            # 获取菜单列表
            r = client.post("/api/user/menu", json={})
            assert r.status_code == 200, f"获取菜单列表失败: {r.text}"
            assert _data(r) is not None

            # 获取系统版本
            r = client.get("/system/version/current")
            assert r.status_code == 200, f"获取系统版本失败: {r.text}"

            # 获取本地配置
            r = client.get("/user/local/config/get")
            assert r.status_code == 200, f"获取本地配置失败: {r.text}"

            # API Key 列表
            r = client.get("/user/api/key/list")
            assert r.status_code == 200, f"获取API Key列表失败: {r.text}"
        test("登录流程", test_login_flow)

        # ═══════════════════════════════════════════════
        # 二、工作台
        # ═══════════════════════════════════════════════
        def test_workbench_flow(client):
            """工作台：首页 → 待办 → 我关注的 → 我创建的。"""
            # 首页-项目概览
            r = client.post("/dashboard/project_view", json={})
            assert r.status_code == 200, f"项目概览失败: {r.text}"
            assert _data(r) is not None

            # 首页-用例数量
            r = client.post("/dashboard/case_count", json={})
            assert r.status_code == 200, f"用例数量失败: {r.text}"

            # 首页-缺陷数量
            r = client.post("/dashboard/bug_count", json={})
            assert r.status_code == 200, f"缺陷数量失败: {r.text}"

            # 首页-接口数量
            r = client.post("/dashboard/api_count", json={})
            assert r.status_code == 200, f"接口数量失败: {r.text}"

            # 首页-接口用例数量
            r = client.post("/dashboard/api_case_count", json={})
            assert r.status_code == 200, f"接口用例数量失败: {r.text}"

            # 首页-场景数量
            r = client.post("/dashboard/scenario_count", json={})
            assert r.status_code == 200, f"场景数量失败: {r.text}"

            # 首页-测试计划数量
            r = client.post("/dashboard/plan_view", json={})
            assert r.status_code == 200, f"测试计划数量失败: {r.text}"

            # 首页-待我评审
            r = client.post("/dashboard/reviewing_by_me", json={})
            assert r.status_code == 200, f"待我评审失败: {r.text}"

            # 待办-测试计划
            r = client.post("/dashboard/todo/plan/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"待办-测试计划失败: {r.text}"

            # 待办-用例评审
            r = client.post("/dashboard/todo/review/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"待办-用例评审失败: {r.text}"

            # 待办-缺陷
            r = client.post("/dashboard/todo/bug/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"待办-缺陷失败: {r.text}"

            # 我创建的
            r = client.post("/dashboard/create_by_me", json={})
            assert r.status_code == 200, f"我创建的失败: {r.text}"

            # 我的用例列表
            r = client.post("/dashboard/my/functional/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"我的用例失败: {r.text}"
            assert "list" in _data(r)

            # 我的缺陷列表
            r = client.post("/dashboard/my/bug/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"我的缺陷失败: {r.text}"

            # 我的接口用例
            r = client.post("/dashboard/my/api/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"我的接口用例失败: {r.text}"

            # 我的场景
            r = client.post("/dashboard/my/scenario/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"我的场景失败: {r.text}"

            # 我的测试计划
            r = client.post("/dashboard/my/plan/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"我的测试计划失败: {r.text}"

            # 我的用例评审
            r = client.post("/dashboard/my/review/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"我的用例评审失败: {r.text}"

            # 布局获取
            r = client.get("/dashboard/layout/get")
            assert r.status_code == 200, f"布局获取失败: {r.text}"
        test("工作台业务流程", test_workbench_flow)

        # ═══════════════════════════════════════════════
        # 三、功能用例管理 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_functional_case_flow(client):
            """功能用例：创建模块 → 创建用例 → 查看详情 → 编辑 → 软删除 → 回收站 → 恢复 → 彻底删除。"""
            # 1. 获取模块树
            r = client.get("/functional/case/module/tree")
            assert r.status_code == 200, f"获取模块树失败: {r.text}"

            # 2. 创建模块
            module_name = _unique("模块")
            r = client.post("/functional/case/module/add", json={
                "name": module_name,
                "parentId": "root",
                "projectId": PROJECT_ID
            })
            assert r.status_code == 200, f"创建模块失败: {r.text}"
            module_id = None
            mdata = _data(r)
            if isinstance(mdata, dict):
                module_id = mdata.get("id")
            if not module_id and isinstance(mdata, list) and mdata:
                module_id = mdata[0].get("id") if isinstance(mdata[0], dict) else None
            # 如果没返回 ID，从模块树中查找
            if not module_id:
                r2 = client.get("/functional/case/module/tree")
                for mod in (_data(r2) or []):
                    if mod.get("name") == module_name:
                        module_id = mod.get("id")
                        break
            assert module_id, f"创建模块未返回 ID: {r.text}"

            # 3. 创建功能用例
            case_name = _unique("用例")
            r = client.post("/functional/case/add", json={
                "name": case_name,
                "description": "业务流程测试用例",
                "priority": "P1",
                "status": "open",
                "moduleId": module_id,
                "testType": "functional",
                "projectId": PROJECT_ID
            })
            assert r.status_code == 200, f"创建功能用例失败: {r.text}"
            case_data = _data(r)
            case_id = case_data.get("id") if isinstance(case_data, dict) else None
            assert case_id, f"创建用例未返回 ID: {r.text}"

            # 4. 查看用例详情
            r = client.get(f"/functional/case/detail/{case_id}")
            assert r.status_code == 200, f"获取用例详情失败: {r.text}"
            detail = _data(r)
            assert detail is not None, "用例详情为空"

            # 5. 用例列表 - 验证用例出现在列表中
            r = client.post("/functional/case/page", json={
                "pageSize": 10, "current": 1, "keyword": ""
            })
            assert r.status_code == 200, f"用例列表失败: {r.text}"
            case_list = _data(r).get("list", [])
            assert any(c.get("id") == case_id for c in case_list), f"用例未出现在列表中: {case_id}"

            # 6. 编辑用例
            r = client.post("/functional/case/update", json={
                "id": case_id,
                "name": case_name + "-改",
                "description": "编辑后的描述",
                "priority": "P2"
            })
            assert r.status_code == 200, f"编辑用例失败: {r.text}"

            # 7. 验证编辑后内容
            r = client.get(f"/functional/case/detail/{case_id}")
            assert r.status_code == 200, f"获取编辑后用例失败: {r.text}"
            updated = _data(r)
            assert updated.get("title") == case_name + "-改" or updated.get("name") == case_name + "-改", \
                f"编辑未生效: {updated}"

            # 8. 获取默认模板字段
            r = client.get(f"/functional/case/default/template/field/{PROJECT_ID}")
            assert r.status_code == 200, f"获取默认模板字段失败: {r.text}"

            # 9. 获取自定义字段
            r = client.get(f"/functional/case/custom/field/{PROJECT_ID}")
            assert r.status_code == 200, f"获取自定义字段失败: {r.text}"

            # 10. 获取脑图数据
            r = client.get("/functional/mind/case/list")
            assert r.status_code == 200, f"获取脑图数据失败: {r.text}"

            # 11. 软删除用例
            r = client.post("/functional/case/delete", json={"id": case_id, "deleteAll": False})
            assert r.status_code == 200, f"软删除用例失败: {r.text}"

            # 12. 验证删除后不可获取（应404或不在列表中）
            r = client.get(f"/functional/case/detail/{case_id}")
            assert r.status_code in [200, 404], f"删除后状态异常: {r.status_code}"
            if r.status_code == 200:
                # 如果还能获取，检查是否标记为删除
                d = _data(r)
                if isinstance(d, dict):
                    assert not d.get("deleted"), f"删除后仍然可获取: {r.text}"

            # 13. 回收站列表
            r = client.post("/functional/case/trash/page", json={"pageSize": 100, "current": 1})
            assert r.status_code == 200, f"回收站列表失败: {r.text}"
            trash_list = _data(r).get("list", [])
            assert any(c.get("id") == case_id for c in trash_list), f"回收站中未找到已删除用例: {case_id}"

            # 14. 从回收站恢复
            r = client.post("/functional/case/trash/batch/recover", json={"ids": [case_id]})
            assert r.status_code == 200, f"恢复用例失败: {r.text}"

            # 15. 恢复后可以获取
            r = client.get(f"/functional/case/detail/{case_id}")
            assert r.status_code == 200, f"恢复后获取用例失败: {r.text}"

            # 16. 再次软删除用于彻底删除测试
            r = client.post("/functional/case/delete", json={"id": case_id, "deleteAll": False})
            assert r.status_code == 200, f"再次软删除失败: {r.text}"

            # 17. 从回收站彻底删除
            r = client.post("/functional/case/trash/batch/delete", json={"ids": [case_id]})
            assert r.status_code == 200, f"彻底删除用例失败: {r.text}"

            # 18. 删除模块
            r = client.post(f"/functional/case/module/delete/{module_id}")
            assert r.status_code in [200, 404], f"删除模块失败: {r.text}"

            # 19. 验证彻底删除后不可获取
            r = client.get(f"/functional/case/detail/{case_id}")
            assert r.status_code == 404, f"彻底删除后仍可获取: {r.text}"
        test("功能用例管理完整流程", test_functional_case_flow)

        # ═══════════════════════════════════════════════
        # 四、接口定义 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_api_definition_flow(client):
            """接口定义：创建接口 → 查看详情 → 编辑 → 删除 → 回收站 → 恢复。"""
            # 1. 创建接口定义模块
            module_name = _unique("API模块")
            r = client.post("/api/definition/module/add", json={
                "name": module_name,
                "parentId": "root",
                "projectId": PROJECT_ID
            })
            assert r.status_code == 200, f"创建接口模块失败: {r.text}"
            module_data = _data(r)
            module_id = None
            if isinstance(module_data, dict):
                module_id = module_data.get("id")
            if not module_id:
                r2 = client.get("/api/definition/module/tree")
                for mod in (_data(r2) or []):
                    if mod.get("name") == module_name:
                        module_id = mod.get("id")
                        break
            # 模块创建不必须成功返回ID，跳到下一步

            # 2. 获取模块树
            r = client.get("/api/definition/module/tree")
            assert r.status_code == 200, f"获取接口模块树失败: {r.text}"

            # 3. 创建接口定义
            api_name = _unique("接口")
            api_path = f"/api/test/{uuid.uuid4().hex[:8]}"
            r = client.post("/api/definition/add", json={
                "name": api_name,
                "method": "POST",
                "path": api_path,
                "protocol": "HTTP",
                "moduleId": module_id or "root",
                "projectId": PROJECT_ID,
                "description": "接口定义业务流程测试"
            })
            assert r.status_code == 200, f"创建接口定义失败: {r.text}"
            api_data = _data(r)
            api_id = api_data.get("id") if isinstance(api_data, dict) else None
            assert api_id, f"创建接口未返回 ID: {r.text}"

            # 4. 接口定义列表 - 验证接口在列表中
            r = client.post("/api/definition/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"接口定义列表失败: {r.text}"
            api_list = _data(r).get("list", [])
            assert any(a.get("id") == api_id for a in api_list), f"接口未出现在列表中: {api_id}"

            # 5. 获取接口详情
            r = client.post("/api/definition/get-detail", json={"id": api_id})
            assert r.status_code == 200, f"获取接口详情失败: {r.text}"
            assert _data(r) is not None

            # 6. 编辑接口定义
            r = client.post("/api/definition/update", json={
                "id": api_id,
                "name": api_name + "-改",
                "description": "编辑后的接口描述"
            })
            assert r.status_code == 200, f"编辑接口失败: {r.text}"

            # 7. 验证编辑生效
            r = client.post("/api/definition/get-detail", json={"id": api_id})
            assert r.status_code == 200, f"获取编辑后接口失败: {r.text}"
            detail = _data(r)
            if isinstance(detail, dict):
                assert detail.get("name") == api_name + "-改", f"接口编辑未生效: {detail}"

            # 8. 创建接口用例
            api_case_name = _unique("接口用例")
            r = client.post("/api/case/add", json={
                "name": api_case_name,
                "apiDefinitionId": api_id,
                "projectId": PROJECT_ID,
                "priority": "P1",
                "status": "prepare"
            })
            assert r.status_code == 200, f"创建接口用例失败: {r.text}"
            case_data = _data(r)
            api_case_id = case_data.get("id") if isinstance(case_data, dict) else None
            assert api_case_id, f"创建接口用例未返回 ID: {r.text}"

            # 9. 接口用例列表
            r = client.post("/api/case/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"接口用例列表失败: {r.text}"
            case_list = _data(r).get("list", [])
            assert any(c.get("id") == api_case_id for c in case_list), "接口用例未出现在列表中"

            # 10. 获取接口用例详情
            r = client.post("/api/case/get-detail", json={"id": api_case_id})
            assert r.status_code == 200, f"获取接口用例详情失败: {r.text}"

            # 11. 编辑接口用例
            r = client.post("/api/case/update", json={
                "id": api_case_id,
                "name": api_case_name + "-改"
            })
            assert r.status_code == 200, f"编辑接口用例失败: {r.text}"

            # 12. 创建 Mock
            mock_name = _unique("Mock")
            r = client.post("/api/definition/mock/add", json={
                "name": mock_name,
                "apiDefinitionId": api_id,
                "projectId": PROJECT_ID
            })
            assert r.status_code == 200, f"创建Mock失败: {r.text}"
            mock_data = _data(r)
            mock_id = mock_data.get("id") if isinstance(mock_data, dict) else None

            # 13. Mock 列表
            r = client.post("/api/definition/mock/page", json={
                "pageSize": 10, "current": 1, "apiId": api_id
            })
            assert r.status_code == 200, f"Mock列表失败: {r.text}"

            # 14. 获取 Mock 详情
            if mock_id:
                r = client.post("/api/definition/mock/detail", json={"id": mock_id})
                assert r.status_code == 200, f"获取Mock详情失败: {r.text}"

            # 15. 删除接口用例
            r = client.post("/api/case/delete-to-gc", json={"id": api_case_id})
            assert r.status_code == 200, f"删除接口用例失败: {r.text}"

            # 16. 删除接口定义（软删除）
            r = client.post("/api/definition/delete-to-gc", json={"id": api_id})
            assert r.status_code == 200, f"删除接口定义失败: {r.text}"

            # 17. 回收站-接口定义列表
            r = client.post("/api/definition/trash/page", json={"pageSize": 10, "current": 1})
            if r.status_code == 200:
                trash = _data(r).get("list", [])
                # 恢复接口定义
                if any(t.get("id") == api_id for t in trash):
                    r = client.post("/api/definition/recover", json={"id": api_id})
                    assert r.status_code == 200, f"恢复接口失败: {r.text}"

                    # 恢复后验证
                    r = client.post("/api/definition/get-detail", json={"id": api_id})
                    assert r.status_code == 200, f"恢复后获取接口失败: {r.text}"

                    # 再次软删除用于清理
                    r = client.post("/api/definition/delete-to-gc", json={"id": api_id})
                    assert r.status_code == 200, f"再次删除接口失败: {r.text}"
        test("接口定义-接口用例-Mock完整流程", test_api_definition_flow)

        # ═══════════════════════════════════════════════
        # 五、接口场景 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_api_scenario_flow(client):
            """接口场景：创建场景 → 查看详情 → 编辑 → 删除 → 回收站。"""
            # 1. 获取场景模块树
            r = client.get("/api/scenario/module/tree")
            assert r.status_code == 200, f"获取场景模块树失败: {r.text}"

            # 2. 创建场景
            scenario_name = _unique("场景")
            r = client.post("/api/scenario/add", json={
                "name": scenario_name,
                "description": "场景业务流程测试",
                "projectId": PROJECT_ID,
                "moduleId": "root",
                "priority": "P2"
            })
            assert r.status_code == 200, f"创建场景失败: {r.text}"
            sdata = _data(r)
            scenario_id = sdata.get("id") if isinstance(sdata, dict) else None
            assert scenario_id, f"创建场景未返回 ID: {r.text}"

            # 3. 场景列表
            r = client.post("/api/scenario/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"场景列表失败: {r.text}"
            s_list = _data(r).get("list", [])
            assert any(s.get("id") == scenario_id for s in s_list), "场景未出现在列表中"

            # 4. 获取场景详情
            r = client.post("/api/scenario/get", json={"id": scenario_id})
            assert r.status_code == 200, f"获取场景详情失败: {r.text}"
            assert _data(r) is not None

            # 5. 获取场景步骤
            r = client.post("/api/scenario/step/get", json={"id": scenario_id})
            assert r.status_code == 200, f"获取场景步骤失败: {r.text}"

            # 6. 编辑场景
            r = client.post("/api/scenario/update", json={
                "id": scenario_id,
                "name": scenario_name + "-改",
                "description": "编辑后的场景描述"
            })
            assert r.status_code == 200, f"编辑场景失败: {r.text}"

            # 7. 验证编辑生效
            r = client.post("/api/scenario/get", json={"id": scenario_id})
            assert r.status_code == 200, f"获取编辑后场景失败: {r.text}"
            detail = _data(r)
            if isinstance(detail, dict):
                assert detail.get("name") == scenario_name + "-改", f"场景编辑未生效: {detail}"

            # 8. 场景统计
            r = client.post("/api/scenario/statistics", json={"id": scenario_id})
            assert r.status_code == 200, f"场景统计失败: {r.text}"

            # 9. 软删除场景
            r = client.post("/api/scenario/delete-to-gc", json={"id": scenario_id})
            assert r.status_code == 200, f"删除场景失败: {r.text}"

            # 10. 回收站场景列表
            r = client.post("/api/scenario/trash/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"场景回收站列表失败: {r.text}"
            trash = _data(r).get("list", [])
            if any(t.get("id") == scenario_id for t in trash):
                # 恢复场景
                r = client.post("/api/scenario/recover", json={"id": scenario_id})
                assert r.status_code == 200, f"恢复场景失败: {r.text}"

                # 恢复后验证
                r = client.post("/api/scenario/get", json={"id": scenario_id})
                assert r.status_code == 200, f"恢复后获取场景失败: {r.text}"

                # 再次软删除用于清理
                r = client.post("/api/scenario/delete-to-gc", json={"id": scenario_id})
                assert r.status_code == 200, f"再次删除场景失败: {r.text}"
        test("接口场景完整流程", test_api_scenario_flow)

        # ═══════════════════════════════════════════════
        # 六、用例评审 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_case_review_flow(client):
            """用例评审：创建评审 → 获取评审人员 → 查看评审列表 → 查看详情。"""
            # 1. 创建功能用例作为评审对象
            case_name = _unique("评审用例")
            r = client.post("/functional/case/add", json={
                "name": case_name,
                "description": "用于评审的用例",
                "priority": "P1",
                "status": "open"
            })
            assert r.status_code == 200, f"创建评审用例失败: {r.text}"
            case_data = _data(r)
            case_id = case_data.get("id") if isinstance(case_data, dict) else None

            # 2. 获取评审人员列表
            r = client.post("/case/review/user-option", json={})
            assert r.status_code == 200, f"获取评审人员失败: {r.text}"

            # 3. 创建评审
            review_name = _unique("评审")
            r = client.post("/case/review/add", json={
                "name": review_name,
                "description": "评审业务流程测试",
                "projectId": PROJECT_ID,
                "status": "PREPARED",
                "caseList": [{"id": case_id}] if case_id else []
            })
            assert r.status_code == 200, f"创建评审失败: {r.text}"
            rdata = _data(r)
            review_id = rdata.get("id") if isinstance(rdata, dict) else None

            # 4. 评审列表
            r = client.post("/case/review/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"评审列表失败: {r.text}"

            # 5. 获取评审详情
            if review_id:
                r = client.post("/case/review/detail", json={"id": review_id})
                assert r.status_code == 200, f"获取评审详情失败: {r.text}"

                # 6. 评审详情-已关联用例列表
                r = client.post("/case/review/detail/page", json={
                    "reviewId": review_id, "pageSize": 10, "current": 1
                })
                assert r.status_code == 200, f"评审详情用例列表失败: {r.text}"

                # 7. 删除评审
                r = client.post("/case/review/delete", json={"id": review_id})
                assert r.status_code == 200, f"删除评审失败: {r.text}"
        test("用例评审完整流程", test_case_review_flow)

        # ═══════════════════════════════════════════════
        # 七、测试计划 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_test_plan_flow(client):
            """测试计划：创建计划 → 查看列表 → 查看详情 → 统计 → 归档 → 删除。"""
            # 1. 获取测试计划模块树
            r = client.get("/test-plan/module/tree")
            assert r.status_code == 200, f"获取测试计划模块树失败: {r.text}"

            # 2. 创建测试计划
            plan_name = _unique("计划")
            r = client.post("/test-plan/add", json={
                "name": plan_name,
                "description": "测试计划业务流程测试",
                "priority": "P1",
                "projectId": PROJECT_ID,
                "status": "PREPARED"
            })
            assert r.status_code == 200, f"创建测试计划失败: {r.text}"
            pdata = _data(r)
            plan_id = pdata.get("id") if isinstance(pdata, dict) else None
            assert plan_id, f"创建测试计划未返回 ID: {r.text}"

            # 3. 测试计划列表
            r = client.post("/test-plan/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"测试计划列表失败: {r.text}"
            plans = _data(r).get("list", [])
            assert any(p.get("id") == plan_id for p in plans), "测试计划未出现在列表中"

            # 4. 获取测试计划详情
            r = client.get(f"/test-plan/{plan_id}")
            assert r.status_code == 200, f"获取测试计划详情失败: {r.text}"

            # 5. 编辑测试计划
            r = client.post("/test-plan/update", json={
                "id": plan_id,
                "name": plan_name + "-改",
                "description": "编辑后的计划描述"
            })
            assert r.status_code == 200, f"编辑测试计划失败: {r.text}"

            # 6. 验证编辑
            r = client.get(f"/test-plan/{plan_id}")
            assert r.status_code == 200, f"获取编辑后计划失败: {r.text}"
            detail = _data(r)
            if isinstance(detail, dict):
                assert detail.get("name") == plan_name + "-改", "测试计划编辑未生效"

            # 7. 测试计划统计
            r = client.get("/test-plan/statistics")
            assert r.status_code == 200, f"测试计划统计失败: {r.text}"

            # 8. 获取统计数量
            r = client.get("/test-plan/getCount")
            assert r.status_code == 200, f"获取统计数量失败: {r.text}"

            # 9. 测试计划模块计数
            r = client.get("/test-plan/module/count")
            assert r.status_code == 200, f"测试计划模块计数失败: {r.text}"

            # 10. 测试计划列表（无分页）
            r = client.get("/test-plan/test-plan-list")
            assert r.status_code == 200, f"获取测试计划列表失败: {r.text}"

            # 11. 归档测试计划
            r = client.post("/test-plan/archived", json={"id": plan_id})
            assert r.status_code == 200, f"归档测试计划失败: {r.text}"

            # 12. 删除测试计划
            r = client.post("/test-plan/delete", json={"id": plan_id})
            assert r.status_code == 200, f"删除测试计划失败: {r.text}"

            # 13. 验证删除后详情
            r = client.get(f"/test-plan/{plan_id}")
            assert r.status_code in [200, 404], f"删除后获取计划状态异常: {r.status_code}"
        test("测试计划完整流程", test_test_plan_flow)

        # ═══════════════════════════════════════════════
        # 八、缺陷管理 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_bug_management_flow(client):
            """缺陷管理：创建缺陷 → 列表 → 详情 → 编辑 → 软删除 → 回收站 → 恢复 → 彻底删除。"""
            # 1. 创建缺陷
            bug_name = _unique("缺陷")
            r = client.post("/bug/add", json={
                "title": bug_name,
                "description": "缺陷业务流程测试",
                "status": "open",
                "severity": "major",
                "platform": "Local"
            })
            assert r.status_code == 200, f"创建缺陷失败: {r.text}"
            bdata = _data(r)
            bug_id = bdata.get("id") if isinstance(bdata, dict) else None
            assert bug_id, f"创建缺陷未返回 ID: {r.text}"

            # 2. 缺陷列表
            r = client.post("/bug/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"缺陷列表失败: {r.text}"
            bugs = _data(r).get("list", [])
            assert any(b.get("id") == bug_id for b in bugs), "缺陷未出现在列表中"

            # 3. 获取缺陷详情
            r = client.get(f"/bug/get/{bug_id}")
            assert r.status_code == 200, f"获取缺陷详情失败: {r.text}"

            # 4. 编辑缺陷
            r = client.post("/bug/update", json={
                "id": bug_id,
                "title": bug_name + "-改",
                "status": "in_progress"
            })
            assert r.status_code == 200, f"编辑缺陷失败: {r.text}"

            # 5. 验证编辑
            r = client.get(f"/bug/get/{bug_id}")
            assert r.status_code == 200, f"获取编辑后缺陷失败: {r.text}"

            # 6. 获取缺陷模板
            r = client.get("/bug/template/detail")
            assert r.status_code == 200, f"获取缺陷模板失败: {r.text}"

            # 7. 获取自定义字段表头
            r = client.get("/bug/header/custom-field/")
            if r.status_code != 200:
                r = client.get("/bug/header/custom-field")
                assert r.status_code == 200, f"获取缺陷自定义字段失败: {r.text}"

            # 8. 获取缺陷模板选项
            r = client.get("/bug/template/option")
            assert r.status_code == 200, f"获取缺陷模板选项失败: {r.text}"

            # 9. 软删除缺陷
            r = client.post("/bug/delete", json={"id": bug_id})
            assert r.status_code == 200, f"删除缺陷失败: {r.text}"

            # 10. 回收站列表
            r = client.post("/bug/trash/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"缺陷回收站列表失败: {r.text}"
            trash = _data(r).get("list", [])
            if any(t.get("id") == bug_id for t in trash):
                # 恢复
                r = client.post("/bug/trash/recover", json={"id": bug_id})
                assert r.status_code in [200, 404], f"恢复缺陷失败: {r.text}"

                # 验证恢复后
                r = client.get(f"/bug/get/{bug_id}")
                assert r.status_code == 200, f"恢复后获取缺陷失败: {r.text}"

                # 再次软删除用于清理
                r = client.post("/bug/delete", json={"id": bug_id})
                assert r.status_code == 200, f"再次删除缺陷失败: {r.text}"

                # 彻底删除
                r = client.post("/bug/trash/delete", json={"id": bug_id})
                assert r.status_code in [200, 404], f"彻底删除缺陷失败: {r.text}"
        test("缺陷管理完整流程", test_bug_management_flow)

        # ═══════════════════════════════════════════════
        # 九、接口测试-调试 - 完整流程
        # ═══════════════════════════════════════════════
        def test_api_debug_flow(client):
            """接口调试：添加调试 → 查看详情 → 更新 → 删除。"""
            # 1. 添加调试
            debug_name = _unique("调试")
            r = client.post("/api/debug/add", json={
                "name": debug_name,
                "method": "GET",
                "path": "/api/apitest/stats",
                "projectId": PROJECT_ID
            })
            assert r.status_code == 200, f"添加调试失败: {r.text}"
            ddata = _data(r)
            debug_id = ddata.get("id") if isinstance(ddata, dict) else None

            # 2. 获取调试详情
            if debug_id:
                r = client.post("/api/debug/get", json={"id": debug_id})
                assert r.status_code == 200, f"获取调试详情失败: {r.text}"

                # 3. 更新调试
                r = client.post("/api/debug/update", json={
                    "id": debug_id,
                    "name": debug_name + "-改"
                })
                assert r.status_code == 200, f"更新调试失败: {r.text}"

                # 4. 删除调试
                r = client.post("/api/debug/delete", json={"id": debug_id})
                assert r.status_code == 200, f"删除调试失败: {r.text}"

            # 5. 获取调试模块树
            r = client.get("/api/debug/module/tree")
            assert r.status_code == 200, f"获取调试模块树失败: {r.text}"

            # 6. 获取模块统计
            r = client.post("/api/debug/module/count", json={})
            assert r.status_code == 200, f"获取调试模块统计失败: {r.text}"
        test("接口调试完整流程", test_api_debug_flow)

        # ═══════════════════════════════════════════════
        # 十、项目管理 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_project_management_flow(client):
            """项目设置：基本信息 → 成员 → 版本 → 文件管理 → 环境管理 → 消息管理。"""
            # 1. 项目列表
            r = client.get("/project/list/options")
            assert r.status_code == 200, f"项目列表失败: {r.text}"
            project_list = _data(r)
            project_id = None
            if isinstance(project_list, list) and project_list:
                project_id = project_list[0].get("id") or project_list[0].get("value")
            elif isinstance(project_list, dict):
                project_id = project_list.get("id") or project_list.get("value")

            # 2. 切换项目
            if project_id:
                r = client.post("/project/switch", json={"id": project_id})
                assert r.status_code == 200, f"切换项目失败: {r.text}"

            # 3. 获取项目模块信息
            if project_id:
                r = client.get(f"/system/get/{project_id}")
                assert r.status_code == 200, f"获取项目模块信息失败: {r.text}"

            # 4. 项目成员列表
            r = client.post("/project/member/list", json={"pageSize": 10, "current": 1})
            if r.status_code != 200:
                r = client.get("/project/member/list")
                assert r.status_code == 200, f"获取项目成员失败: {r.text}"

            # 5. 项目版本列表
            r = client.get("/project/version/list")
            assert r.status_code == 200, f"获取项目版本失败: {r.text}"

            # 6. 文件管理-模块树
            r = client.get("/project/file-module/tree")
            assert r.status_code == 200, f"获取文件模块树失败: {r.text}"

            # 7. 文件列表
            r = client.post("/project/file/page", json={"pageSize": 10, "current": 1})
            if r.status_code != 200:
                r = client.get("/project/file/page")
                assert r.status_code == 200, f"获取文件列表失败: {r.text}"

            # 8. 环境管理-获取环境列表
            r = client.get("/project/environment/list")
            assert r.status_code == 200, f"获取环境列表失败: {r.text}"

            # 9. 获取所有全局参数
            r = client.get("/project/global/params/get/default")
            assert r.status_code == 200, f"获取全局参数失败: {r.text}"

            # 10. 消息管理-机器人列表
            r = client.get("/project/robot/list")
            assert r.status_code == 200, f"获取机器人列表失败: {r.text}"

            # 11. 消息-任务获取
            r = client.get("/notice/message/task/get")
            assert r.status_code == 200, f"获取消息任务失败: {r.text}"

            # 12. 公共脚本-自定义函数列表
            r = client.post("/project/custom/func/page", json={"pageSize": 10, "current": 1})
            if r.status_code != 200:
                r = client.get("/project/custom/func/page")
                assert r.status_code == 200, f"获取自定义函数失败: {r.text}"

            # 13. 项目日志
            r = client.post("/project/log/list", json={"pageSize": 10, "current": 1})
            if r.status_code != 200:
                r = client.get("/project/log/list")
                assert r.status_code == 200, f"获取项目日志失败: {r.text}"
        test("项目管理完整流程", test_project_management_flow)

        # ═══════════════════════════════════════════════
        # 十一、系统设置 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_system_settings_flow(client):
            """系统设置：用户 → 用户组 → 组织/项目 → 参数 → 资源池 → 日志。"""
            # 1. 用户列表
            r = client.post("/system/user/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"系统用户列表失败: {r.text}"

            # 2. 创建用户
            username = _unique("user").lower()
            r = client.post("/system/user/add", json={
                "username": username,
                "email": f"{username}@test.com",
                "password": "Test@123456"
            })
            assert r.status_code == 200, f"创建用户失败: {r.text}"
            udata = _data(r)
            user_id = udata.get("id") if isinstance(udata, dict) else None

            # 3. 用户组列表
            r = client.get("/user/role/global/list")
            assert r.status_code == 200, f"获取用户组列表失败: {r.text}"

            # 4. 组织列表
            r = client.post("/system/organization/list", json={"pageSize": 10, "current": 1})
            if r.status_code != 200:
                r = client.get("/system/organization/list")
                assert r.status_code == 200, f"获取组织列表失败: {r.text}"

            # 5. 系统参数-获取基础信息
            r = client.get("/system/parameter/get/base-info")
            assert r.status_code == 200, f"获取系统基础信息失败: {r.text}"

            # 6. 获取界面配置
            r = client.get("/display/info")
            assert r.status_code == 200, f"获取界面配置失败: {r.text}"

            # 7. 认证源列表
            r = client.post("/system/authsource/list", json={})
            assert r.status_code == 200, f"获取认证源列表失败: {r.text}"

            # 8. 资源池列表
            r = client.post("/test/resource/pool/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"获取资源池列表失败: {r.text}"

            # 9. 系统日志
            r = client.post("/operation/log/list", json={"pageSize": 10, "current": 1})
            if r.status_code != 200:
                r = client.get("/operation/log/list")
                assert r.status_code == 200, f"获取系统日志失败: {r.text}"

            # 10. 删除用户
            if user_id:
                r = client.post("/system/user/delete", json={"id": user_id})
                assert r.status_code == 200, f"删除用户失败: {r.text}"
        test("系统设置完整流程", test_system_settings_flow)

        # ═══════════════════════════════════════════════
        # 十二、组织设置 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_org_settings_flow(client):
            """组织设置：成员 → 项目 → 模板 → 服务集成。"""
            # 1. 组织成员列表
            r = client.get("/organization/member/list")
            assert r.status_code == 200, f"获取组织成员失败: {r.text}"

            # 2. 组织项目列表
            r = client.post("/organization/project/list", json={"pageSize": 10, "current": 1})
            if r.status_code != 200:
                r = client.get("/organization/project/list")
                assert r.status_code == 200, f"获取组织项目失败: {r.text}"

            # 3. 组织模板列表
            r = client.get("/organization/template/list")
            assert r.status_code == 200, f"获取组织模板列表失败: {r.text}"

            # 4. 组织日志
            r = client.post("/organization/log/list", json={"pageSize": 10, "current": 1})
            if r.status_code != 200:
                r = client.get("/organization/log/list")
                assert r.status_code == 200, f"获取组织日志失败: {r.text}"

            # 5. 服务集成列表
            r = client.get("/service/integration/list")
            if r.status_code != 200:
                r = client.post("/service/integration/list", json={})
                assert r.status_code == 200, f"获取服务集成列表失败: {r.text}"
        test("组织设置完整流程", test_org_settings_flow)

        # ═══════════════════════════════════════════════
        # 十三、任务中心 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_task_center_flow(client):
            """任务中心：项目/组织/系统三级任务。"""
            # 1. 项目任务-执行任务分页
            r = client.post("/project/task-center/exec-task/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"项目任务列表失败: {r.text}"

            # 2. 项目任务-定时任务分页
            r = client.post("/project/task-center/schedule/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"项目定时任务列表失败: {r.text}"

            # 3. 组织任务
            r = client.post("/organization/task-center/exec-task/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"组织任务列表失败: {r.text}"

            # 4. 系统任务
            r = client.post("/system/task-center/exec-task/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"系统任务列表失败: {r.text}"

            # 5. 系统定时任务
            r = client.post("/system/task-center/schedule/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"系统定时任务列表失败: {r.text}"
        test("任务中心完整流程", test_task_center_flow)

        # ═══════════════════════════════════════════════
        # 十四、AI 用例生成 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_ai_case_gen_flow(client):
            """AI用例生成：测试类型 → 低代码生成 → 项目批量生成。"""
            # 1. 测试类型列表
            r = client.get("/api/test-types")
            assert r.status_code == 200, f"获取测试类型失败: {r.text}"
            test_types = _data(r)
            assert test_types is not None

            # 2. 低代码生成
            r = client.post("/api/insights/lowcode", json={"description": "生成一个登录功能测试用例"})
            assert r.status_code == 200, f"低代码生成失败: {r.text}"

            # 3. 技能路径
            r = client.post("/api/insights/skill-path", json={})
            if r.status_code != 200:
                r = client.get("/api/insights/skill-path")
                assert r.status_code == 200, f"获取技能路径失败: {r.text}"

            # 4. 任务列表
            r = client.get("/api/tasks")
            assert r.status_code == 200, f"获取任务列表失败: {r.text}"

            # 5. 项目批量生成（空目录返回错误是正常的）
            r = client.post("/api/projects/scan", json={"directory": "/tmp/nonexistent-dir-12345"})
            assert r.status_code in [200, 400, 404], f"项目扫描请求异常: {r.status_code}"
        test("AI用例生成完整流程", test_ai_case_gen_flow)

        # ═══════════════════════════════════════════════
        # 十五、报告中心 - 完整业务流程
        # ═══════════════════════════════════════════════
        def test_report_center_flow(client):
            """报告中心：测试计划报告 → 接口用例报告 → 场景报告 → 导出。"""
            # 1. 测试计划报告列表
            r = client.post("/test-plan/report/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"测试计划报告列表失败: {r.text}"

            # 2. 接口用例报告列表
            r = client.post("/api/report/case/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"接口用例报告列表失败: {r.text}"

            # 3. 场景报告列表
            r = client.post("/api/report/scenario/page", json={"pageSize": 10, "current": 1})
            assert r.status_code == 200, f"场景报告列表失败: {r.text}"

            # 4. 报告导出参数
            r = client.post("/test-plan/report/batch-param", json={"ids": []})
            assert r.status_code == 200, f"报告导出参数失败: {r.text}"

            # 5. 接口用例报告导出
            r = client.post("/api/report/case/batch-param", json={"ids": []})
            assert r.status_code == 200, f"接口报告导出参数失败: {r.text}"

            # 6. 场景报告导出参数
            r = client.post("/api/report/scenario/batch-param", json={"ids": []})
            assert r.status_code == 200, f"场景报告导出参数失败: {r.text}"
        test("报告中心完整流程", test_report_center_flow)

        # ═══════════════════════════════════════════════
        # 十六、接口测试-环境管理
        # ═══════════════════════════════════════════════
        def test_api_environment_flow(client):
            """接口测试-环境管理：创建环境 → 列表 → 更新 → 删除。"""
            # 1. 获取环境列表
            r = client.get("/api/test/env-list")
            assert r.status_code == 200, f"获取接口测试环境列表失败: {r.text}"

            # 2. 创建环境（apitester模块）
            env_name = _unique("环境")
            r = client.post("/api/apitest/environments", json={
                "name": env_name,
                "description": "接口测试环境",
                "baseUrl": "http://localhost:8000"
            })
            if r.status_code == 200:
                edata = _data(r)
                env_id = edata.get("id") if isinstance(edata, dict) else None
                if env_id:
                    # 获取环境详情
                    r = client.get(f"/api/apitest/environments/{env_id}")
                    assert r.status_code == 200, f"获取环境详情失败: {r.text}"

                    # 更新环境
                    r = client.put(f"/api/apitest/environments/{env_id}", json={
                        "name": env_name + "-改"
                    })
                    assert r.status_code == 200, f"更新环境失败: {r.text}"

                    # 删除环境
                    r = client.delete(f"/api/apitest/environments/{env_id}")
                    assert r.status_code == 200, f"删除环境失败: {r.text}"

            # 3. 获取环境详情（apitester模块）
            r = client.get("/api/test/environment")
            if r.status_code != 200:
                r = client.post("/api/test/environment", json={})
                assert r.status_code in [200, 404], f"获取环境详情失败: {r.status_code}"
        test("接口测试环境管理流程", test_api_environment_flow)

        # ═══════════════════════════════════════════════
        # 十七、接口报告
        # ═══════════════════════════════════════════════
        def test_api_report_flow(client):
            """接口报告：查看用例报告和场景报告。"""
            # 1. 接口用例报告详情（获取空报告应该返回错误或空）
            r = client.get("/api/report/case/get/nonexistent")
            assert r.status_code in [200, 404], f"获取接口用例报告异常: {r.status_code}"

            # 2. 场景报告详情
            r = client.get("/api/report/scenario/get/nonexistent")
            assert r.status_code in [200, 404], f"获取场景报告异常: {r.status_code}"

            # 3. 报告分享生成
            r = client.post("/api/report/share/gen", json={"reportId": "nonexistent", "reportType": "CASE"})
            assert r.status_code in [200, 404, 400], f"生成报告分享异常: {r.status_code}"

            # 4. 报告分享获取
            r = client.get("/api/report/share/get")
            assert r.status_code in [200, 400], f"获取报告分享异常: {r.status_code}"
        test("接口报告流程", test_api_report_flow)

        # ═══════════════════════════════════════════════
        # 十八、测试计划详情 - 功能用例/接口用例/场景关联
        # ═══════════════════════════════════════════════
        def test_test_plan_detail_flow(client):
            """测试计划详情：功能用例/接口用例/场景列表、执行历史。"""
            # 1. 创建测试计划
            plan_name = _unique("计划详情")
            r = client.post("/test-plan/add", json={
                "name": plan_name,
                "description": "计划详情流程测试",
                "priority": "P2"
            })
            assert r.status_code == 200, f"创建测试计划失败: {r.text}"
            pdata = _data(r)
            plan_id = pdata.get("id") if isinstance(pdata, dict) else None

            if plan_id:
                # 2. 计划详情-功能用例列表
                r = client.post("/test-plan/functional/case/page", json={
                    "pageSize": 10, "current": 1, "testPlanId": plan_id
                })
                assert r.status_code == 200, f"计划功能用例列表失败: {r.text}"

                # 3. 计划详情-功能用例模块树
                r = client.get(f"/test-plan/functional/case/tree?testPlanId={plan_id}")
                assert r.status_code == 200, f"计划功能用例模块树失败: {r.text}"

                # 4. 计划详情-功能用例模块数量
                r = client.get("/test-plan/functional/case/module/count")
                if r.status_code != 200:
                    r = client.post("/test-plan/functional/case/module/count", json={"testPlanId": plan_id})
                assert r.status_code == 200, f"计划功能用例模块数量失败: {r.text}"

                # 5. 计划详情-执行历史
                r = client.post("/test-plan/his/page", json={"pageSize": 10, "current": 1, "testPlanId": plan_id})
                if r.status_code != 200:
                    r = client.get(f"/test-plan/his/page?testPlanId={plan_id}")
                assert r.status_code == 200, f"计划执行历史失败: {r.text}"

                # 6. 执行人选项
                r = client.get("/test-plan/functional/case/user-option")
                assert r.status_code == 200, f"执行人选项失败: {r.text}"

                # 7. 关联用例接口用例分页
                r = client.post("/test-plan/association/api/page", json={"pageSize": 10, "current": 1, "testPlanId": plan_id})
                assert r.status_code == 200, f"关联接口用例分页失败: {r.text}"

                # 8. 关联用例接口场景分页
                r = client.post("/test-plan/association/api/scenario/page", json={"pageSize": 10, "current": 1, "testPlanId": plan_id})
                assert r.status_code == 200, f"关联接口场景分页失败: {r.text}"

                # 9. 删除计划
                r = client.post("/test-plan/delete", json={"id": plan_id})
                assert r.status_code == 200, f"删除计划失败: {r.text}"

            # 10. 计划组下拉
            r = client.get("/test-plan/group-list")
            assert r.status_code == 200, f"计划组下拉失败: {r.text}"
        test("测试计划详情完整流程", test_test_plan_detail_flow)

        # ═══════════════════════════════════════════════
        # 十九、个人设置
        # ═══════════════════════════════════════════════
        def test_personal_settings_flow(client):
            """个人设置：基本信息 → 密码修改 → 语言 → 模型配置。"""
            # 1. 获取个人信息
            r = client.get("/personal/get")
            assert r.status_code == 200, f"获取个人信息失败: {r.text}"

            # 2. 修改基本信息
            r = client.post("/personal/update-info", json={
                "name": "admin",
                "email": "admin@test.com"
            })
            assert r.status_code == 200, f"修改个人信息失败: {r.text}"

            # 3. 获取本地执行配置
            r = client.get("/user/local/config/get")
            assert r.status_code == 200, f"获取本地配置失败: {r.text}"

            # 4. 模型配置列表
            r = client.get("/personal/model/source/list")
            assert r.status_code == 200, f"获取个人模型配置失败: {r.text}"

            # 5. 平台信息
            r = client.get("/user/platform/get")
            assert r.status_code == 200, f"获取平台信息失败: {r.text}"

            # 6. 平台账号信息
            r = client.get("/user/platform/account/info")
            assert r.status_code == 200, f"获取平台账号信息失败: {r.text}"
        test("个人设置完整流程", test_personal_settings_flow)

        # ═══════════════════════════════════════════════
        # 二十、跨模块业务流程
        # ═══════════════════════════════════════════════
        def test_cross_module_flow(client):
            """跨模块业务：创建用例 → 创建缺陷 → 关联缺陷到用例 → 创建评审关联用例。"""
            # 1. 创建功能用例
            case_name = _unique("跨模块")
            r = client.post("/functional/case/add", json={
                "name": case_name,
                "description": "跨模块业务流程测试",
                "priority": "P1",
                "status": "open"
            })
            assert r.status_code == 200, f"创建功能用例失败: {r.text}"
            cdata = _data(r)
            case_id = cdata.get("id") if isinstance(cdata, dict) else None
            assert case_id, f"创建功能用例未返回 ID: {r.text}"

            # 2. 创建缺陷
            bug_name = _unique("跨模块缺陷")
            r = client.post("/bug/add", json={
                "title": bug_name,
                "description": "跨模块流程缺陷",
                "status": "open",
                "severity": "critical"
            })
            assert r.status_code == 200, f"创建缺陷失败: {r.text}"
            bdata = _data(r)
            bug_id = bdata.get("id") if isinstance(bdata, dict) else None

            # 3. 关联缺陷到用例（如果接口存在）
            if case_id and bug_id:
                r = client.post("/functional/case/test/associate/bug", json={
                    "caseId": case_id,
                    "bugId": bug_id
                })
                assert r.status_code in [200, 404, 400], f"关联缺陷到用例异常: {r.status_code}"

                # 4. 获取用例关联缺陷列表
                r = client.post("/functional/case/test/has/associate/bug/page", json={
                    "caseId": case_id, "pageSize": 10, "current": 1
                })
                assert r.status_code == 200, f"获取用例关联缺陷失败: {r.text}"

            # 5. 创建用例评审
            review_name = _unique("跨模块评审")
            r = client.post("/case/review/add", json={
                "name": review_name,
                "description": "跨模块流程评审",
                "projectId": PROJECT_ID
            })
            assert r.status_code == 200, f"创建用例评审失败: {r.text}"
            rdata = _data(r)
            review_id = rdata.get("id") if isinstance(rdata, dict) else None

            # 6. 关联用例到评审
            if case_id and review_id:
                r = client.post("/case/review/associate", json={
                    "reviewId": review_id,
                    "caseIds": [case_id]
                })
                assert r.status_code in [200, 400], f"关联用例到评审异常: {r.status_code}"

            # 7. 清理
            if case_id:
                r = client.post("/functional/case/delete", json={"id": case_id})
                assert r.status_code == 200, f"清理用例失败: {r.text}"
            if review_id:
                r = client.post("/case/review/delete", json={"id": review_id})
                assert r.status_code == 200, f"清理评审失败: {r.text}"
        test("跨模块业务流程", test_cross_module_flow)

        # ═══════════════════════════════════════════════
        # 输出总结
        # ═══════════════════════════════════════════════
        print("\n" + "=" * 60)
        passed = len([r for r in results if r.startswith("✅")])
        failed = len([r for r in results if r.startswith("❌")])
        print(f"共 {passed + failed} 项测试，{passed} 项通过，{failed} 项失败")
        if failures:
            print("\n失败详情：")
            for module, err in failures:
                print(f"  ❌ {module}: {err}")
        print("=" * 60)

        # 返回失败信息
        if failures:
            raise SystemExit(f"业务流程测试失败: {len(failures)} 项失败")

if __name__ == "__main__":
    main()
