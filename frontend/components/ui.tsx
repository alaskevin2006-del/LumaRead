'use client';
import {BookOpen,ChevronLeft,Home,Library,UserRound,LogOut,X} from 'lucide-react';
import {go} from '../lib/api';
import {ReactNode} from 'react';
export function Brand(){return <div className="brand"><BookOpen size={29}/><div><strong>LumaRead</strong><small>英语绘本 · 每天读一点</small></div></div>;}
export function Button({children,secondary=false,danger=false,...props}:React.ButtonHTMLAttributes<HTMLButtonElement>&{secondary?:boolean;danger?:boolean}){return <button {...props} className={`button ${secondary?'secondary':''} ${danger?'danger':''} ${props.className||''}`}>{children}</button>;}
export function Notice({children,error=false}: {children:ReactNode;error?:boolean}){return children?<div role={error?'alert':'status'} className={`notice ${error?'error':''}`}>{children}</div>:null;}
export function Header({title,back='/',right}: {title:string;back?:string;right?:ReactNode}){return <header className="reader-header"><button className="icon-button" aria-label="返回" onClick={()=>go(back)}><ChevronLeft/></button><b>{title}</b><div>{right}</div></header>;}
export function Nav({active='home'}:{active?:string}){return <nav className="bottom-nav">{[[Home,'首页','/','home'],[Library,'绘本','/books','books'],[UserRound,'我的','/me','me']].map(([Icon,label,route,key])=>{const I=Icon as typeof Home;return <button key={key as string} onClick={()=>go(route as string)} className={active===key?'active':''}><I size={23}/><span>{label as string}</span></button>;})}</nav>;}
export function Modal({title,children,onClose,wide=false}: {title:string;children:ReactNode;onClose:()=>void;wide?:boolean}){return <div className="shade" onClick={e=>{if(e.target===e.currentTarget)onClose();}}><section className={"modal"+(wide?" modal-wide":"")} role="dialog" aria-modal="true" aria-label={title}><div className="row between"><h2>{title}</h2><button className="icon-button" aria-label="关闭" onClick={onClose}><X/></button></div>{children}</section></div>;}
export function Empty({title,children}:{title:string;children?:ReactNode}){return <div className="empty"><BookOpen size={48}/><h2>{title}</h2><div>{children}</div></div>;}
export function Loading(){return <div className="empty"><div className="spinner"/><p>正在加载…</p></div>;}
