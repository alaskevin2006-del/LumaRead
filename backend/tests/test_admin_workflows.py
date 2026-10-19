from test_content import ready_book, draft

def test_optional_media_and_display_only_book(admin):
    app,c=admin;b=ready_book(app,c);v=b['draft'];p=v['pages'][0]
    c.patch('/api/admin/pages/'+p['id'],json={'audio_id':None,'reviewed':False})
    assert c.get('/api/admin/versions/'+v['id']+'/check').json()['issues']==[]
    c.patch('/api/admin/pages/'+p['id'],json={'kind':'display','text':''})
    assert c.post('/api/admin/versions/'+v['id']+'/publish').status_code==200
    s=c.post('/api/sessions',json={'book_id':b['id']}).json()
    assert c.post('/api/sessions/'+s['id']+'/complete').status_code==200

def test_unpublish_edit_delete_preserves_history(admin):
    app,c=admin;b=ready_book(app,c);v=b['draft'];c.post('/api/admin/versions/'+v['id']+'/publish')
    s=c.post('/api/sessions',json={'book_id':b['id']}).json()
    assert c.post('/api/admin/books/'+b['id']+'/archive').status_code==200
    updated=c.get('/api/admin/books/'+b['id']).json()
    assert updated['status']=='draft' and updated['draft']
    assert c.delete('/api/admin/books/'+b['id']).status_code==200
    assert all(x['id']!=b['id'] for x in c.get('/api/admin/books').json())
    assert c.get('/api/sessions/'+s['id']).status_code==200

def test_page_order_and_atomic_audio_mapping(admin):
    app,c=admin;b=ready_book(app,c);v=b['draft'];p=v['pages'][0]
    second=c.post('/api/admin/versions/'+v['id']+'/pages?position=1').json()
    pages=c.get('/api/admin/books/'+b['id']).json()['draft']['pages']
    assert [x['id'] for x in pages]==[second['id'],p['id']]
    url='/api/admin/versions/'+v['id']
    assert c.put(url+'/order',json={'page_ids':[p['id'],second['id']]}).status_code==200
    assert c.put(url+'/order',json={'page_ids':[p['id'],p['id']]}).status_code==422
    data={'bindings':[{'page_id':second['id'],'audio_id':p['audio_id'],'start_ms':0,'end_ms':1000}]}
    assert c.put(url+'/audio-bindings',json=data).status_code==200
    data['bindings'][0]['end_ms']=9000;data['overwrite']=True
    assert c.put(url+'/audio-bindings',json=data).status_code==422
    assert c.get('/api/admin/books/'+b['id']).json()['draft']['pages'][1]['audio_end_ms']==1000

def test_bulk_students_atomic_validation_and_reset(admin):
    app,c=admin
    rows=[{'name':'小明','class_name':'一班'},{'name':'小红','username':'hong','class_name':'二班'}]
    r=c.post('/api/admin/students/import',json={'rows':rows});assert r.status_code==201,r.text
    users=r.json();assert len(users)==2 and all(x['temporary_password'] for x in users)
    assert c.post('/api/admin/students/import',json={'rows':[{'name':'新生','username':'fresh'},rows[1]]}).status_code==409
    assert not any(x['username']=='fresh' for x in c.get('/api/admin/users').json())
    ids=[u['id'] for u in users]
    assert c.post('/api/admin/students/bulk',json={'ids':ids,'action':'class','class_name':'三班'}).status_code==200
    assert all(x['class_name']=='三班' for x in c.get('/api/admin/users').json())
    r=c.post('/api/admin/students/bulk',json={'ids':ids,'action':'reset'})
    assert r.status_code==200 and all(x['temporary_password'] for x in r.json())

def test_xlsx_preview_does_not_create_accounts(admin):
    import io
    from openpyxl import Workbook
    app,c=admin
    w=Workbook();w.active.append(['姓名','账号','班级']);w.active.append(['小明','xlsx_student','一班'])
    data=io.BytesIO();w.save(data)
    r=c.post('/api/admin/students/preview',files={'file':('students.xlsx',data.getvalue())})
    assert r.status_code==200,r.text
    assert r.json()==[{'name':'小明','username':'xlsx_student','class_name':'一班'}]
    assert c.get('/api/admin/users').json()==[]

def test_text_only_practice_can_publish_but_empty_page_cannot(admin):
    app,c=admin;b=ready_book(app,c);v=b['draft'];p=v['pages'][0]
    assert c.patch('/api/admin/pages/'+p['id'],json={'image_id':None,'audio_id':None}).status_code==200
    assert c.get('/api/admin/versions/'+v['id']+'/check').json()['issues']==[]
    c.patch('/api/admin/pages/'+p['id'],json={'kind':'display','text':''})
    assert c.post('/api/admin/versions/'+v['id']+'/publish').status_code==422

def test_audio_binding_failure_rolls_back_all_pages(admin):
    app,c=admin;b=ready_book(app,c);v=b['draft'];p=v['pages'][0]
    second=c.post('/api/admin/versions/'+v['id']+'/pages').json()
    payload={'overwrite':True,'bindings':[{'page_id':second['id'],'audio_id':p['audio_id'],'start_ms':0,'end_ms':500},{'page_id':p['id'],'audio_id':p['audio_id'],'start_ms':0,'end_ms':9000}]}
    assert c.put('/api/admin/versions/'+v['id']+'/audio-bindings',json=payload).status_code==422
    assert c.get('/api/admin/books/'+b['id']).json()['draft']['pages'][1]['audio_id'] is None

def test_bulk_management_rejects_student_and_admin_targets(admin):
    from conftest import student
    app,c=admin
    admin_id=c.get('/api/auth/me').json()['id']
    assert c.post('/api/admin/students/bulk',json={'ids':[admin_id],'action':'disable'}).status_code==422
    student(c);c.post('/api/auth/login',json={'username':'student','password':'Student123'})
    c.post('/api/auth/password',json={'current_password':'Student123','new_password':'NewStudent123'})
    assert c.post('/api/admin/students/import',json={'rows':[{'name':'forbidden'}]}).status_code==403
