import type { Conversation } from './types.ts';
/** Case snapshots can omit the greeting or contain only a later assistant tool turn.
 * Keep the complete answer actually delivered to this client; take status/evidence from the case. */
export function mergeCaseDetails(current:Conversation,detail:Conversation):Conversation{
 const last=current.messages[current.messages.length-1];
 const delivered=last?.role==='assistant'&&!!last.text.trim();
 return {...current,...detail,messages:delivered?current.messages:detail.messages.length?detail.messages:current.messages,final:current.final??detail.final,events:current.events};
}
