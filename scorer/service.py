import hashlib,json,os,subprocess,tempfile,threading,time
from pathlib import Path
import numpy as np
from fastapi import FastAPI,UploadFile,File,Form,HTTPException
from core import MODEL,REVISION,PREPROCESS,prepare,compare

app=FastAPI(docs_url=None,redoc_url=None)
lock=threading.Lock()
model=None
cache=Path(os.environ.get('FEATURE_CACHE','/cache/features'))

def load_model():
    global model
    if model is None:
        import torch
        from transformers import WavLMModel
        torch.set_num_threads(1)
        source=os.environ.get('MODEL_PATH',MODEL)
        if source!=MODEL:
            if (Path(source)/'REVISION').read_text().strip()!=REVISION:
                raise RuntimeError('Model revision manifest mismatch')
        model=WavLMModel.from_pretrained(source,revision=REVISION,low_cpu_mem_usage=True,
            torch_dtype=torch.float32,local_files_only=source!=MODEL).eval()
    return model

def features(x):
    import torch
    with torch.inference_mode():
        return load_model()(torch.from_numpy(x).unsqueeze(0)).last_hidden_state[0].cpu().numpy()

def decode(data):
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'input';path.write_bytes(data)
        p=subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(path),'-t','61','-vn','-ar','16000','-ac','1','-f','f32le','pipe:1'],capture_output=True,timeout=35)
        if p.returncode or not p.stdout:raise ValueError('音频损坏或不完整，请重新录制或上传')
        return prepare(np.frombuffer(p.stdout,dtype='<f4'))

def evaluate(reference,recording,reference_key):
    cache.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(reference+reference_key.encode()+REVISION.encode()+PREPROCESS.encode()).hexdigest()
    dest=cache/(digest+'.npz')
    if dest.exists():
        with np.load(dest,allow_pickle=False) as saved:
            a=saved['features'];ao=float(saved['offset']);ad=float(saved['duration'])
        os.utime(dest,None)
    else:
        try:x,ao=decode(reference)
        except ValueError as e:raise ValueError('标准音频不可用：'+str(e)) from e
        ad=len(x)/16000;a=features(x)
        np.savez(dest,features=a,offset=ao,duration=ad)
        files=sorted(cache.glob('*.npz'),key=lambda p:p.stat().st_mtime,reverse=True);size=0
        for p in files:
            size+=p.stat().st_size
            if size>512*1024*1024:p.unlink(missing_ok=True)
    y,bo=decode(recording);b=features(y)
    return compare(a,b,ao,bo,ad,len(y)/16000)

@app.get('/health')
def health():return {'ready':model is not None,'model_revision':REVISION}

@app.post('/evaluate')
def endpoint(reference:UploadFile=File(),recording:UploadFile=File(),reference_key:str=Form(),model_revision:str=Form()):
    if model_revision!=REVISION:raise HTTPException(409,'比对模型版本不匹配，请联系管理员')
    if len(reference_key)>200:raise HTTPException(422,'参考标识无效')
    # No waiting thread queue: the application worker already serializes jobs.
    if not lock.acquire(blocking=False):raise HTTPException(503,'比对服务忙，请稍后重试')
    try:
        a=reference.file.read(20*1024*1024+1);b=recording.file.read(20*1024*1024+1)
        if max(len(a),len(b))>20*1024*1024:raise ValueError('音频文件过大')
        start=time.monotonic();result=evaluate(a,b,reference_key)
        result['processing_seconds']=round(time.monotonic()-start,3)
        return result
    except ValueError as e:raise HTTPException(422,str(e)) from e
    finally:lock.release()
