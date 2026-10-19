import time,logging
from pathlib import Path
from datetime import timedelta
from sqlalchemy import select,update
from .models import Job,MediaAsset,Page,BookVersion,now,uid
log=logging.getLogger('lumaread.worker')

def pdf_job(app,job_id):
    import pymupdf
    with app.state.db() as db:
        j=db.get(Job,job_id);v=db.scalar(select(BookVersion).where(BookVersion.id==j.payload['version_id']).with_for_update());a=db.get(MediaAsset,j.payload['asset_id'])
        if not v or v.published:raise ValueError('草稿已不存在或已发布')
        doc=pymupdf.open(Path(app.state.settings.media_dir)/a.path)
        if doc.is_encrypted or not 1<=len(doc)<=100:raise ValueError('PDF 加密或页数不在 1–100 范围')
        failures=[]
        for idx in range(len(doc)):
            v=db.scalar(select(BookVersion).where(BookVersion.id==j.payload['version_id']).with_for_update().execution_options(populate_existing=True))
            if not v or v.published:raise ValueError('已发布版本不可重新导入')
            if db.scalar(select(Page.id).where(Page.version_id==v.id,Page.position==idx+1)):continue
            try:
                source=doc[idx];scale=min(1.5,1400/max(source.rect.width,source.rect.height))
                pix=source.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
                name=uid()+'.png';pix.save(str(Path(app.state.settings.media_dir)/name))
                image=MediaAsset(user_id=j.user_id,version_id=v.id,kind='image',filename=f'page-{idx+1}.png',path=name,mime='image/png')
                db.add(image);db.flush()
                db.add(Page(version_id=v.id,position=idx+1,image_id=image.id,text=source.get_text().strip()[:3000]))
                if not v.cover_id:v.cover_id=image.id
            except Exception:failures.append(idx+1)
            j.progress=round((idx+1)/len(doc)*100);db.commit()
        j.result={'pages':len(doc),'failed_pages':failures};db.commit();doc.close()
        if failures:raise ValueError('部分页面导入失败：'+','.join(map(str,failures))+'；已完成页面保留，请手工补充')

def run_job(app,job_id):
    with app.state.db() as db:
        claimed=db.execute(update(Job).where(Job.id==job_id,Job.status=='queued').values(status='running',started_at=now())).rowcount
        db.commit()
        if not claimed:return
        kind=db.get(Job,job_id).kind
    try:
        if kind=='pdf':pdf_job(app,job_id)
        elif kind=='evaluation':
            from .evaluators import evaluation_job
            evaluation_job(app,job_id)
        with app.state.db() as db:
            j=db.get(Job,job_id);j.status='succeeded';j.progress=100;db.commit()
    except Exception as e:
        log.warning('job %s failed: %s',job_id,type(e).__name__)
        with app.state.db() as db:
            j=db.get(Job,job_id);j.status='failed';j.error=str(e)[:300] if isinstance(e,ValueError) else '处理失败，请检查文件或稍后重试';db.commit()
            if kind=='evaluation':
                from .models import ReadingAttempt
                for a in db.scalars(select(ReadingAttempt).where(ReadingAttempt.job_id==job_id)):a.status='failed'
                db.commit()

def main():
    from .main import create_app
    app=create_app()
    # Single worker container: recover jobs interrupted by a previous process exit.
    with app.state.db() as db:db.execute(update(Job).where(Job.status=='running').values(status='queued'));db.commit()
    while True:
        with app.state.db() as db:ids=list(db.scalars(select(Job.id).where(Job.status=='queued').order_by(Job.created_at).limit(1)))
        for jid in ids:run_job(app,jid)
        time.sleep(1)
if __name__=='__main__':main()
