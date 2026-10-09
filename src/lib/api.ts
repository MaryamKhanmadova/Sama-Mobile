import type { Conversation, DashboardData, SubmitResponse } from './types';
import type { BackendCase, SessionCreated, FinalEvent, StreamEvent, DemoCustomer } from './backend';
import { SessionSocket, websocketUrl } from './websocket';
import { mergeCaseDetails } from './turn';
import { readSse } from './sse';
import { demoConversations, demoDashboard, demoReply } from './demo';
const proxyAuth=import.meta.env.VITE_API_AUTH !== 'direct';
export const config = {
 mode: import.meta.env.VITE_DATA_MODE === 'demo' ? 'demo' : 'api',
 baseUrl: (import.meta.env.VITE_API_BASE_URL || (proxyAuth?'/api':'https://sema-care-production.up.railway.app')).replace(/\/$/, ''),
 transport: proxyAuth || import.meta.env.VITE_CHAT_TRANSPORT === 'sse' ? 'sse' : 'websocket',
 auth: proxyAuth ? 'proxy' : 'direct',
 wsBaseUrl: import.meta.env.VITE_WS_BASE_URL || 'https://sema-care-production.up.railway.app',
 voiceAgent: import.meta.env.VITE_ELEVENLABS_AGENT_ID || 'agent_6601m4g16s0afv8tk7c8x204x23b',
} as const;
const key='sema-conversations-v1';
let credential=sessionStorage.getItem('sema-access')||'';
const sockets=new Map<string,SessionSocket>();
const headers=()=>({'Content-Type':'application/json',[config.auth==='direct'?'X-API-Key':'X-Sema-Access']:credential,'X-Request-Id':crypto.randomUUID()});
export const hasAccess=()=>config.auth==='proxy'||!!credential;
export const setAccess=(value:string)=>{for(const socket of sockets.values())socket.close();sockets.clear();credential=value.trim();sessionStorage.setItem('sema-access',credential)};
const sessionIndex:Record<string,Conversation>={};
export class ApiError extends Error { constructor(message:string,public status=0){super(message)} }
export function readDemo():Conversation[]{try{const saved=localStorage.getItem(key);return saved?JSON.parse(saved):demoConversations}catch{return demoConversations}}
function writeDemo(data:Conversation[]){localStorage.setItem(key,JSON.stringify(data));window.dispatchEvent(new Event('sema:data'))}
async function request<T>(path:string,options:RequestInit={}):Promise<T>{
 if(!hasAccess())throw new ApiError(config.auth==='direct'?'Demo API açarını daxil edin.':'Demo giriş kodunu daxil edin.',401);
 if(!config.baseUrl)throw new ApiError('VITE_API_BASE_URL təyin edilməyib.');
 const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),20000);
 try{const response=await fetch(`${config.baseUrl}${path}`,{...options,signal:controller.signal,credentials:config.auth==='proxy'?'include':'omit',headers:{...headers(),...options.headers}});if(!response.ok){const error=await response.json().catch(()=>({}));throw new ApiError(error.message||`Sorğu uğursuz oldu (${response.status}).`,response.status);}return await response.json() as T}catch(e){if(e instanceof ApiError)throw e;throw new ApiError(e instanceof Error&&e.name==='AbortError'?'Sorğunun vaxtı bitdi. Yenidən cəhd edin.':'Serverə bağlantı alınmadı.')}finally{clearTimeout(timeout)}
}
function mapCase(c:BackendCase):Conversation {return {id:c.case_id,sessionId:c.session_id,title:c.summary||c.intent||c.root_cause||'Yeni müraciət',preview:c.root_cause||'Müraciət qeydə alındı',time:'',status:c.status==='RESOLVED'?'closed':'open',channel:c.channel==='voice'?'call':'text',queue:c.status==='ESCALATED'?'agent':c.status==='OPEN'?'unassigned':'ai',priority:c.priority==='P1'?'urgent':c.priority==='P2'?'high':'normal',customer:c.msisdn.replace(/(\+99498)\d+(\d{4})$/,'$1***$2'),assignee:c.team||undefined,createdAt:c.created_at,waitingMinutes:Math.max(0,Math.floor((Date.now()-Date.parse(c.created_at))/60000)),final:c.decision?{message_id:'',decision:c.decision,root_cause:c.root_cause,amount:c.amount,case_id:c.case_id,citations:c.citations||[],rule_ids:c.rule_ids||[],latency_ms:c.latency_ms||[...(c.transcript||[])].reverse().find(m=>m.role==='assistant')?.latency_ms}:undefined,messages:(c.transcript||[]).filter(m=>m.role==='user'||m.role==='assistant'),backendCase:c}}
async function cases():Promise<BackendCase[]>{const result=await request<BackendCase[]|{cases:BackendCase[]}>('/v1/cases?limit=250');const list=Array.isArray(result)?result:result.cases;if(!Array.isArray(list)||list.some(c=>!c.case_id||!c.status))throw new ApiError('Backend case formatı müqaviləyə uyğun deyil.');return list}
let demoMsisdn=import.meta.env.VITE_DEMO_MSISDN||'+994981000548';
async function openSession():Promise<Conversation>{
 const created=await request<SessionCreated>('/v1/sessions',{method:'POST',body:JSON.stringify({channel:'web',msisdn:demoMsisdn})});
 const c:Conversation={id:created.case_id||created.session_id,sessionId:created.session_id,title:'Yeni müraciət',preview:created.greeting,time:'İndi',status:'open',channel:'text',customer:demoMsisdn,messages:[{role:'assistant',text:created.greeting}]};sessionIndex[c.id]=c;return c;
}
async function submitStream(text:string,id?:string,onEvent?:(event:StreamEvent)=>void):Promise<SubmitResponse>{
 let c=id?sessionIndex[id]:undefined;
 if(!c&&id){c=mapCase(await request<BackendCase>(`/v1/cases/${encodeURIComponent(id)}`));sessionIndex[c.id]=c}
 if(!c)c=await openSession();
 const session=c.sessionId||c.id;let assembled='',lastId='',final:FinalEvent|undefined,done=false,interrupted=false;
 const events:StreamEvent[]=[];
 const consume=(event:StreamEvent)=>{
  if(event.id&&event.id===lastId)return;if(event.id)lastId=event.id;
  onEvent?.(event);
  if(event.event==='delta')assembled+=String(event.data.text||'');
  if(event.event==='final'){final=event.data as unknown as FinalEvent;if(final.text)assembled=final.text}
  if(event.event==='action'||event.event==='handoff')events.push(event);
  if(event.event==='error')throw new ApiError(String(event.data.message||'Emal xətası'));
  if(event.event==='done'){done=true;interrupted=!!event.data.interrupted}
 };
 if(config.transport==='websocket'){
  if(config.auth!=='direct')throw new ApiError('WebSocket üçün direct demo autentifikasiyası tələb olunur; server proxy rejimində SSE seçin.');
  let socket=sockets.get(session);
  if(!socket){socket=new SessionSocket(websocketUrl(config.wsBaseUrl,session,credential));sockets.set(session,socket)}
  await socket.send(text,consume);
 }else{
  for(let attempt=0;attempt<3&&!done;attempt++){
   const url=attempt===0?`/v1/sessions/${encodeURIComponent(session)}/messages:stream`:`/v1/sessions/${encodeURIComponent(session)}/events`;
   const response=await fetch(`${config.baseUrl}${url}`,{method:attempt===0?'POST':'GET',headers:{...headers(),Accept:'text/event-stream',...(lastId?{'Last-Event-ID':lastId}:{})},body:attempt===0?JSON.stringify({text,client_msg_id:crypto.randomUUID()}):undefined,signal:AbortSignal.timeout(90000)});
   if(!response.ok||!response.body)throw new ApiError(`Stream sorğusu uğursuz oldu (${response.status}).`,response.status);
   try{for await(const frame of readSse(response.body)){consume({event:frame.event,id:frame.id,data:JSON.parse(frame.data)});if(done)break}}catch(e){if(e instanceof ApiError||!lastId||attempt===2)throw e}
   if(!done&&!lastId)throw new ApiError('Stream tamamlanmadı. Sorğu avtomatik təkrarlanmadı.');
  }
 }
 if(!done)throw new ApiError('Cavab axını tamamlanmadı. Sessiyanı yoxlayın.');
 let result:Conversation={...c,title:c.title==='Yeni müraciət'?text.slice(0,50):c.title,messages:[...c.messages,{role:'user',text},...(assembled?[{role:'assistant' as const,text:assembled}]:[])],final,events,status:interrupted||!final||['SPECIALIST','CLARIFY'].includes(final.decision)?'open':'closed'};
 // The case response supplies the canonical status/transcript, including interrupted turns.
 try{const detail=mapCase(await request<BackendCase>(`/v1/cases/${encodeURIComponent(final?.case_id||c.id)}`));result=mergeCaseDetails(result,detail)}catch{/* Keep the received answer if the detail read is temporarily unavailable. */}
 sessionIndex[result.id]=result;return {conversation:result};
}

