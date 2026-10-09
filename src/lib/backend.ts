export type BackendDecision = 'REFUND'|'FIX'|'EXPLAIN'|'GOODWILL'|'SPECIALIST'|'NOT_CONFIRMED'|'INFO'|'REFUSE'|'CLARIFY';
export interface BackendCase { case_id:string;session_id:string;msisdn:string;channel:'web'|'voice'|'api';intent?:string;root_cause:string|null;decision:BackendDecision;amount:number|null;team:string|null;priority:'P1'|'P2'|'P3'|null;sla:string|null;ticket_no:string|null;summary:string|null;rule_ids:string[];evidence?:string[];citations:string[];status:'RESOLVED'|'ESCALATED'|'OPEN';created_at:string;closed_at?:string|null;updated_at?:string;latency_ms?:{first_token:number;llm?:number;tools:number;total:number};transcript?:{role:'user'|'assistant';text:string;latency_ms?:BackendCase['latency_ms']}[] }
export interface SessionCreated {session_id:string;case_id?:string;language?:string;persona:{name:string};greeting:string}
export interface FinalEvent {message_id:string;text?:string;voice_text?:string;decision:BackendDecision;root_cause:string|null;amount:number|null;case_id:string;citations:string[];rule_ids:string[];latency_ms?:BackendCase['latency_ms']}
export interface StreamEvent {event:string;id?:string;data:Record<string,unknown>}

export interface DemoCustomer {id:string;msisdn:string;title:string;language:string;turns:string[]}
