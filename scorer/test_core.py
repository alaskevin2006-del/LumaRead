import numpy as np
import pytest
from core import align, prepare

def test_self_and_speed_alignment():
    a=np.eye(8,dtype=np.float32)
    score,path=align(a,a)
    assert score==pytest.approx(0,abs=1e-6)
    assert len(path)==8
    stretched=np.repeat(a,2,axis=0)
    assert align(a,stretched)[0]==pytest.approx(0,abs=1e-6)
    assert align(a,-a)[0]>0.5

def test_silence_clipping_and_edge_trim():
    with pytest.raises(ValueError):prepare(np.zeros(16000,dtype=np.float32))
    with pytest.raises(ValueError):prepare(np.ones(16000,dtype=np.float32))
    x=.1*np.sin(np.arange(16000)*.12).astype(np.float32)
    y,offset=prepare(np.concatenate([np.zeros(3200),x,np.zeros(3200)]))
    assert offset>0 and len(y)<22400
    quiet,_=prepare(x*.3)
    assert np.allclose(quiet,prepare(x)[0],atol=.001)
    with pytest.raises(ValueError):prepare(np.zeros(16000*62))

def test_recorder_encoder_duration_tolerance():
    # Browser timer/container overhead must not reject a legitimate 60-second take.
    x=.1*np.sin(np.arange(int(60.25*16000))*.12).astype(np.float32)
    y,_=prepare(x)
    assert len(y)==len(x)
