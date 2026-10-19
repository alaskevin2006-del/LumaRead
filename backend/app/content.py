from fastapi import APIRouter,Request,UploadFile,File,Form
from pydantic import BaseModel,Field
from typing import Literal
from sqlalchemy import select,delete
from .auth import DB,Admin,Current,fail
from .models import Book,BookVersion,Page,MediaAsset,Job,ReadingSession
from .media import save_upload,can_read_version

router=APIRouter(prefix='/api')
def page_json(p):return {k:getattr(p,k) for k in ['id','version_id','position','kind','text','image_id','audio_id','audio_start_ms','audio_end_ms','reviewed']}
def version_json(db,v):
    if not v:return None
    return {**{k:getattr(v,k) for k in ['id','book_id','number','published','title','level','description','cover_id']},'pages':[page_json(p) for p in db.scalars(select(Page).where(Page.version_id==v.id).order_by(Page.position))]}
def get_draft(db,version_id):
    v=db.scalar(select(BookVersion).where(BookVersion.id==version_id).with_for_update())
    if not v:fail(404,'版本不存在')
    if v.published:fail(409,'已发布版本不可修改，请创建修订草稿')
    return v
def book_json(db,b,admin=False):
    pub=db.get(BookVersion,b.published_version_id) if b.published_version_id else None
    draft=db.scalar(select(BookVersion).where(BookVersion.book_id==b.id,BookVersion.published==False).order_by(BookVersion.number.desc())) if admin else None
    return {'id':b.id,'status':b.status,'published':version_json(db,pub),'draft':version_json(db,draft)}
def busy(db,vid):
    jobs=db.scalars(select(Job).where(Job.kind=='pdf',Job.status.in_(['queued','running'])))
    if any(j.payload.get('version_id')==vid for j in jobs):fail(409,'PDF 正在导入，请稍后编辑或发布')

class BookInput(BaseModel):
    title:str=Field(min_length=1,max_length=120)
    level:Literal['A','B','C']='A'
    description:str=Field(default='',max_length=2000)
    cover_id:str|None=None
class PageInput(BaseModel):
    kind:Literal['practice','display']|None=None
    text:str|None=Field(default=None,max_length=3000)
    image_id:str|None=None
    audio_id:str|None=None
    audio_start_ms:int|None=Field(default=None,ge=0)
    audio_end_ms:int|None=Field(default=None,gt=0)
    reviewed:bool|None=None

@router.get('/admin/books')
def admin_books(admin:Admin,db:DB):return [book_json(db,b,True) for b in db.scalars(select(Book).where(Book.status!='deleted').order_by(Book.created_at.desc()))]
@router.post('/admin/books',status_code=201)
def new_book(data:BookInput,admin:Admin,db:DB):
    b=Book();db.add(b);db.flush();db.add(BookVersion(book_id=b.id,**data.model_dump(exclude={'cover_id'})));db.commit();return book_json(db,b,True)
@router.get('/admin/books/{book_id}')
def admin_book(book_id:str,admin:Admin,db:DB):
    b=db.get(Book,book_id)
    if not b:fail(404,'绘本不存在')
    return book_json(db,b,True)
@router.patch('/admin/versions/{version_id}')
def update_version(version_id:str,data:BookInput,admin:Admin,db:DB):
    v=get_draft(db,version_id);busy(db,v.id)
    if data.cover_id:
        m=db.get(MediaAsset,data.cover_id)
        if not m or m.kind!='image':fail(422,'封面必须是已上传图片')
    for k,val in data.model_dump().items():setattr(v,k,val)
    db.commit();return version_json(db,v)
@router.post('/admin/books/{book_id}/draft')
def revision(book_id:str,admin:Admin,db:DB):
    b=db.scalar(select(Book).where(Book.id==book_id).with_for_update())
    if not b:fail(404,'绘本不存在')
    versions=list(db.scalars(select(BookVersion).where(BookVersion.book_id==book_id).order_by(BookVersion.number.desc())))
    if not versions[0].published:return version_json(db,versions[0])
    old=db.get(BookVersion,b.published_version_id)
    v=BookVersion(book_id=b.id,number=versions[0].number+1,title=old.title,description=old.description,level=old.level,cover_id=old.cover_id)
    db.add(v);db.flush()
    for p in db.scalars(select(Page).where(Page.version_id==old.id)):
        values=page_json(p);values.pop('id');values['version_id']=v.id;db.add(Page(**values))
    db.commit();return version_json(db,v)
@router.post('/admin/books/{book_id}/archive')
def archive(book_id:str,admin:Admin,db:DB):
    b=db.get(Book,book_id)
    if not b:fail(404,'绘本不存在')
    if not b.published_version_id:fail(409,'草稿请使用删除')
    revision(book_id,admin,db)
    b.status='draft';db.commit();return {'ok':True}
