"""接口测试模块单元测试"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from fastapi.testclient import TestClient


def _data(resp):
    """解析响应，统一取 data 层。"""
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body



@pytest.fixture(scope="module")
def client():
    os.environ['OPENAI_API_KEY'] = 'test-key'
    from app.main import app
    with TestClient(app) as c:
        # 登录获取认证令牌
        r = c.post("/login", json={"username": "admin", "password": "admin123"})
        if r.status_code == 200:
            session = r.json()["data"]
            c.headers.update({
                "X-AUTH-TOKEN": session["sessionId"],
                "CSRF-TOKEN": session["csrfToken"],
            })
        yield c


class TestApiDefinitions:
    def test_create_api_definition(self, client):
        r = client.post('/api/api-definitions', json={
            'name': 'User API', 'method': 'GET', 'path': '/api/users',
            'protocol': 'HTTP', 'description': 'Get users list'
        })
        assert r.status_code == 200
        data = _data(r)
        assert data['name'] == 'User API'
        assert data['method'] == 'GET'
        assert data['path'] == '/api/users'
        assert 'id' in data
        return data['id']

    def test_list_api_definitions(self, client):
        r = client.get('/api/api-definitions')
        assert r.status_code == 200
        assert 'definitions' in _data(r)
        assert len(_data(r)['definitions']) >= 1

    def test_get_api_definition(self, client):
        def_id = self.test_create_api_definition(client)
        r = client.get(f'/api/api-definitions/{def_id}')
        assert r.status_code == 200
        assert _data(r)['id'] == def_id

    def test_update_api_definition(self, client):
        def_id = self.test_create_api_definition(client)
        r = client.put(f'/api/api-definitions/{def_id}', json={
            'name': 'Updated API', 'method': 'POST', 'path': '/api/updated',
            'protocol': 'HTTP'
        })
        assert r.status_code == 200
        assert _data(r)['name'] == 'Updated API'
        assert _data(r)['method'] == 'POST'

    def test_delete_api_definition(self, client):
        def_id = self.test_create_api_definition(client)
        r = client.delete(f'/api/api-definitions/{def_id}')
        assert r.status_code == 200


class TestApiTestCases:
    def test_create_api_test_case(self, client):
        r = client.post('/api/api-test-cases', json={
            'name': 'Test User List', 'method': 'GET', 'path': '/api/users'
        })
        assert r.status_code == 200
        data = _data(r)
        assert data['name'] == 'Test User List'
        assert data['method'] == 'GET'
        return data['id']

    def test_list_api_test_cases(self, client):
        r = client.get('/api/api-test-cases')
        assert r.status_code == 200
        assert 'cases' in _data(r)

    def test_update_api_test_case(self, client):
        case_id = self.test_create_api_test_case(client)
        r = client.put(f'/api/api-test-cases/{case_id}', json={
            'name': 'Updated Case', 'method': 'POST', 'path': '/api/updated',
            'assertions': [{'type': 'status_code', 'value': '200'}]
        })
        assert r.status_code == 200
        assert _data(r)['name'] == 'Updated Case'

    def test_delete_api_test_case(self, client):
        case_id = self.test_create_api_test_case(client)
        r = client.delete(f'/api/api-test-cases/{case_id}')
        assert r.status_code == 200


class TestScenarios:
    def test_create_scenario(self, client):
        r = client.post('/api/scenarios', json={
            'name': 'User Flow', 'description': 'End-to-end user flow',
            'steps': []
        })
        assert r.status_code == 200
        assert _data(r)['name'] == 'User Flow'
        return _data(r)['id']

    def test_list_scenarios(self, client):
        r = client.get('/api/scenarios')
        assert r.status_code == 200
        assert 'scenarios' in _data(r)

    def test_execute_scenario(self, client):
        sc_id = self.test_create_scenario(client)
        r = client.post(f'/api/scenarios/{sc_id}/execute', json={})
        assert r.status_code == 200


class TestMockServices:
    def test_create_mock(self, client):
        r = client.post('/api/mock-services', json={
            'name': 'Mock Users', 'method': 'GET', 'path': '/api/mock/users',
            'response_code': 200
        })
        assert r.status_code == 200
        assert _data(r)['name'] == 'Mock Users'
        return _data(r)['id']

    def test_list_mocks(self, client):
        r = client.get('/api/mock-services')
        assert r.status_code == 200
        assert 'mocks' in _data(r)


class TestEnvironments:
    def test_create_environment(self, client):
        r = client.post('/api/environments', json={
            'name': 'Dev', 'base_url': 'https://dev.example.com'
        })
        assert r.status_code == 200
        assert _data(r)['name'] == 'Dev'
        return _data(r)['id']

    def test_list_environments(self, client):
        r = client.get('/api/environments')
        assert r.status_code == 200
        assert 'environments' in _data(r)


class TestProjects:
    def test_create_project(self, client):
        r = client.post('/api/projects', json={
            'name': 'Test Project', 'language': 'python'
        })
        assert r.status_code == 200
        assert _data(r)['name'] == 'Test Project'
        return _data(r)['id']

    def test_list_projects(self, client):
        r = client.get('/api/projects')
        assert r.status_code == 200
        assert 'projects' in _data(r)


class TestImport:
    def test_import_postman(self, client):
        data = {
            'item': [{
                'name': 'Get Users',
                'request': {
                    'method': 'GET',
                    'url': {'path': ['api', 'users'], 'query': []},
                    'header': [],
                    'body': {}
                }
            }]
        }
        r = client.post('/api/api-definitions/import', json={
            'format': 'postman', 'data': data
        })
        assert r.status_code == 200
        assert _data(r)['imported'] >= 1

    def test_import_swagger(self, client):
        data = {
            'paths': {
                '/api/users': {
                    'get': {
                        'summary': 'Get all users',
                        'operationId': 'getUsers',
                        'tags': ['users'],
                        'parameters': [],
                        'requestBody': {}
                    }
                }
            }
        }
        r = client.post('/api/api-definitions/import', json={
            'format': 'swagger', 'data': data
        })
        assert r.status_code == 200
        assert _data(r)['imported'] >= 1


class TestCaseManagementAPIs:
    def test_mindmap(self, client):
        r = client.get('/api/cases/mindmap')
        assert r.status_code == 200

    def test_trash(self, client):
        r = client.get('/api/cases/trash')
        assert r.status_code == 200

    def test_export(self, client):
        r = client.get('/api/cases/export?format=excel')
        assert r.status_code == 200
