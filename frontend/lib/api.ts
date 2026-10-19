export type User={id:string;username:string;name:string;class_name:string;role:string;active:boolean;must_change_password:boolean};
export type Page={id:string;position:number;kind:string;text:string;image_id:string|null;audio_id:string|null;audio_start_ms:number;audio_end_ms:number|null;reviewed:boolean};
export type Version={id:string;title:string;description:string;level:string;cover_id:string|null;pages:Page[];number:number;published:boolean};
export type Book={id:string;status:string;published:Version|null;draft:Version|null};
export type Word={text:string;char_start:number;char_end:number;score:number|null;level:string};
export type Result={mode?:string;segments?:{reference_start:number;reference_end:number;recording_start:number;recording_end:number;similarity:number}[];reference_audio_id?:string;recording_audio_id?:string;reference_offset?:number;overall_score:number;accuracy:number|null;fluency:number|null;completeness:number|null;words:Word[];experimental?:boolean};
export type Reading={scoring_mode?:string;required_page_ids?:string[]|null;id:string;book_id:string;current_page:number;completed_at:string|null;created_at:string;title:string;level:string;cover_id:string|null;page_count:number;completed_pages:string[];version:Version;latest_results:Record<string,Result>;pending_jobs:Record<string,string>};
export type Job={id:string;status:string;error:string;progress:number;result:Result&{raw?:unknown;failed_pages?:number[]}};
export class ApiError extends Error{constructor(public status:number,public detail:unknown){super(typeof detail==='string'?detail:(detail as {message?:string})?.message||'操作未完成，请检查输入后重试');}}
export async function api<T=any>(path:string,method='GET',data?:unknown):Promise<T>{
 const form=data instanceof FormData;
 const r=await fetch('/api'+path,{method,credentials:'same-origin',headers:{'X-LumaRead':'1',...(!form&&data!==undefined?{'Content-Type':'application/json'}:{})},body:data===undefined?undefined:form?data:JSON.stringify(data),cache:'no-store'});
 const json=await r.json().catch(()=>({detail:'网络响应异常'}));
 if(!r.ok){if(r.status===401&&path!='/auth/login')window.dispatchEvent(new Event('luma:unauthorized'));throw new ApiError(r.status,json.detail);}
 return json;
}
export const media=(id:string|null|undefined)=>id?'/api/media/'+id:'/sample-book.png';
export const go=(route:string)=>{window.location.hash=route;};
export async function upload(path:string,file:File|Blob,extra:Record<string,string>={},name?:string){const f=new FormData();f.append('file',file,name||((file as File).name||'recording.webm'));for(const [k,v] of Object.entries(extra))f.append(k,v);return api(path,'POST',f);}
