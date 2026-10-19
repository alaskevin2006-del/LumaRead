import re,json,base64,subprocess,math,wave,array
from pathlib import Path
import httpx
from sqlalchemy import select
from .models import Job,ReadingAttempt,MediaAsset

def word_tokens(text):return [{'token_index':i,'text':m.group(),'char_start':m.start(),'char_end':m.end()} for i,m in enumerate(re.finditer(r"[A-Za-z]+(?:['’-][A-Za-z]+)*",text))]
def numeric(value):
    if value is None:return None
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not 0<=value<=100:raise ValueError('评分服务返回了无效分值')
    return round(value,1)
def normalize(data,text,provider,green=80,orange=60):
    tokens=word_tokens(text);scores=data.get('words')
    if not isinstance(scores,list) or len(scores)!=len(tokens):raise ValueError('评分服务未提供完整逐词结果，不能作为正式成绩')
    total=numeric(data.get('overall_score'))
    if total is None:raise ValueError('评分服务未提供总分')
    for token,word in zip(tokens,scores):
        if not isinstance(word,dict):raise ValueError('逐词结果格式错误')
        if word.get('text') and word['text'].casefold()!=token['text'].casefold():raise ValueError('评分结果与标准单词顺序不一致')
        score=numeric(word.get('score'))
        token.update(score=score,level='unknown' if score is None else 'green' if score>=green else 'orange' if score>=orange else 'red',status=word.get('status','uncertain' if score is None else 'assessed'))
    if not any(x['score'] is not None for x in tokens):raise ValueError('未能可靠评估任何单词，请重新录音')
    return {'status':'succeeded','overall_score':total,'accuracy':numeric(data.get('accuracy')),'fluency':numeric(data.get('fluency')),'completeness':numeric(data.get('completeness')),'words':tokens,'provider':provider,'provider_version':data.get('provider_version','external'),'scoring_config_version':f'v1-{green}-{orange}','experimental':bool(data.get('experimental',False))}

def azure_evaluate(settings,wav,text):
    assessment={'ReferenceText':text,'GradingSystem':'HundredMark','Granularity':'Phoneme','EnableMiscue':True}
    if not settings.azure_key or not re.fullmatch('[a-z0-9-]+',settings.azure_region):raise ValueError('Azure 评分尚未配置')
    headers={'Ocp-Apim-Subscription-Key':settings.azure_key,'Content-Type':'audio/wav; codecs=audio/pcm; samplerate=16000','Pronunciation-Assessment':base64.b64encode(json.dumps(assessment).encode()).decode()}
    response=httpx.post(f'https://{settings.azure_region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1',params={'language':'en-US','format':'detailed'},headers=headers,content=wav.read_bytes(),timeout=90)
    response.raise_for_status();raw=response.json()
    if raw.get('RecognitionStatus')!='Success' or not raw.get('NBest'):raise ValueError('未能听清录音，请按本页文字重读')
    item=raw['NBest'][0];score=item.get('PronunciationAssessment',{})
    tokens=word_tokens(text);words=[]
    # Azure emits omitted words with their reference position; insertions are not reference tokens.
    for w in item.get('Words',[]):
        a=w.get('PronunciationAssessment',{})
        if a.get('ErrorType')=='Insertion':continue
        words.append({'text':w.get('Word',''),'score':a.get('AccuracyScore'),'status':'omitted' if a.get('ErrorType')=='Omission' else 'assessed'})
    data={'overall_score':score.get('PronScore'),'accuracy':score.get('AccuracyScore'),'fluency':score.get('FluencyScore'),'completeness':score.get('CompletenessScore'),'words':words,'provider_version':'azure-rest-v1'}
    if score.get('CompletenessScore',0)<10:raise ValueError('录音与本页文字差异过大，请重新跟读')
    return data,raw

def evaluation_job(app,job_id):
    settings=app.state.settings
    with app.state.db() as db:
        j=db.get(Job,job_id);payload=j.payload;a=db.get(MediaAsset,payload['asset_id']);src=Path(settings.media_dir)/a.path;text=payload['reference_text']
    wav=src.with_suffix('.normalized.wav')
    try:
        subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(src),'-t','61','-ar','16000','-ac','1','-c:a','pcm_s16le',str(wav)],capture_output=True,timeout=30,check=True)
        with wave.open(str(wav),'rb') as audio:
            samples=array.array('h',audio.readframes(audio.getnframes()))
            rms=math.sqrt(sum(x*x for x in samples)/max(1,len(samples)))
            if rms<35:raise ValueError('没有听到有效语音，请靠近麦克风重录')
        if settings.speech_provider=='azure':data,raw=azure_evaluate(settings,wav,text)
        elif settings.speech_provider=='remote':
            with wav.open('rb') as audio:
                response=httpx.post(settings.speech_url.rstrip('/')+'/evaluate',files={'file':('recording.wav',audio,'audio/wav')},data={'reference_text':text},timeout=180)
            response.raise_for_status();data=response.json();raw=data
        else:raise ValueError('真实评分服务尚未配置')
        result=normalize(data,text,settings.speech_provider,settings.green_threshold,settings.orange_threshold)
        with app.state.db() as db:
            j=db.get(Job,job_id);j.result={**result,**({'raw':raw} if payload.get('test') else {})}
            for attempt in db.scalars(select(ReadingAttempt).where(ReadingAttempt.job_id==job_id)):attempt.status='succeeded';attempt.result=result
            db.commit()
    finally:wav.unlink(missing_ok=True)
