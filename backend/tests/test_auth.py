from conftest import student

def test_login_cookie_and_wrong_password(env):
    _,c=env
    assert c.get('/api/auth/me').status_code==401
    assert c.post('/api/auth/login',json={'username':'admin','password':'wrong'}).status_code==401
    r=c.post('/api/auth/login',json={'username':'admin','password':'AdminPass123'})
    assert r.status_code==200
    assert 'httponly' in r.headers['set-cookie'].lower()
    assert c.get('/api/auth/me').json()['role']=='admin'

def test_first_password_admin_restriction_and_logout(admin):
    _,c=admin
    student(c)
    c.post('/api/auth/logout')
    assert c.post('/api/auth/login',json={'username':'student','password':'Student123'}).json()['must_change_password']
    assert c.get('/api/books').status_code==403
    assert c.post('/api/auth/password',json={'current_password':'Student123','new_password':'NewStudent123'}).status_code==200
    assert c.get('/api/books').status_code==200
    assert c.get('/api/admin/users').status_code==403
    c.post('/api/auth/logout')
    assert c.get('/api/auth/me').status_code==401

def test_disable_reset_revokes_sessions(admin):
    _,c=admin
    u=student(c)
    c.post('/api/auth/logout')
    c.post('/api/auth/login',json={'username':'student','password':'Student123'})
    cookie=c.cookies.get('lumaread_session')
    c.post('/api/auth/login',json={'username':'admin','password':'AdminPass123'})
    assert c.patch('/api/admin/users/'+u['id'],json={'active':False}).status_code==200
    c.cookies.clear();c.cookies.set('lumaread_session',cookie)
    assert c.get('/api/auth/me').status_code==401

def test_csrf_and_account_validation(admin):
    _,c=admin
    assert c.post('/api/admin/users',headers={'X-LumaRead':''},json={}).status_code==403
    assert c.post('/api/admin/users',json={'username':'../bad','name':'X','password':'short'}).status_code==422
    student(c)
    assert c.post('/api/admin/users',json={'username':'student','name':'duplicate','password':'Student123'}).status_code==409

def test_failed_login_tracking_expires_and_is_bounded(env):
    from collections import deque
    import time
    app,c=env
    app.state.login_attempts.update({('ip',str(i)):deque([time.monotonic()-1000]) for i in range(4100)})
    assert c.post('/api/auth/login',json={'username':'missing','password':'wrong'}).status_code==401
    assert len(app.state.login_attempts)==1
    app.state.login_attempts.clear()
    app.state.login_attempts.update({('ip',str(i)):deque([time.monotonic()]) for i in range(4096)})
    assert c.post('/api/auth/login',json={'username':'another','password':'wrong'}).status_code==429
    assert len(app.state.login_attempts)==4096
