"""Resource/mechanics probe; generated signal is NOT pronunciation validation."""
import json,time,resource
import numpy as np
from service import load_model,features
from core import prepare,compare

def report(**data):
    print(json.dumps(data|{'rss_peak_mb':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1)}),flush=True)

start=time.monotonic();load_model();report(stage='loaded',seconds=round(time.monotonic()-start,2))
for duration in [2,10,30,60]:
    # Chirp/amplitude modulation exercises full sequence allocation, no chunking.
    t=np.arange(duration*16000,dtype=np.float32)/16000
    signal=(.12*np.sin(2*np.pi*(170*t+20*t*t))*(.6+.4*np.cos(2*np.pi*3*t))).astype(np.float32)
    x,offset=prepare(signal);start=time.monotonic();a=features(x)
    result=compare(a,a,offset,offset,len(x)/16000,len(x)/16000)
    report(stage='inference',duration=duration,seconds=round(time.monotonic()-start,2),self_similarity=result['overall_score'],frames=len(a))
