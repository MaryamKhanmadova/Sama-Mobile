import test from 'node:test';import assert from 'node:assert/strict';import {mergeCaseDetails} from '../src/lib/turn.ts';
const base={id:'CS-demo',title:'Request',preview:'',time:'',status:'open',channel:'text'};
test('canonical case metadata does not replace a complete streamed answer with a shorter transcript',()=>{
 const final={decision:'INFO',case_id:base.id};
 const current={...base,final,events:[{event:'action',data:{ok:true}}],messages:[{role:'assistant',text:'Hello'},{role:'user',text:'Explain'},{role:'assistant',text:'Full answer with all steps.'}]};
 const detail={...base,status:'closed',title:'Server summary',messages:[{role:'user',text:'Explain'},{role:'assistant',text:'Any other questions?'}]};
 const merged=mergeCaseDetails(current,detail);assert.equal(merged.status,'closed');assert.equal(merged.title,'Server summary');assert.equal(merged.messages.at(-1).text,'Full answer with all steps.');assert.equal(merged.messages.length,3);assert.deepEqual(merged.final,final);assert.deepEqual(merged.events,current.events);
});
test('without a delivered answer the canonical transcript can restore the result',()=>{const current={...base,messages:[{role:'user',text:'Explain'}]};const detail={...base,messages:[{role:'user',text:'Explain'},{role:'assistant',text:'Stored answer'}]};assert.equal(mergeCaseDetails(current,detail).messages.at(-1).text,'Stored answer')});
