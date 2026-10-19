from datetime import timedelta,timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter,Request,UploadFile,File,Form,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from .auth import DB,Current,Admin,fail
from .models import Book,BookVersion,Page,ReadingSession,ReadingAttempt,Checkin,Job,now
from .content import version_json,get_draft,busy
from .media import save_upload

router=APIRouter(prefix='/api')
def local_date(dt=None):return (dt or now()).replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Asia/Shanghai')).date()
def own_session(db,sid,user,lock=False):
    query=select(ReadingSession).where(ReadingSession.id==sid,ReadingSession.user_id==user.id)
    s=db.scalar(query.with_for_update() if lock else query)
    if not s:fail(404,'阅读记录不存在')
    return s
def session_json(db,s,detail=False):
    attempts=list(db.scalars(select(ReadingAttempt).where(ReadingAttempt.session_id==s.id,ReadingAttempt.status=='succeeded').order_by(ReadingAttempt.created_at)))
    result={'id':s.id,'book_id':s.book_id,'version_id':s.version_id,'current_page':s.current_page,'completed_at':s.completed_at,'created_at':s.created_at,'completed_pages':list(dict.fromkeys(a.page_id for a in attempts))}
    v=db.get(BookVersion,s.version_id)
    result.update(title=v.title,level=v.level,cover_id=v.cover_id,page_count=db.scalar(select(func.count()).select_from(Page).where(Page.version_id==v.id,Page.kind=='practice')))
    if detail:
        result['version']=version_json(db,v);result['latest_results']={a.page_id:a.result for a in attempts}
        result['pending_jobs']={a.page_id:a.job_id for a in db.scalars(select(ReadingAttempt).where(ReadingAttempt.session_id==s.id,ReadingAttempt.status.in_(['queued','running'])))}
    return result
class Start(BaseModel):book_id:str
class Progress(BaseModel):current_page:int=Field(ge=1,le=100)

@router.post('/sessions')
def start(data:Start,user:Current,db:DB):
    key=user.id+':'+data.book_id
    existing=db.scalar(select(ReadingSession).where(ReadingSession.active_key==key))
    if existing:return session_json(db,existing,True)
    b=db.get(Book,data.book_id)
    if not b or b.status!='published':fail(404,'绘本暂不可用')
    s=ReadingSession(user_id=user.id,book_id=b.id,version_id=b.published_version_id,active_key=key);db.add(s)
    try:db.commit()
    except IntegrityError:db.rollback();s=db.scalar(select(ReadingSession).where(ReadingSession.active_key==key))
    return session_json(db,s,True)
@router.get('/sessions/{session_id}')
def detail(session_id:str,user:Current,db:DB):return session_json(db,own_session(db,session_id,user),True)
@router.put('/sessions/{session_id}/progress')
def progress(session_id:str,data:Progress,user:Current,db:DB):
    s=own_session(db,session_id,user)
    if not db.scalar(select(Page.id).where(Page.version_id==s.version_id,Page.position==data.current_page)):fail(422,'页码不存在')
    s.current_page=data.current_page;db.commit();return {'ok':True}
@router.post('/sessions/{session_id}/complete')
def complete(session_id:str,user:Current,db:DB):
    s=own_session(db,session_id,user,True)
    if s.completed_at:return session_json(db,s)
    pages=list(db.scalars(select(Page).where(Page.version_id==s.version_id,Page.kind=='practice').order_by(Page.position)))
    done=set(db.scalars(select(ReadingAttempt.page_id).where(ReadingAttempt.session_id==s.id,ReadingAttempt.status=='succeeded')))
    missing=[p.position for p in pages if p.id not in done]
    if missing or not pages:raise HTTPException(422,{'message':'请补齐未练习的页面','missing_pages':missing})
    s.completed_at=now();s.active_key=None;day=local_date(s.completed_at)
    insert=__import__('sqlalchemy.dialects.sqlite' if db.bind.dialect.name=='sqlite' else 'sqlalchemy.dialects.postgresql',fromlist=['insert']).insert
    db.execute(insert(Checkin).values(user_id=user.id,date=day).on_conflict_do_nothing(index_elements=['user_id','date']))
    db.commit();return session_json(db,s)
