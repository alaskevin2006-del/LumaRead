import pytest
from test_content import ready_book,wav_bytes
from test_reading import setup_student,mark_success
from app.models import Job,Page

def test_reference_job_snapshots_page_not_client_text(admin):
    app,c=admin;app.state.settings.speech_provider='reference_similarity'
    b=ready_book(app,c);p=b['draft']['pages'][0]
    r=c.post('/api/admin/speech/test',data={'page_id':p['id'],'reference_text':'ignored'},files={'file':('test.wav',wav_bytes())})
    assert r.status_code==202,r.text
    with app.state.db() as db:
        payload=db.get(Job,r.json()['id']).payload
        assert payload['provider']=='reference_similarity'
        assert payload['reference']['asset_id']==p['audio_id']
        assert payload['reference']['end_ms']==1000
    c.patch('/api/admin/pages/'+p['id'],json={'audio_id':None})
    with app.state.db() as db:assert db.get(Job,r.json()['id']).payload==payload
    assert c.post('/api/admin/speech/test',data={'page_id':p['id']},files={'file':('test.wav',wav_bytes())}).status_code==422
    assert c.post('/api/admin/speech/test',data={'page_id':'missing'},files={'file':('test.wav',wav_bytes())}).status_code==404

def test_reference_session_eligibility_is_fixed(admin):
    app,c=admin;app.state.settings.speech_provider='reference_similarity'
    b,v,u=setup_student(app,c);p=v['pages'][0]
    with app.state.db() as db:
        db.add(Page(version_id=v['id'],position=2,kind='practice',text='Read only'));db.commit()
    s=c.post('/api/sessions',json={'book_id':b['id']}).json()
    assert s['scoring_mode']=='reference_similarity'
    assert s['required_page_ids']==[p['id']] and s['page_count']==1
    app.state.settings.speech_provider='disabled'
    mark_success(app,u,s,p)
    assert c.post('/api/sessions/'+s['id']+'/complete').status_code==200

def test_reference_result_rejects_malformed_values():
    from app.reference import normalize_reference,REVISION
    data={'mode':'reference_similarity','overall_score':90,'mean_cosine_distance':.1,'duration_ratio':1,
          'model_revision':REVISION,'model':'microsoft/wavlm-large','preprocessing_version':'mono16k-edge-rms-v1',
          'scoring_config_version':'wavlm-last-cosine-dtw-path-v1','segments':[{'reference_start':0,'reference_end':1,'recording_start':0,'recording_end':1,'similarity':90}]}
    assert normalize_reference(data,1,1)['experimental'] is True
    for key,value in [('overall_score',float('nan')),('model_revision','other'),('segments',[])]:
        with pytest.raises(ValueError):normalize_reference({**data,key:value},1,1)
    with pytest.raises(ValueError):normalize_reference({**data,'segments':[dict(data['segments'][0],recording_end=1000)]},1,1)

def test_reference_worker_and_private_recording(admin,monkeypatch):
    import httpx
    from app.worker import run_job
    from app.reference import REVISION
    app,c=admin;app.state.settings.speech_provider='reference_similarity'
    b,v,u=setup_student(app,c);p=v['pages'][0]
    s=c.post('/api/sessions',json={'book_id':b['id']}).json()
    def provider(url,**kwargs):
        assert url.endswith('/evaluate')
        assert kwargs['data']['model_revision']==REVISION
        assert kwargs['files']['reference'][1].read(4)==b'RIFF'
        return httpx.Response(200,json={'mode':'reference_similarity','overall_score':90,'mean_cosine_distance':.1,'duration_ratio':1,
          'model_revision':REVISION,'model':'microsoft/wavlm-large','preprocessing_version':'mono16k-edge-rms-v1',
          'scoring_config_version':'wavlm-last-cosine-dtw-path-v1','segments':[{'reference_start':0,'reference_end':1,'recording_start':0,'recording_end':1,'similarity':90}]})
    monkeypatch.setattr('app.evaluators.httpx.post',provider)
    fields={'session_id':s['id'],'page_id':p['id'],'idempotency_key':'reference-test'}
    r=c.post('/api/evaluations',data=fields,files={'file':('test.wav',wav_bytes())})
    assert r.status_code==202,r.text
    assert c.post('/api/evaluations',data=fields,files={'file':('test.wav',wav_bytes())}).json()==r.json()
    run_job(app,r.json()['id'])
    j=c.get('/api/jobs/'+r.json()['id']).json();assert j['status']=='succeeded',j
    result=j['result'];assert result['words']==[] and result['experimental']
    assert result['reference_audio_id']==p['audio_id']
    assert c.get('/api/media/'+result['recording_audio_id']).status_code==200
    assert c.post('/api/sessions/'+s['id']+'/complete').status_code==200
    c.post('/api/auth/logout')
    assert c.get('/api/media/'+result['recording_audio_id']).status_code==401

def test_foreign_book_reference_is_rejected(admin):
    app,c=admin;app.state.settings.speech_provider='reference_similarity'
    first=ready_book(app,c);second=ready_book(app,c);p=first['draft']['pages'][0]
    with app.state.db() as db:
        db.get(Page,p['id']).audio_id=second['draft']['pages'][0]['audio_id'];db.commit()
    r=c.post('/api/admin/speech/test',data={'page_id':p['id']},files={'file':('test.wav',wav_bytes())})
    assert r.status_code==422

def test_legacy_round_does_not_silently_change_mode_and_can_restart(admin):
    app,c=admin;b,v,u=setup_student(app,c);p=v['pages'][0]
    with app.state.db() as db:
        db.get(Page,p['id']).audio_id=None;db.commit()
    old=c.post('/api/sessions',json={'book_id':b['id']}).json()
    app.state.settings.speech_provider='reference_similarity'
    r=c.post('/api/evaluations',data={'session_id':old['id'],'page_id':p['id'],'idempotency_key':'legacy'},files={'file':('test.wav',wav_bytes())})
    assert r.status_code==503
    new=c.post('/api/sessions',json={'book_id':b['id'],'restart':True}).json()
    assert new['id']!=old['id'] and new['required_page_ids']==[]
    assert c.post('/api/sessions/'+new['id']+'/complete').status_code==200
    # The historical incomplete round and its original requirements stay intact.
    assert c.get('/api/sessions/'+old['id']).json()['completed_at'] is None
    assert c.post('/api/sessions/'+old['id']+'/complete').status_code==422
