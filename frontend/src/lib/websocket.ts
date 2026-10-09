import type { StreamEvent } from './backend.ts';
/** One outstanding turn per socket. Never replay a message after a disconnect. */
export class SessionSocket {
 private socket?: WebSocket;
 private connecting?: Promise<void>;
 private pending?: {on:(event:StreamEvent)=>void;resolve:()=>void;reject:(error:Error)=>void;timer:ReturnType<typeof setTimeout>};
 private url:string;private factory:(url:string)=>WebSocket;private timeoutMs:number;
 constructor(url:string,factory:(url:string)=>WebSocket=url=>new WebSocket(url),timeoutMs=90000){this.url=url;this.factory=factory;this.timeoutMs=timeoutMs}
 private async connect(){
  if(this.socket?.readyState===1)return;
  if(this.connecting)return this.connecting;
  this.connecting=new Promise<void>((resolve,reject)=>{
   const socket=this.factory(this.url);this.socket=socket;
   const timeout=setTimeout(()=>{reject(new Error('WebSocket bağlantısının vaxtı bitdi.'));socket.close()},15000);
   socket.onopen=()=>{clearTimeout(timeout);resolve()};
   socket.onmessage=event=>{
    if(!this.pending)return;
    try{const frame=JSON.parse(String(event.data));if(typeof frame.event!=='string'||!frame.data||typeof frame.data!=='object')throw new Error('WebSocket event formatı yanlışdır.');
     this.pending.on({id:frame.id===undefined?undefined:String(frame.id),event:frame.event,data:frame.data});
     if(frame.event==='error')this.fail(new Error(String(frame.data.message||'Agent xətası.')));
     else if(frame.event==='done'){const p=this.pending;this.pending=undefined;clearTimeout(p.timer);p.resolve()}
    }catch(error){this.fail(error instanceof Error?error:new Error('WebSocket cavabı oxunmadı.'))}
   };
   socket.onerror=()=>{clearTimeout(timeout);reject(new Error('WebSocket bağlantısı alınmadı.'));this.fail(new Error('WebSocket bağlantısı kəsildi. Cavabın nəticəsini sessiyadan yoxlayın.'))};
   socket.onclose=()=>{clearTimeout(timeout);if(this.socket===socket)this.socket=undefined;reject(new Error('WebSocket bağlantısı bağlandı.'));this.fail(new Error('Cavab axını yarımçıq qaldı. Sorğu avtomatik təkrarlanmadı; sessiyanı yoxlayın.'))};
  }).finally(()=>{this.connecting=undefined});
  return this.connecting;
 }
 async send(text:string,on:(event:StreamEvent)=>void){
  if(this.pending)throw new Error('Əvvəlki cavab hələ tamamlanmayıb.');
  await this.connect();
  if(this.pending)throw new Error('Əvvəlki cavab hələ tamamlanmayıb.');
  return new Promise<void>((resolve,reject)=>{
   this.pending={on,resolve,reject,timer:setTimeout(()=>{this.fail(new Error('Cavabın vaxtı bitdi. Nəticəni sessiyadan yoxlayın.'));this.socket?.close()},this.timeoutMs)};
   try{this.socket!.send(JSON.stringify({type:'message',text}))}catch{this.fail(new Error('Mesaj göndərilmədi.'))}
  });
 }
 interrupt(heardText=''){if(this.pending&&this.socket?.readyState===1)this.socket.send(JSON.stringify({type:'interrupt',heard_text:heardText}))}
 private fail(error:Error){if(!this.pending)return;const p=this.pending;this.pending=undefined;clearTimeout(p.timer);p.reject(error)}
 close(){this.fail(new Error('Sessiya bağlandı.'));this.socket?.close();this.socket=undefined}
}
export function websocketUrl(base:string,sessionId:string,key:string){
 const url=new URL(base);if(!['https:','http:','wss:','ws:'].includes(url.protocol))throw new Error('WebSocket URL yanlışdır.');
 url.protocol=url.protocol==='http:'||url.protocol==='ws:'?'ws:':'wss:';url.pathname=url.pathname.replace(/\/$/,'')+`/v1/sessions/${encodeURIComponent(sessionId)}/ws`;url.search='';url.searchParams.set('api_key',key);url.hash='';return url.toString();
}
