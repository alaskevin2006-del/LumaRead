"""Full-sequence, final-layer WavLM cosine DTW. No transcription or speaker score."""
import numpy as np
from numba import njit

MODEL='microsoft/wavlm-large'
REVISION='c1423ed94bb01d80a3f5ce5bc39f6026a0f4828c'
PREPROCESS='mono16k-edge-rms-v1'
METHOD='wavlm-last-cosine-dtw-path-v1'

def prepare(x):
    x=np.asarray(x,dtype=np.float32)
    if x.ndim!=1 or not 4800<=len(x)<=960000 or not np.isfinite(x).all():
        raise ValueError('音频须为 0.3–60 秒的完整录音，请重新录制')
    if np.mean(np.abs(x)>=.995)>.03:
        raise ValueError('音频严重削波，请降低录音音量后重试')
    # Energy gate is deliberately not described as speech recognition.
    frames=x[:len(x)//320*320].reshape(-1,320)
    energy=np.sqrt(np.mean(frames**2,axis=1))
    threshold=max(.0015,float(np.max(energy))*.025)
    active=np.flatnonzero(energy>threshold)
    if len(active)<10:raise ValueError('音频过轻或没有足够有效声音，请靠近麦克风重录')
    begin=max(0,int(active[0])*320-800);end=min(len(x),(int(active[-1])+1)*320+800)
    y=x[begin:end].copy()
    y=(y-y.mean())/np.sqrt(y.var()+1e-7)
    return y,begin/16000

@njit(cache=True)
def _path(cost):
    n,m=cost.shape
    acc=np.full((n+1,m+1),np.inf,np.float32);acc[0,0]=0
    back=np.zeros((n,m),np.uint8)
    for i in range(n):
        for j in range(m):
            a,b,c=acc[i,j],acc[i,j+1],acc[i+1,j]
            if a<=b and a<=c:best=a;direction=0
            elif b<=c:best=b;direction=1
            else:best=c;direction=2
            acc[i+1,j+1]=cost[i,j]+best;back[i,j]=direction
    i,j=n-1,m-1;path=[]
    while i>=0 and j>=0:
        path.append((i,j));d=back[i,j]
        if d==0:i-=1;j-=1
        elif d==1:i-=1
        else:j-=1
    return acc[n,m]/len(path),path[::-1]

def align(reference,recording):
    if min(len(reference),len(recording))<1 or max(len(reference),len(recording))>3000:
        raise ValueError('音频长度无法比对')
    if max(len(reference),len(recording))/min(len(reference),len(recording))>4:
        raise ValueError('两段音频时长相差过大，请读完整个片段后重试')
    a=reference/np.maximum(np.linalg.norm(reference,axis=1,keepdims=True),1e-8)
    b=recording/np.maximum(np.linalg.norm(recording,axis=1,keepdims=True),1e-8)
    cost=np.clip(1-a@b.T,0,2).astype(np.float32)
    return _path(cost)

def compare(a,b,reference_offset,recording_offset,reference_duration,recording_duration):
    distance,path=align(a,b)
    segments=[]
    for start in range(0,len(a),100):
        pairs=[(i,j) for i,j in path if start<=i<start+100]
        if not pairs:continue
        i=np.array([p[0] for p in pairs]);j=np.array([p[1] for p in pairs])
        aa=a[i];bb=b[j]
        d=np.clip(1-np.sum(aa*bb,axis=1)/(np.maximum(np.linalg.norm(aa,axis=1)*np.linalg.norm(bb,axis=1),1e-8)),0,2).mean()
        segments.append({'reference_start':round(reference_offset+i.min()*.02,3),
                         'reference_end':round(reference_offset+min((i.max()+1)*.02,reference_duration),3),
                         'recording_start':round(recording_offset+j.min()*.02,3),
                         'recording_end':round(recording_offset+min((j.max()+1)*.02,recording_duration),3),
                         'similarity':round(float(np.clip(1-d,0,1)*100),1)})
    return {'mode':'reference_similarity','overall_score':round(float(np.clip(1-distance,0,1)*100),1),
            'mean_cosine_distance':float(distance),'duration_ratio':round(recording_duration/reference_duration,3),
            'segments':segments,'model':MODEL,'model_revision':REVISION,'preprocessing_version':PREPROCESS,
            'scoring_config_version':METHOD,'experimental':True}