@router.delete('/admin/books/{book_id}')
def remove_book(book_id:str,admin:Admin,db:DB):
    b=db.get(Book,book_id)
    if not b:fail(404,'绘本不存在')
    if b.status=='published':fail(409,'请先下架绘本')
    if b.published_version_id:
        b.status='deleted';db.commit();return {'ok':True}
    for v in db.scalars(select(BookVersion).where(BookVersion.book_id==b.id)):
        busy(db,v.id);db.execute(delete(Page).where(Page.version_id==v.id));db.delete(v)
    db.flush();db.delete(b);db.commit();return {'ok':True}

@router.post('/admin/versions/{version_id}/pages',status_code=201)
def add_page(version_id:str,admin:Admin,db:DB,position:int|None=None):
    v=get_draft(db,version_id);busy(db,v.id)
    pages=list(db.scalars(select(Page).where(Page.version_id==v.id)))
    if len(pages)>=100:fail(422,'最多 100 页')
    position=position if position is not None else len(pages)+1
    if not 1<=position<=len(pages)+1:fail(422,'插入位置无效')
    for other in sorted(pages,key=lambda p:p.position,reverse=True):
        if other.position>=position:other.position+=1;db.flush()
    p=Page(version_id=v.id,position=position,kind='display')
    db.add(p);db.commit();return page_json(p)
@router.patch('/admin/pages/{page_id}')
def edit_page(page_id:str,data:PageInput,admin:Admin,db:DB):
    p=db.get(Page,page_id)
    if not p:fail(404,'页面不存在')
    get_draft(db,p.version_id);busy(db,p.version_id)
    changes=data.model_dump(exclude_unset=True)
    if any(k!='reviewed' and getattr(p,k)!=v for k,v in changes.items()):p.reviewed=False
    for k,val in changes.items():
        if k in ['text','kind','audio_start_ms'] and val is None:fail(422,'字段不可为空')
        if k in ['image_id','audio_id'] and val:
            a=db.get(MediaAsset,val)
            if not a or a.kind!=('image' if k=='image_id' else 'audio'):fail(422,'媒体类型不匹配')
        setattr(p,k,val)
    if p.audio_id:
        a=db.get(MediaAsset,p.audio_id)
        end=p.audio_end_ms if p.audio_end_ms is not None else a.duration_ms
        if end is None or not 0<=p.audio_start_ms<end<=a.duration_ms:fail(422,'音频起止时间超出范围')
        p.audio_end_ms=end
    db.commit();return page_json(p)
@router.delete('/admin/pages/{page_id}')
def delete_page(page_id:str,admin:Admin,db:DB):
    p=db.get(Page,page_id)
    if not p:fail(404,'页面不存在')
    get_draft(db,p.version_id);busy(db,p.version_id)
    vid=p.version_id;db.delete(p);db.flush()
    for idx,other in enumerate(db.scalars(select(Page).where(Page.version_id==vid).order_by(Page.position)),1):
        other.position=idx
        # Shift in position order; UUID batch ordering can otherwise collide.
        db.flush()
    db.commit();return {'ok':True}

@router.post('/admin/versions/{version_id}/assets',status_code=201)
async def upload_asset(version_id:str,request:Request,admin:Admin,db:DB,file:UploadFile=File(),kind:str=Form()):
    get_draft(db,version_id)
    if kind not in ['image','audio']:fail(422,'请选择图片或音频')
    a=await save_upload(file,kind,admin.id,version_id,request.app.state.settings,db);db.commit()
    return {'id':a.id,'filename':a.filename,'duration_ms':a.duration_ms,'kind':a.kind}
@router.get('/admin/versions/{version_id}/assets')
def assets(version_id:str,admin:Admin,db:DB):
    v=db.get(BookVersion,version_id)
    if not v:fail(404,'版本不存在')
    versions=list(db.scalars(select(BookVersion.id).where(BookVersion.book_id==v.book_id)))
    return [{'id':a.id,'filename':a.filename,'kind':a.kind,'duration_ms':a.duration_ms} for a in db.scalars(select(MediaAsset).where(MediaAsset.version_id.in_(versions),MediaAsset.kind.in_(['audio','image'])))]
@router.post('/admin/versions/{version_id}/import',status_code=202)
async def import_pdf(version_id:str,request:Request,admin:Admin,db:DB,file:UploadFile=File()):
    get_draft(db,version_id);busy(db,version_id)
    if db.scalar(select(Page.id).where(Page.version_id==version_id)):fail(409,'已有页面不能重新导入覆盖，请新建绘本或手工增补页面')
    a=await save_upload(file,'pdf',admin.id,version_id,request.app.state.settings,db)
    j=Job(user_id=admin.id,kind='pdf',payload={'version_id':version_id,'asset_id':a.id});db.add(j);db.commit();return {'id':j.id,'status':j.status}

