import json,subprocess,shutil,wave,tempfile,math
from pathlib import Path
from fastapi import APIRouter,Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from .auth import DB,Current,fail
from .models import MediaAsset,Book,BookVersion,Page,ReadingSession,uid

router=APIRouter(prefix='/api')
MIMES={'.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.mp3':'audio/mpeg','.wav':'audio/wav','.m4a':'audio/mp4','.mp4':'audio/mp4','.webm':'audio/webm','.ogg':'audio/ogg'}

def duration(path,decode_limit=62):
    if Path(path).suffix.lower()=='.wav':
        try:
            with wave.open(str(path),'rb') as w:return round(w.getnframes()/w.getframerate()*1000)
        except (wave.Error,EOFError):pass
    try:
        p=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type','-of','json',str(path)],capture_output=True,text=True,timeout=20,check=True)
        data=json.loads(p.stdout)
        if not any(x.get('codec_type')=='audio' for x in data.get('streams',[])):raise ValueError()
        value=data.get('format',{}).get('duration')
        if value is not None and math.isfinite(float(value)) and float(value)>0:
            return round(float(value)*1000)
        # MediaRecorder writes a streaming WebM without duration metadata. Decode
        # into a bounded temporary WAV, never trust container metadata to exist.
        with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f:decoded=Path(f.name)
        try:
            subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(path),'-t',str(decode_limit),'-vn','-ar','16000','-ac','1','-c:a','pcm_s16le',str(decoded)],capture_output=True,timeout=30,check=True)
            with wave.open(str(decoded),'rb') as audio:return round(audio.getnframes()/audio.getframerate()*1000)
        finally:decoded.unlink(missing_ok=True)
    except (OSError,ValueError,KeyError,subprocess.SubprocessError):fail(422,'无法解析音频，请上传有效的 MP3、WAV、M4A 或浏览器录音')

async def save_upload(file,kind,user_id,version_id,settings,db):
    ext=Path(file.filename or '').suffix.lower()
    allowed={'pdf':{'.pdf'},'image':{'.png','.jpg','.jpeg','.webp'},'audio':{'.mp3','.wav','.m4a','.mp4','.webm','.ogg'},'recording':{'.mp3','.wav','.m4a','.mp4','.webm','.ogg'}}
    if kind not in allowed or ext not in allowed[kind]:fail(422,'文件格式不支持')
    limit=(50 if kind=='pdf' else 12 if kind=='image' else 20 if kind=='recording' else 100)*1024*1024
    key=uid()+ext;path=Path(settings.media_dir)/key;size=0
    try:
        with path.open('wb') as out:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>limit:fail(413,f'文件超过 {limit//1024//1024} MB 限制')
                out.write(chunk)
        if size==0:fail(422,'文件为空')
        length=None
        if kind in ['audio','recording']:
            length=duration(path,62 if kind=='recording' else 3601)
            if kind=='recording' and (length<300 or length>61000):fail(422,'录音须在 0.3–60 秒之间')
            if kind=='audio' and length>3600000:fail(422,'原音最长支持 60 分钟，请拆分上传')
        if kind=='image':
            import pymupdf
            try:
                pix=pymupdf.Pixmap(str(path))
                if pix.width*pix.height>40_000_000:fail(422,'图片尺寸过大')
            except RuntimeError:fail(422,'图片无法读取')
        asset=MediaAsset(user_id=user_id,version_id=version_id,kind=kind,filename=Path(file.filename).name[:160],path=key,mime=MIMES[ext],duration_ms=length)
        db.add(asset);db.flush();return asset
    except BaseException:
        path.unlink(missing_ok=True);raise

def can_read_version(db,user,version_id):
    if user.role=='admin':return True
    v=db.get(BookVersion,version_id)
    if not v or not v.published:return False
    b=db.get(Book,v.book_id)
    if b.status=='published' and b.published_version_id==v.id:return True
    return db.scalar(select(ReadingSession.id).where(ReadingSession.user_id==user.id,ReadingSession.version_id==v.id)) is not None

@router.get('/media/{asset_id}')
def media(asset_id:str,request:Request,user:Current,db:DB):
    asset=db.get(MediaAsset,asset_id)
    if not asset:fail(404,'文件不存在')
    if user.role!='admin':
        if asset.kind=='recording':
            if asset.user_id!=user.id:fail(404,'文件不存在')
        elif asset.kind=='pdf':fail(404,'文件不存在')
        else:
            # Revision copies can reference original assets; authorization follows references.
            candidates=set(db.scalars(select(Page.version_id).where((Page.image_id==asset.id)|(Page.audio_id==asset.id))))
            candidates.update(db.scalars(select(BookVersion.id).where(BookVersion.cover_id==asset.id)))
            if not any(can_read_version(db,user,v) for v in candidates):fail(404,'文件不存在')
    path=Path(request.app.state.settings.media_dir)/asset.path
    if not path.is_file():fail(404,'文件已过期或不存在')
    return FileResponse(path,media_type=asset.mime,headers={'Content-Disposition':'inline','Cache-Control':'private, no-store'})
