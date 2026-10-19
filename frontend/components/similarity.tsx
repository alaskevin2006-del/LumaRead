'use client';
import {useEffect,useRef,useState} from 'react';
import {Result,media} from '../lib/api';
import {Button,Notice} from './ui';

export function SimilarityResult({result,disabled=false}:{result:Result;disabled?:boolean}){
 const player=useRef<HTMLAudioElement|null>(null),[error,setError]=useState('');
 useEffect(()=>{const stop=()=>player.current?.pause();window.addEventListener('luma:playback',stop);return()=>{stop();window.removeEventListener('luma:playback',stop);};},[]);
 useEffect(()=>{player.current?.pause();},[result,disabled]);
 async function play(id:string|undefined,start:number,end:number){
  if(!id)return;window.dispatchEvent(new Event('luma:playback'));setError('');
  const a=new Audio(media(id));player.current=a;
  a.onloadedmetadata=()=>{a.currentTime=start;};a.ontimeupdate=()=>{if(a.currentTime>=end)a.pause();};
  a.onerror=()=>setError('录音无法播放，可能已超过 30 天保留期或网络暂不可用。');
  try{await a.play();}catch(e){if((e as DOMException).name!=='AbortError')setError('暂时无法播放，请重试。');}
 }
 return <div className="card similarity-result"><div className="score">{result.overall_score.toFixed(1)}<small>原音相似度指数</small></div><p>数值越高，声音特征越贴近本页原音。它不是发音正确率，也没有及格线。</p><Notice>实验比对 · 尚未经过儿童样例标定。音色、设备和背景声音可能影响结果。</Notice><p className="small muted">逐段对照听一听。片段按时间划分，不代表单词错误。</p><div className="stack">{result.segments?.map((s,i)=><div key={i} className="card"><b>原音 {s.reference_start.toFixed(1)}–{s.reference_end.toFixed(1)} 秒 · 相似度 {s.similarity.toFixed(1)}</b><div className="row"><Button secondary disabled={disabled} onClick={()=>play(result.reference_audio_id,s.reference_start+(result.reference_offset||0),s.reference_end+(result.reference_offset||0))}>听原音片段</Button><Button secondary disabled={disabled} onClick={()=>play(result.recording_audio_id,s.recording_start,s.recording_end)}>听我的对应录音</Button></div></div>)}</div><Notice error>{error}</Notice><small className="muted">WavLM-Large · 余弦距离与时间对齐 · <a href="https://huggingface.co/microsoft/wavlm-large" target="_blank" rel="noreferrer">模型来源</a> · CC BY-SA 3.0</small></div>;
}
