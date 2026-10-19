import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings

@pytest.fixture
def env(tmp_path):
    app=create_app(Settings(database_url=f'sqlite:///{tmp_path}/test.db',media_dir=str(tmp_path/'media'),secure_cookies=False,testing=True))
    with TestClient(app, headers={'X-LumaRead':'1'}) as c:
        app.state.seed_admin('admin','AdminPass123')
        yield app,c

@pytest.fixture
def admin(env):
    app,c=env
    assert c.post('/api/auth/login',json={'username':'admin','password':'AdminPass123'}).status_code==200
    return app,c

def student(client, name='student'):
    r=client.post('/api/admin/users',json={'username':name,'name':'小林','password':'Student123'})
    assert r.status_code==201,r.text
    return r.json()
