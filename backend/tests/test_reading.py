from conftest import student
from test_content import ready_book
from app.models import ReadingAttempt,Job

def setup_student(app,c):
    b=ready_book(app,c);v=b['draft'];c.post('/api/admin/versions/'+v['id']+'/publish');u=student(c)
    c.post('/api/auth/login',json={'username':'student','password':'Student123'})
    c.post('/api/auth/password',json={'current_password':'Student123','new_password':'NewStudent123'})
    return b,v,u
def mark_success(app,u,s,p,key='one',score=20):
    with app.state.db() as db:
        db.add(ReadingAttempt(user_id=u['id'],session_id=s['id'],page_id=p['id'],media_id='test-fixture',job_id='test-job',idempotency_key=key,status='succeeded',result={'overall_score':score,'words':[]}));db.commit()

def test_completion_low_score_checkin_and_replay(admin):
    app,c=admin;b,v,u=setup_student(app,c)
    s=c.post('/api/sessions',json={'book_id':b['id']}).json()
    assert c.post('/api/sessions',json={'book_id':b['id']}).json()['id']==s['id']
    r=c.post('/api/sessions/'+s['id']+'/complete')
    assert r.status_code==422 and r.json()['detail']['missing_pages']==[1]
    mark_success(app,u,s,v['pages'][0])
    assert c.post('/api/sessions/'+s['id']+'/complete').status_code==200
    assert c.post('/api/sessions/'+s['id']+'/complete').status_code==200
    stats=c.get('/api/me/stats').json();assert stats['books_completed']==1 and len(stats['checkins'])==1
    s2=c.post('/api/sessions',json={'book_id':b['id']}).json();assert s2['id']!=s['id']
    mark_success(app,u,s2,v['pages'][0],'two')
    c.post('/api/sessions/'+s2['id']+'/complete')
    stats=c.get('/api/me/stats').json();assert stats['sessions_completed']==2 and len(stats['checkins'])==1

def test_session_owner_and_failed_attempt_does_not_remove_success(admin):
    app,c=admin;b,v,u=setup_student(app,c);s=c.post('/api/sessions',json={'book_id':b['id']}).json()
    mark_success(app,u,s,v['pages'][0])
    with app.state.db() as db:
        db.add(ReadingAttempt(user_id=u['id'],session_id=s['id'],page_id=v['pages'][0]['id'],media_id='test',job_id='test',idempotency_key='failed',status='failed'));db.commit()
    detail=c.get('/api/sessions/'+s['id']).json();assert len(detail['completed_pages'])==1 and detail['latest_results'][v['pages'][0]['id']]['overall_score']==20
    c.post('/api/auth/login',json={'username':'admin','password':'AdminPass123'});student(c,'other')
    c.post('/api/auth/login',json={'username':'other','password':'Student123'})
    c.post('/api/auth/password',json={'current_password':'Student123','new_password':'Other12345'})
    assert c.get('/api/sessions/'+s['id']).status_code==404
    assert c.post('/api/sessions/'+s['id']+'/complete').status_code==404

def test_archived_book_allows_old_session_only(admin):
    app,c=admin;b,v,u=setup_student(app,c);s=c.post('/api/sessions',json={'book_id':b['id']}).json()
    c.post('/api/auth/login',json={'username':'admin','password':'AdminPass123'});c.post('/api/admin/books/'+b['id']+'/archive')
    c.post('/api/auth/login',json={'username':'student','password':'NewStudent123'})
    assert c.get('/api/sessions/'+s['id']).status_code==200
    assert c.get('/api/media/'+v['pages'][0]['image_id']).status_code==200
    # Resume existing session is safe even if hidden from library.
    assert c.post('/api/sessions',json={'book_id':b['id']}).json()['id']==s['id']

def test_recording_worker_contract_and_completion(admin,monkeypatch):
    """External provider is a test double; exercises actual upload, FFmpeg, queue and persistence."""
    import subprocess,httpx
    from app.worker import run_job
    from app.evaluators import word_tokens
    app,c=admin;b,v,u=setup_student(app,c);s=c.post('/api/sessions',json={'book_id':b['id']}).json();p=v['pages'][0]
    app.state.settings.speech_provider='remote'
    def provider(url,**kwargs):
        assert kwargs['data']['reference_text']==p['text']
        assert kwargs['files']['file'][1].read(4)==b'RIFF'
        return httpx.Response(200,request=httpx.Request('POST',url),json={'overall_score':30,'words':[{'text':w['text'],'score':30} for w in word_tokens(p['text'])],'provider_version':'test-fixture-only'})
    monkeypatch.setattr('app.evaluators.httpx.post',provider)
    recording=subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1','-c:a','libopus','-f','webm','pipe:1'],capture_output=True,check=True).stdout
    fields={'session_id':s['id'],'page_id':p['id'],'idempotency_key':'stable-key'}
    job=c.post('/api/evaluations',data=fields,files={'file':('browser.webm',recording,'audio/webm')})
    assert job.status_code==202,job.text
    assert c.post('/api/evaluations',data=fields,files={'file':('browser.webm',recording,'audio/webm')}).json()==job.json()
    run_job(app,job.json()['id'])
    result=c.get('/api/jobs/'+job.json()['id']).json();assert result['status']=='succeeded',result
    assert result['result']['words'][0]['level']=='red'
    assert c.post('/api/sessions/'+s['id']+'/complete').status_code==200
    assert len(c.get('/api/me/stats').json()['checkins'])==1
