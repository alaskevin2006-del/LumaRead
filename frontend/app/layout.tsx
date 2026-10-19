import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'LumaRead · 英语绘本',description:'机构英语绘本听读、跟读与学习记录'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="zh-CN"><body>{children}</body></html>;}
