import io,wave
import numpy as np
import pytest
import service
from core import REVISION
from fastapi.testclient import TestClient

def signal():
    buf=io.BytesIO()
    with wave.open(buf,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
        w.writeframes((np.sin(np.arange(32000)*.12)*5000).astype('<i2').tobytes())
    return buf.getvalue()

def test_cache_and_silence_boundary(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'cache',tmp_path)
    calls=[]
    def features(x):
        calls.append(len(x));return np.eye(8,dtype=np.float32)
    monkeypatch.setattr(service,'features',features)
    data=signal();r=service.evaluate(data,data,'page:1000:3000')
    assert r['overall_score']==pytest.approx(100)
    service.evaluate(data,data,'page:1000:3000')
    assert len(calls)==3  # first reference, first recording, second recording
    service.evaluate(data,data,'page:2000:4000')
    assert len(calls)==5
    with pytest.raises(ValueError):service.decode(b'broken')

def test_version_and_queue_boundary():
    c=TestClient(service.app);files={'reference':('r.wav',signal()),'recording':('s.wav',signal())}
    assert c.post('/evaluate',files=files,data={'reference_key':'p','model_revision':'wrong'}).status_code==409
    service.lock.acquire()
    try:assert c.post('/evaluate',files=files,data={'reference_key':'p','model_revision':REVISION}).status_code==503
    finally:service.lock.release()
