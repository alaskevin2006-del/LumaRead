import type { NextConfig } from 'next';
const config:NextConfig={output:'standalone',turbopack:{root:process.cwd()},outputFileTracingRoot:process.cwd(),poweredByHeader:false,async rewrites(){return [{source:'/api/:path*',destination:`${process.env.API_URL||'http://127.0.0.1:8000'}/api/:path*`}];},async headers(){return [{source:'/:path*',headers:[{key:'X-Frame-Options',value:'DENY'},{key:'Referrer-Policy',value:'same-origin'},{key:'Permissions-Policy',value:'microphone=(self), camera=()'}]}];}};
export default config;
