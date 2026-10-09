import { t, localizeText } from '../lib/i18n';
import type { FinalEvent, StreamEvent } from '../lib/backend';
export function AgentEvents({events=[],final}:{events?:StreamEvent[];final?:FinalEvent}){
 return <div className="agent-events">{events.map((e,i)=>{
  if(e.event==='handoff')return <div className="handoff-result" key={i}>{t('events.handoff',{team:String(e.data.team_name||e.data.team||'')})}<br/>{String(e.data.ticket_no||'')} · {String(e.data.sla||'')}</div>;
  const result=e.data.result as Record<string,unknown>|undefined;
  return <div className={`action-result ${e.data.ok===false?'failed':''}`} key={i}>{e.data.ok===false?'✕':'✓'} {e.data.ok===false?t('events.actionFailed'):typeof result?.credited_azn==='number'?t('events.credited',{amount:result.credited_azn.toFixed(2)}):String(e.data.name||t('events.actionCompleted'))}{typeof result?.new_balance_azn==='number'&&<small>{t('events.newBalance',{amount:result.new_balance_azn.toFixed(2)})}</small>}</div>
 })}{final&&<details className="why-panel"><summary>{t('events.why')} · {final.decision}</summary><dl><dt>{t('events.ruleIds')}</dt><dd>{final.rule_ids?.join(', ')||t('common.notProvided')}</dd><dt>{t('events.citations')}</dt><dd>{final.citations?.map(c=>typeof c==='string'?c:JSON.stringify(c)).join('\n')||t('common.notProvided')}</dd><dt>{t('events.rootCause')}</dt><dd>{final.root_cause||'—'}</dd><dt>{t('events.amount')}</dt><dd>{final.amount==null?'—':t('common.amountAzn',{amount:final.amount.toFixed(2)})}</dd><dt>{t('events.latency')}</dt><dd>{final.latency_ms?.total==null?'—':t('common.latencyMs',{latency:final.latency_ms.total})}</dd></dl></details>}</div>
}
