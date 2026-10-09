import test from 'node:test';import assert from 'node:assert/strict';
import {SessionSocket,websocketUrl} from '../src/lib/websocket.ts';
class Socket{
 readyState=0;sent=[];onopen;onclose;onerror;onmessage;
 open(){this.readyState=1;this.onopen?.()}
 send(text){this.sent.push(JSON.parse(text))}
 emit(event,data){this.onmessage?.({data:JSON.stringify({id:1,event,data})})}
 close(){this.readyState=3;this.onclose?.()}
}
const tick=()=>new Promise(r=>setImmediate(r));
test('URL uses WSS and encodes session/key without leaking extra parameters',()=>{const u=new URL(websocketUrl('https://backend.test?old=x','ss_demo','test+&key'));assert.equal(u.protocol,'wss:');assert.equal(u.pathname,'/v1/sessions/ss_demo/ws');assert.equal(u.searchParams.get('api_key'),'test+&key');assert.equal(u.searchParams.has('old'),false)});
test('streams events, waits for done and reuses connection for second turn',async()=>{
 const socket=new Socket();let count=0;const client=new SessionSocket('wss://test',()=>{count++;return socket});const events=[];
 const pending=client.send('Salam',e=>events.push(e));socket.open();await tick();
 assert.deepEqual(socket.sent,[{type:'message',text:'Salam'}]);socket.emit('delta',{text:'Salam'});socket.emit('final',{decision:'INFO'});socket.emit('done',{});await pending;
 assert.deepEqual(events.map(e=>e.event),['delta','final','done']);
 const second=client.send('Sualım var',()=>{});await tick();socket.emit('done',{});await second;assert.equal(count,1);client.close();
});
test('interrupt has exact backend payload and rejects concurrent submissions',async()=>{
 const socket=new Socket();const client=new SessionSocket('wss://test',()=>socket);const pending=client.send('Birinci',()=>{});socket.open();await tick();
 await assert.rejects(client.send('İkinci',()=>{}),/tamamlanmayıb/);client.interrupt('dayan');assert.deepEqual(socket.sent[1],{type:'interrupt',heard_text:'dayan'});socket.emit('done',{interrupted:true});await pending;client.close();
});
test('disconnect rejects without replay; server and malformed errors are visible',async()=>{
 for(const kind of ['close','error','malformed']){const socket=new Socket();const client=new SessionSocket('wss://test',()=>socket);const p=client.send('Salam',()=>{});socket.open();await tick();
 const rejected=assert.rejects(p);if(kind==='close')socket.close();else if(kind==='error')socket.emit('error',{message:'Agent xətası'});else socket.onmessage({data:'not-json'});await rejected;assert.equal(socket.sent.length,1);client.close()}
});
