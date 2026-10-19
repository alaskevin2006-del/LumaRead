'use client';
import {useEffect,useState} from 'react';
import {api,go,User} from '../lib/api';
import {Brand,Button,Notice,Loading} from '../components/ui';
import {Student} from '../components/student';
import {Admin} from '../components/admin';
export default function App(){
 const [user,setUser]=useState<User|null>(null),[loading,setLoading]=useState(true),[route,setRoute]=useState('/'),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{const change=()=>{setRoute(location.hash.slice(1)||'/');setError('');};change();window.addEventListener('hashchange',change);const expired=()=>{setUser(null);setError('登录已过期，请重新登录');};window.addEventListener('luma:unauthorized',expired);api<User>('/auth/me').then(setUser).catch(()=>{}).finally(()=>setLoading(false));return()=>{window.removeEventListener('hashchange',change);window.removeEventListener('luma:unauthorized',expired);};},[]);
 async function login(e:React.FormEvent<HTMLFormElement>){e.preventDefault();setBusy(true);setError('');const f=new FormData(e.currentTarget);try{const u=await api<User>('/auth/login','POST',Object.fromEntries(f));setUser(u);go(u.role==='admin'?'/admin':'/');}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function logout(){await api('/auth/logout','POST');setUser(null);go('/');}
 if(loading)return <Loading/>;
 if(!user)return <main className="auth-layout"><section className="auth-art"><Brand/><img src="/sample-book.png" alt="小狗与红球"/><h1>把好故事准备好，<br/>让每一次开口都有收获。</h1></section><section className="auth-form"><Brand/><p className="eyebrow">A LITTLE READING, EVERY DAY</p><h1>{route.startsWith('/admin')?'管理员登录':'从一本好故事开始'}</h1><p className="muted">使用机构提供的账号，开始今天的阅读。</p><form onSubmit={login}><label>账号<input name="username" autoComplete="username" required maxLength={32} placeholder="请输入机构分配的账号"/></label><label>密码<input name="password" type="password" autoComplete="current-password" required maxLength={128} placeholder="请输入密码"/></label><Notice error>{error}</Notice><Button disabled={busy} type="submit">{busy?'正在登录…':'登录，开始阅读'}</Button></form><p className="small muted">忘记密码？请联系机构老师</p><button className="link" onClick={()=>go(route.startsWith('/admin')?'/':'/admin')}>{route.startsWith('/admin')?'学生登录':'管理入口'}</button><p className="small muted">机构账号仅用于学习。录音用于评分和必要复核，<br/>默认保存 30 天，不默认公开或用于模型训练。</p></section></main>;
 if(user.must_change_password)return <PasswordForm user={user} onDone={setUser} first onLogout={logout}/>;
 if(route==='/settings/password')return <PasswordForm user={user} onDone={u=>{setUser(u);go('/settings');}} onLogout={logout}/>;
 return user.role==='admin'&&route.startsWith('/admin')?<Admin user={user} route={route} logout={logout}/>:<Student user={user} route={route} logout={logout}/>;
}
function PasswordForm({user,onDone,first=false,onLogout}:{user:User;onDone:(u:User)=>void;first?:boolean;onLogout:()=>void}){
 const [error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function save(e:React.FormEvent<HTMLFormElement>){e.preventDefault();const f=new FormData(e.currentTarget);if(f.get('new_password')!==f.get('confirm')){setError('两次新密码不一致');return;}setBusy(true);try{onDone(await api('/auth/password','POST',{current_password:f.get('current_password'),new_password:f.get('new_password')}));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 return <div className="password-shell"><Brand/><h1>{first?'设置自己的密码':'修改密码'}</h1><p className="muted">{first?'首次登录，请更换机构提供的临时密码。':'修改后，其他设备会退出登录。'}</p><form onSubmit={save}><label>当前密码<input name="current_password" type="password" required autoComplete="current-password"/></label><label>新密码<input name="new_password" type="password" minLength={8} maxLength={64} pattern="(?=.*[A-Za-z])(?=.*[0-9]).{8,64}" title="8–64 位，至少包含字母和数字" required autoComplete="new-password"/></label><label>确认新密码<input name="confirm" type="password" required autoComplete="new-password"/></label><Notice error>{error}</Notice><Button disabled={busy}>{busy?'保存中…':'保存密码'}</Button><Button type="button" secondary onClick={first?onLogout:()=>go('/settings')}>{first?'退出登录':'返回设置'}</Button></form></div>;
}
