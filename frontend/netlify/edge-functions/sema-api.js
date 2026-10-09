// Server-only gateway for the synthetic hackathon demo. Never expose SEMА_API_KEY in VITE_*.
const json=(message,status)=>new Response(JSON.stringify({message}),{status,headers:{'content-type':'application/json','cache-control':'no-store'}});
export default async function handler(request){
 const env=Netlify.env;const base=env.get('SEMA_BACKEND_URL'),key=env.get('SEMA_API_KEY'),access=env.get('SEMA_ACCESS_TOKEN');
 if(!base||!key)return json('Backend konfiqurasiyası tamamlanmayıb.',503);
 if(access){
 const supplied=request.headers.get('x-sema-access')||'';
 if(!supplied||supplied.length>1024)return json('Demo giriş kodunu daxil edin.',401);
 const digest=async s=>new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)));
 const [a,b]=await Promise.all([digest(supplied),digest(access)]);if(a.reduce((v,n,i)=>v|(n^b[i]),0)!==0)return json('Demo giriş kodu düzgün deyil.',401);
 }
 const url=new URL(request.url);const path=url.pathname.slice(4);
 const getAllowed=request.method==='GET'&&(/^\/v1\/cases(?:\/[A-Za-z0-9_-]+)?$/.test(path)||/^\/v1\/sessions\/[A-Za-z0-9_-]+(?:\/events)?$/.test(path)||path==='/health'||path==='/v1/demo/cases'||/^\/v1\/lines\/(?:%2B|\+)?99498\d{7}\/usage$/i.test(path)||path==='/v1/usage/summary');
 const usageLine=path.match(/^\/v1\/lines\/((?:%2B|\+)?99498\d{7})\/usage$/i);
 if(usageLine||path==='/v1/usage/summary'){const count=url.searchParams.get('months')||'6';if(!/^[1-6]$/.test(count)||[...url.searchParams.keys()].some(k=>k!=='months'))return json('Usage sorğusu düzgün deyil.',400);if(usageLine&&!['994981000137','994981000274','994981000411','994981000548','994981000685','994981000822','994981000959','994981001096','994981001233','994981001370'].includes(decodeURIComponent(usageLine[1]).replace('+','')))return json('Bu nömrə üçün məlumat tapılmadı.',404);}
 const postAllowed=request.method==='POST'&&(path==='/v1/sessions'||/^\/v1\/sessions\/[A-Za-z0-9_-]+\/(?:messages(?::stream)?|interrupt)$/.test(path));
 if(!getAllowed&&!postAllowed)return json('Bu əməliyyat web client üçün açıq deyil.',403);
 const origin=request.headers.get('origin');if(origin&&origin!==url.origin)return json('Sorğu mənbəyi qəbul edilmir.',403);
 let body;if(postAllowed){const text=await request.text();if(text.length>16384)return json('Sorğu çox böyükdür.',413);let parsed;try{parsed=JSON.parse(text)}catch{return json('JSON formatı yanlışdır.',400)}
 if(path==='/v1/sessions'){let msisdn=env.get('SEMA_DEMO_MSISDN')||'+994981000548';if(!access){const demos=await fetch(new URL('/v1/demo/cases',base),{headers:{'X-API-Key':key},signal:request.signal});if(!demos.ok)return json('Demo müştərilər yüklənmədi.',502);const data=await demos.json();const list=Array.isArray(data)?data:data.cases;if(!Array.isArray(list)||!list.some(c=>c.msisdn===parsed.msisdn))return json('Demo xətti düzgün konfiqurasiya edilməyib.',400);msisdn=parsed.msisdn;}if(!/^\+99498\d{7}$/.test(msisdn))return json('Demo xətti düzgün konfiqurasiya edilməyib.',503);body=JSON.stringify({channel:'web',msisdn,verified_level:1,language:['az','ru','en'].includes(parsed.language)?parsed.language:'az'})}
 else if(path.endsWith('/interrupt'))body=JSON.stringify({heard_text:String(parsed.heard_text||'').slice(0,8000)});
 else {if(typeof parsed.text!=='string'||!parsed.text.trim())return json('Mətn tələb olunur.',400);body=JSON.stringify({text:parsed.text,client_msg_id:parsed.client_msg_id})}}
 let upstream;try{upstream=new URL(base)}catch{return json('Backend URL yanlışdır.',503)}if(upstream.protocol!=='https:')return json('Backend HTTPS ilə işləməlidir.',503);
 upstream.pathname=upstream.pathname.replace(/\/$/,'')+path;upstream.search=url.search;
 const headers=new Headers({'X-API-Key':key,'Content-Type':'application/json','Accept':request.headers.get('accept')||'application/json','X-Request-Id':crypto.randomUUID()});const last=request.headers.get('last-event-id');if(last)headers.set('Last-Event-ID',last);
 try{const response=await fetch(upstream,{method:request.method,headers,body,redirect:'manual',signal:request.signal});if(response.status>=300&&response.status<400)return json('Backend yönləndirməsi qəbul edilmir.',502);return new Response(response.body,{status:response.status,headers:{'content-type':response.headers.get('content-type')||'application/json','cache-control':'no-store','x-content-type-options':'nosniff'}})}catch{return json('Backend-ə bağlantı alınmadı.',502)}
}
export const config={path:'/api/*'};
