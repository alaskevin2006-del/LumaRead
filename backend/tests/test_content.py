import io,wave
import pymupdf
from conftest import student

def pdf_bytes():
    d=pymupdf.open();p=d.new_page();p.insert_text((40,50),'The little dog sees a red ball.')
    return d.tobytes()
def wav_bytes():
    b=io.BytesIO()
    with wave.open(b,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*16000)
    return b.getvalue()
def draft(c):
    r=c.post('/api/admin/books',json={'title':'A Big Red Ball','level':'A','description':'测试'})
    assert r.status_code==201,r.text
    return r.json()
def ready_book(app,c):
    b=draft(c);v=b['draft']['id']
    j=c.post(f'/api/admin/versions/{v}/import',files={'file':('book.pdf',pdf_bytes(),'application/pdf')}).json()
    from app.worker import run_job
    run_job(app,j['id'])
    b=c.get('/api/admin/books/'+b['id']).json();p=b['draft']['pages'][0]
    a=c.post(f'/api/admin/versions/{v}/assets',data={'kind':'audio'},files={'file':('page.wav',wav_bytes(),'audio/wav')}).json()
    assert c.patch('/api/admin/pages/'+p['id'],json={'audio_id':a['id'],'audio_start_ms':0,'audio_end_ms':1000,'reviewed':True}).status_code==200
    return c.get('/api/admin/books/'+b['id']).json()

def test_import_publish_immutable_revision_and_archive(admin):
    app,c=admin;b=draft(c);v=b['draft']['id']
    assert c.post(f'/api/admin/versions/{v}/publish').status_code==422
    b=ready_book(app,c);v=b['draft']['id'];p=b['draft']['pages'][0]
    assert p['text'].startswith('The little dog')
    assert c.post(f'/api/admin/versions/{v}/publish').status_code==200
    assert c.patch('/api/admin/pages/'+p['id'],json={'text':'changed'}).status_code==409
    rev=c.post('/api/admin/books/'+b['id']+'/draft').json()
    assert rev['id']!=v and rev['pages'][0]['id']!=p['id']
    assert c.patch('/api/admin/pages/'+rev['pages'][0]['id'],json={'text':'A new sentence.'}).json()['reviewed'] is False
    assert c.post('/api/admin/books/'+b['id']+'/archive').status_code==200
    assert c.get('/api/books').json()==[]

def test_private_drafts_and_intervals(admin):
    app,c=admin;b=ready_book(app,c);p=b['draft']['pages'][0]
    assert c.patch('/api/admin/pages/'+p['id'],json={'audio_start_ms':1000,'audio_end_ms':500}).status_code==422
    student(c);c.post('/api/auth/login',json={'username':'student','password':'Student123'})
    c.post('/api/auth/password',json={'current_password':'Student123','new_password':'NewStudent123'})
    assert c.get('/api/media/'+p['image_id']).status_code==404
    assert c.get('/api/books/'+b['id']).status_code==404

def test_corrupt_pdf_retains_draft(admin):
    app,c=admin;b=draft(c)
    j=c.post(f'/api/admin/versions/{b["draft"]["id"]}/import',files={'file':('broken.pdf',b'%PDF-broken','application/pdf')}).json()
    from app.worker import run_job
    run_job(app,j['id'])
    assert c.get('/api/jobs/'+j['id']).json()['status']=='failed'
    assert c.get('/api/admin/books/'+b['id']).status_code==200

def test_delete_first_page_renumbers_regardless_of_primary_key_order(admin):
    from app.models import Page
    app,c=admin;b=draft(c);vid=b['draft']['id']
    with app.state.db() as db:
        db.add_all([Page(id='a-delete',version_id=vid,position=1),Page(id='z-second',version_id=vid,position=2),Page(id='b-third',version_id=vid,position=3)])
        db.commit()
    assert c.delete('/api/admin/pages/a-delete').status_code==200
    pages=c.get('/api/admin/books/'+b['id']).json()['draft']['pages']
    assert [(p['id'],p['position']) for p in pages]==[('z-second',1),('b-third',2)]

def test_streaming_webm_without_container_duration_is_accepted(tmp_path):
    import subprocess,json
    from app.media import duration
    # Pipe output reproduces MediaRecorder's non-seekable WebM without a Duration header.
    result=subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1','-c:a','libopus','-f','webm','pipe:1'],capture_output=True,check=True)
    path=tmp_path/'browser.webm';path.write_bytes(result.stdout)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(path)]))
    assert 'duration' not in probe.get('format',{})
    assert 900<=duration(path)<=1100

def test_failed_pdf_cannot_be_retried_after_publication(admin):
    from app.models import Job
    app,c=admin;b=ready_book(app,c);vid=b['draft']['id']
    with app.state.db() as db:
        j=Job(user_id=db.query(Job).first().user_id,kind='pdf',status='failed',payload={'version_id':vid,'asset_id':'unused'})
        db.add(j);db.commit();jid=j.id
    assert c.post(f'/api/admin/versions/{vid}/publish').status_code==200
    assert c.post(f'/api/jobs/{jid}/retry').status_code==409
    assert c.get('/api/jobs/'+jid).json()['status']=='failed'

def test_pdf_retry_waits_for_publication_lock_on_postgres(admin):
    import pytest,threading
    from concurrent.futures import ThreadPoolExecutor
    from app.content import get_draft
    from app.models import Job
    app,c=admin
    if app.state.engine.dialect.name!='postgresql':pytest.skip('Requires real PostgreSQL row locks')
    b=ready_book(app,c);vid=b['draft']['id']
    with app.state.db() as db:
        j=Job(user_id=db.query(Job).first().user_id,kind='pdf',status='failed',payload={'version_id':vid,'asset_id':'unused'})
        db.add(j);db.commit();jid=j.id
    locked=threading.Event();release=threading.Event()
    def publishing():
        with app.state.db() as db:
            v=get_draft(db,vid);locked.set()
            if not release.wait(5):raise TimeoutError('Test publisher did not release')
            v.published=True;db.commit()
    with ThreadPoolExecutor(2) as pool:
        publisher=pool.submit(publishing);assert locked.wait(3)
        retry=pool.submit(lambda:c.post('/api/jobs/'+jid+'/retry'))
        try:
            # A retry must wait until publication commits, then reject the locked version.
            from concurrent.futures import TimeoutError as FutureTimeout
            with pytest.raises(FutureTimeout):retry.result(timeout=.2)
        finally:release.set()
        publisher.result(timeout=5);assert retry.result(timeout=5).status_code==409