@router.get('/me/history')
def history(user:Current,db:DB):return [session_json(db,s) for s in db.scalars(select(ReadingSession).where(ReadingSession.user_id==user.id).order_by(ReadingSession.created_at.desc()).limit(200))]
@router.get('/me/stats')
def stats(user:Current,db:DB):
    days=set(db.scalars(select(Checkin.date).where(Checkin.user_id==user.id)))
    today=local_date();cursor=today if today in days else today-timedelta(days=1);streak=0
    while cursor in days:streak+=1;cursor-=timedelta(days=1)
    sessions=list(db.scalars(select(ReadingSession).where(ReadingSession.user_id==user.id,ReadingSession.completed_at.is_not(None))))
    return {'books_completed':len({s.book_id for s in sessions}),'sessions_completed':len(sessions),'streak':streak,'today_checked':today in days,'today':str(today),'checkins':sorted(str(x) for x in days)}
@router.get('/speech/status')
def speech_status(request:Request,user:Current):
    s=request.app.state.settings
    return {'provider':s.speech_provider,'configured':s.speech_provider=='remote' or (s.speech_provider=='azure' and bool(s.azure_key and s.azure_region)),'message':'评分服务尚未配置，当前可以听读；配置完成后可跟读评分。' if s.speech_provider=='disabled' else '评分供练习参考'}
@router.post('/evaluations',status_code=202)
async def evaluate(request:Request,user:Current,db:DB,file:UploadFile=File(),session_id:str=Form(),page_id:str=Form(),idempotency_key:str=Form(max_length=80)):
    previous=db.scalar(select(ReadingAttempt).where(ReadingAttempt.user_id==user.id,ReadingAttempt.idempotency_key==idempotency_key))
    if previous:
        if previous.session_id!=session_id or previous.page_id!=page_id:fail(409,'重复请求的内容不同')
        return {'id':previous.job_id,'attempt_id':previous.id}
    s=own_session(db,session_id,user);p=db.get(Page,page_id)
    if s.completed_at:fail(409,'本轮已完成，请开始新一轮阅读')
    if not p or p.version_id!=s.version_id or p.kind!='practice':fail(422,'此页面不可跟读')
    settings=request.app.state.settings
    if settings.speech_provider not in ['azure','remote']:fail(503,'真实评分服务尚未配置；不会使用模拟成绩')
    pending=db.scalar(select(func.count()).select_from(Job).where(Job.user_id==user.id,Job.kind=='evaluation',Job.status.in_(['queued','running'])))
    if pending>=3:fail(429,'还有录音正在处理，请稍后再试')
    a=await save_upload(file,'recording',user.id,None,settings,db)
    j=Job(user_id=user.id,kind='evaluation',payload={'asset_id':a.id,'page_id':p.id,'reference_text':p.text,'version_id':p.version_id});db.add(j);db.flush()
    attempt=ReadingAttempt(user_id=user.id,session_id=s.id,page_id=p.id,media_id=a.id,job_id=j.id,idempotency_key=idempotency_key);db.add(attempt)
    try:db.commit()
    except IntegrityError:
        db.rollback();previous=db.scalar(select(ReadingAttempt).where(ReadingAttempt.user_id==user.id,ReadingAttempt.idempotency_key==idempotency_key))
        if previous:return {'id':previous.job_id,'attempt_id':previous.id}
        raise
    return {'id':j.id,'attempt_id':attempt.id}
@router.post('/jobs/{job_id}/retry')
def retry(job_id:str,user:Current,db:DB):
    j=db.get(Job,job_id)
    if not j or (j.user_id!=user.id and user.role!='admin'):fail(404,'任务不存在')
    if j.status in ['queued','running','succeeded']:return {'id':j.id,'status':j.status}
    if j.kind=='pdf':
        # Publication/editing and retry share the same version lock. Queueing a
        # retry cannot slip through publication's busy check.
        get_draft(db,j.payload['version_id']);busy(db,j.payload['version_id'])
    j=db.scalar(select(Job).where(Job.id==job_id).with_for_update().execution_options(populate_existing=True))
    if j.status in ['queued','running','succeeded']:return {'id':j.id,'status':j.status}
    j.status='queued';j.error='';j.result={}
    for a in db.scalars(select(ReadingAttempt).where(ReadingAttempt.job_id==j.id)):a.status='queued'
    db.commit();return {'id':j.id,'status':j.status}
@router.post('/admin/speech/test',status_code=202)
async def speech_test(request:Request,admin:Admin,db:DB,file:UploadFile=File(),reference_text:str=Form(min_length=1,max_length=3000)):
    if request.app.state.settings.speech_provider not in ['azure','remote']:fail(503,'请先配置真实评分服务')
    a=await save_upload(file,'recording',admin.id,None,request.app.state.settings,db)
    j=Job(user_id=admin.id,kind='evaluation',payload={'asset_id':a.id,'reference_text':reference_text,'test':True});db.add(j);db.commit();return {'id':j.id}