def publish_issues(db,v):
    issues=[];pages=list(db.scalars(select(Page).where(Page.version_id==v.id).order_by(Page.position)))
    if not v.title.strip():issues.append('请填写书名')
    if not v.cover_id and not any(p.image_id for p in pages):issues.append('请设置封面或上传页面图片')
    if not pages:issues.append('至少需要一个页面')
    for p in pages:
        prefix=f'第 {p.position} 页：'
        if not (p.image_id or p.text.strip() or p.audio_id):issues.append(prefix+'页面为空，请添加图片、文字或音频')
        if p.kind=='practice':
            if not p.text.strip():issues.append(prefix+'缺少标准英文')
        if p.audio_id:
            a=db.get(MediaAsset,p.audio_id)
            if not a or not p.audio_end_ms or not 0<=p.audio_start_ms<p.audio_end_ms<=a.duration_ms:issues.append(prefix+'音频区间无效')
    return issues
@router.get('/admin/versions/{version_id}/check')
def check(version_id:str,admin:Admin,db:DB):
    v=db.get(BookVersion,version_id)
    if not v:fail(404,'版本不存在')
    return {'issues':publish_issues(db,v)}
@router.post('/admin/versions/{version_id}/publish')
def publish(version_id:str,admin:Admin,db:DB):
    v=get_draft(db,version_id);busy(db,version_id);issues=publish_issues(db,v)
    if issues:raise __import__('fastapi').HTTPException(422,{'message':'发布检查未通过','issues':issues})
    if not v.cover_id:v.cover_id=db.scalar(select(Page.image_id).where(Page.version_id==v.id,Page.image_id.is_not(None)).order_by(Page.position))
    v.published=True;b=db.get(Book,v.book_id);b.published_version_id=v.id;b.status='published';db.commit();return book_json(db,b,True)

@router.get('/books')
def books(user:Current,db:DB,q:str='',level:str=''):
    result=[]
    for b in db.scalars(select(Book).where(Book.status=='published').order_by(Book.created_at.desc())):
        v=db.get(BookVersion,b.published_version_id)
        if (not q or q.casefold() in v.title.casefold()) and (not level or v.level==level):result.append(book_json(db,b))
    return result
@router.get('/books/{book_id}')
def book(book_id:str,user:Current,db:DB):
    b=db.get(Book,book_id)
    if not b or b.status!='published':fail(404,'绘本暂不可用')
    return book_json(db,b)
@router.get('/jobs/{job_id}')
def job_status(job_id:str,user:Current,db:DB):
    j=db.get(Job,job_id)
    if not j or (user.role!='admin' and j.user_id!=user.id):fail(404,'任务不存在')
    return {k:getattr(j,k) for k in ['id','status','progress','error','result','kind']}


class PageOrder(BaseModel):
    page_ids:list[str]=Field(min_length=1,max_length=100)

@router.put('/admin/versions/{version_id}/order')
def order_pages(version_id:str,data:PageOrder,admin:Admin,db:DB):
    get_draft(db,version_id);busy(db,version_id)
    pages={p.id:p for p in db.scalars(select(Page).where(Page.version_id==version_id))}
    if len(data.page_ids)!=len(pages) or set(data.page_ids)!=set(pages):fail(422,'必须包含全部页面且不能重复')
    for i,p in enumerate(pages.values(),1):p.position=1000+i
    db.flush()
    for i,pid in enumerate(data.page_ids,1):pages[pid].position=i
    db.commit();return {'ok':True}

class AudioBinding(BaseModel):
    page_id:str
    audio_id:str
    start_ms:int=Field(ge=0)
    end_ms:int=Field(gt=0)
class AudioBindings(BaseModel):
    bindings:list[AudioBinding]=Field(min_length=1,max_length=100)
    overwrite:bool=False

@router.put('/admin/versions/{version_id}/audio-bindings')
def bind_audio(version_id:str,data:AudioBindings,admin:Admin,db:DB):
    v=get_draft(db,version_id);busy(db,version_id)
    versions=set(db.scalars(select(BookVersion.id).where(BookVersion.book_id==v.book_id)))
    seen=set()
    for item in data.bindings:
        p=db.get(Page,item.page_id);a=db.get(MediaAsset,item.audio_id)
        if not p or p.version_id!=version_id or p.id in seen:fail(422,'页面无效或重复')
        seen.add(p.id)
        if p.audio_id and not data.overwrite:fail(409,'部分页面已有音频，请明确选择覆盖')
        if not a or a.kind!='audio' or a.version_id not in versions:fail(422,'音频不属于此绘本')
        if not 0<=item.start_ms<item.end_ms<=(a.duration_ms or 0):fail(422,'音频区间无效')
        p.audio_id=a.id;p.audio_start_ms=item.start_ms;p.audio_end_ms=item.end_ms
    db.commit();return {'ok':True}
