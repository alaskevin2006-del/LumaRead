"""Versioned reference inputs and strict result boundary for the isolated scorer."""
import math
from sqlalchemy import select
from .models import MediaAsset,BookVersion
from .auth import fail

REVISION='c1423ed94bb01d80a3f5ce5bc39f6026a0f4828c'
MODE='reference_similarity'

def reference_snapshot(db,page,strict=True):
    a=db.get(MediaAsset,page.audio_id) if page.audio_id else None
    v=db.get(BookVersion,page.version_id)
    owner=db.get(BookVersion,a.version_id) if a and a.version_id else None
    end=page.audio_end_ms or (a.duration_ms if a else 0)
    if not (a and a.kind=='audio' and v and owner and v.book_id==owner.book_id
            and a.duration_ms and 0<=page.audio_start_ms<end<=a.duration_ms
            and 300<=end-page.audio_start_ms<=60000):
        if strict:fail(422,'本页需要设置 0.3–60 秒的有效标准音频区间，才能跟读比对')
        return None
    return {'asset_id':a.id,'start_ms':page.audio_start_ms,'end_ms':end,'model_revision':REVISION}

def normalize_reference(data,reference_seconds,recording_seconds):
    def number(x,low,high):
        if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not low<=x<=high:
            raise ValueError('比对服务返回了无效结果，请重试')
        return x
    if not isinstance(data,dict) or data.get('mode')!=MODE or data.get('model_revision')!=REVISION or data.get('model')!='microsoft/wavlm-large':
        raise ValueError('比对服务模型或结果类型不匹配')
    if data.get('preprocessing_version')!='mono16k-edge-rms-v1' or data.get('scoring_config_version')!='wavlm-last-cosine-dtw-path-v1':
        raise ValueError('比对方法版本不匹配')
    score=number(data.get('overall_score'),0,100);distance=number(data.get('mean_cosine_distance'),0,2)
    if abs(score-round(max(0,1-distance)*100,1))>.11:raise ValueError('相似度与距离不一致')
    ratio=number(data.get('duration_ratio'),.001,100)
    segments=data.get('segments')
    if not isinstance(segments,list) or not 1<=len(segments)<=31:raise ValueError('比对服务没有提供有效片段')
    clean=[];last_reference=-1;last_recording=-1
    for part in segments:
        if not isinstance(part,dict):raise ValueError('片段格式错误')
        rs=number(part.get('reference_start'),0,reference_seconds);re=number(part.get('reference_end'),0,reference_seconds+.03)
        ss=number(part.get('recording_start'),0,recording_seconds);se=number(part.get('recording_end'),0,recording_seconds+.03)
        if re<=rs or se<=ss or rs<last_reference or ss<last_recording:raise ValueError('比对片段区间无效')
        last_reference=rs;last_recording=ss
        clean.append(dict(reference_start=rs,reference_end=re,recording_start=ss,recording_end=se,similarity=number(part.get('similarity'),0,100)))
    return {k:data[k] for k in ['mode','model','model_revision','preprocessing_version','scoring_config_version']}|dict(
        status='succeeded',overall_score=score,mean_cosine_distance=distance,duration_ratio=ratio,
        segments=clean,experimental=True,words=[],accuracy=None,fluency=None,completeness=None,provider=MODE)