function realDashboard(raw:BackendCase[]):DashboardData {const closed=raw.filter(c=>c.status==='RESOLVED'),today=new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Baku'});const daily=new Map<string,{date:string;incoming:number;resolved:number}>();for(const c of raw){const d=c.created_at.slice(0,10);if(!daily.has(d))daily.set(d,{date:d,incoming:0,resolved:0});daily.get(d)!.incoming++;if(c.closed_at||(c.status==='RESOLVED'&&c.updated_at)){const r=(c.closed_at||c.updated_at)!.slice(0,10);if(!daily.has(r))daily.set(r,{date:r,incoming:0,resolved:0});daily.get(r)!.resolved++}}const times=raw.flatMap(c=>c.latency_ms?[c.latency_ms.first_token/1000]:[]).sort((a,b)=>a-b);return {conversations:raw.map(mapCase),volume:[...daily.values()].sort((a,b)=>a.date.localeCompare(b.date)),medianFirstResponseSeconds:times.length?Math.round(times[Math.floor(times.length/2)]):null,resolvedToday:closed.filter(c=>(c.closed_at||c.updated_at)?.startsWith(today)).length,resolution:{ai:closed.filter(c=>!c.team).length,agent:closed.filter(c=>c.team).length,handoff:raw.filter(c=>c.status==='ESCALATED').length}}}
export const supportApi={
 open:openSession,
 async demoCustomers():Promise<DemoCustomer[]>{const data=await request<DemoCustomer[]|{cases:DemoCustomer[]}>('/v1/demo/cases');const list=Array.isArray(data)?data:data.cases;return list},
 chooseCustomer(msisdn:string){demoMsisdn=msisdn},
 async interrupt(id:string){const c=sessionIndex[id];if(!c)return;const session=c.sessionId||c.id;if(config.transport==='websocket')sockets.get(session)?.interrupt();else await request(`/v1/sessions/${encodeURIComponent(session)}/interrupt`,{method:'POST',body:JSON.stringify({heard_text:''})})},
 disconnect(){for(const socket of sockets.values())socket.close();sockets.clear()},
 async detail(id:string):Promise<Conversation>{if(config.mode==='demo')return readDemo().find(c=>c.id===id)!;const c=mapCase(await request<BackendCase>(`/v1/cases/${encodeURIComponent(id)}`));const cached=sessionIndex[c.id];const latestUser=(v:Conversation)=>[...v.messages].reverse().find(m=>m.role==='user')?.text;const hydrated=cached&&latestUser(cached)===latestUser(c)?mergeCaseDetails(cached,c):c;sessionIndex[hydrated.id]=hydrated;return hydrated},
 async conversations():Promise<Conversation[]>{return config.mode==='demo'?readDemo():(await cases()).map(mapCase)},
 async dashboard():Promise<DashboardData>{return config.mode==='demo'?demoDashboard(readDemo()):realDashboard(await cases())},
 async submit(text:string,id?:string,onEvent?:(event:StreamEvent)=>void):Promise<SubmitResponse>{if(config.mode==='api')return submitStream(text,id,onEvent);await new Promise(r=>setTimeout(r,450));const data=readDemo();let c=data.find(c=>c.id===id);if(!c){c={id:crypto.randomUUID(),title:text.slice(0,37),preview:text,time:'İndi',status:'open',channel:'text',queue:'ai',priority:'normal',createdAt:new Date().toISOString(),customer:'Demo müştəri',messages:[]};data.unshift(c)}c={...c,preview:text,time:'İndi',messages:[...c.messages,{role:'user',text},{role:'assistant',text:demoReply(text)}]};writeDemo(data.map(item=>item.id===c.id?c:item));return {conversation:c}},
 async status(id:string,status:Conversation['status']):Promise<Conversation>{if(config.mode==='api')throw new ApiError('Müraciətin statusunu dəyişmək üçün endpoint müqavilədə göstərilməyib.');const data=readDemo();const found=data.find(c=>c.id===id);if(!found)throw new ApiError('Müraciət tapılmadı.');const updated={...found,status};writeDemo(data.map(c=>c.id===id?updated:c));return updated},
 async assign(id:string,assignee:string):Promise<Conversation>{if(config.mode==='api')throw new ApiError('Mütəxəssis təyinatı backend tərəfindən idarə olunur.');const data=readDemo();const found=data.find(c=>c.id===id);if(!found)throw new ApiError('Müraciət tapılmadı.');const updated:Conversation={...found,assignee,queue:'agent'};writeDemo(data.map(c=>c.id===id?updated:c));return updated},
 async saveDemoCall(seconds:number){if(config.mode!=='demo')throw new ApiError('Real zəng xidməti hələ inteqrasiya edilməyib.');const c:Conversation={id:crypto.randomUUID(),title:'Səsli müraciət',preview:`Demo zəng · ${seconds} saniyə`,time:'İndi',status:'closed',channel:'call',queue:'ai',priority:'normal',messages:[{role:'assistant',text:`Demo zəng ${seconds} saniyə davam etdi. Real səs ötürülməyib.`}]};writeDemo([c,...readDemo()]);return c}
};
