export type CostKey='monthly_fee'|'packages'|'vas'|'roaming'|'out_of_bundle'|'intl_calls';
export type Category='video'|'social'|'browsing'|'music'|'messaging'|'games'|'maps';
export interface UsageMonth{
 msisdn:string;month:string;customer_id:string;full_name:string;tariff_id:'T_START'|'T_PLUS'|'T_MAX'|'T_GENC'|'T_PAYG'|'T_BIZNES';tariff_name:string;region:string;currency:'AZN';is_current:boolean;days_elapsed:number;days_in_month:number;
 costs:Record<CostKey,number>;total:number;credits:{reason:string;amount:number}[];credits_total:number;net_total:number;forecast_total:number;prev_month_total:number|null;change_pct:number|null;
 usage:{data_mb:number;data_limit_mb:number;data_pct:number|null;voice_min:number;voice_limit_min:number;voice_pct:number|null;sms:number;sms_limit:number};
 data_by_category:Partial<Record<Category,number>>;top_category:Category|null;daily_data_mb:number[];peak_day:number|null;packages:{package_id:string;name:string;price:number}[];vas:{vas_id:string;name:string;amount:number;period:string}[];
 roaming:{country:string;country_name:string;zone:string;days:number;package:string;package_price:number;extra_charges:number}|null;insights:string[];potential_savings:number;
}
export interface LineUsageResponse{msisdn:string;currency:'AZN';months:UsageMonth[]}
export interface SummaryMonth{msisdn:'#ALL';month:string;lines:number;currency:'AZN';is_current:boolean;avg_total:number;avg_data_mb:number;avg_voice_min:number;revenue_total:number;credits_total:number;credits_count:number;potential_savings_total:number;cost_breakdown:Record<CostKey,number>;data_by_category:Partial<Record<Category,number>>;tariff_mix:Record<string,number>;roaming_trips:number}
export interface SummaryResponse{currency:'AZN';months:SummaryMonth[]}
export const costKeys:CostKey[]=['monthly_fee','packages','vas','roaming','out_of_bundle','intl_calls'];
export const categoryIcons:Record<Category,string>={video:'🎬',social:'💬',browsing:'🌐',music:'🎵',messaging:'✉️',games:'🎮',maps:'🗺️'};
export const demoLines=[['+994981000137','Aysel Məmmədova'],['+994981000274','Tural Əliyev'],['+994981000411','Leyla Hüseynova'],['+994981000548','Orxan Quliyev'],['+994981000685','Nigar Rzayeva'],['+994981000822','Kamran Kərimov'],['+994981000959','Günay Abbasova'],['+994981001096','Elvin Nəbiyev'],['+994981001233','Ирина Петрова'],['+994981001370','Fidan Cəfərova']] as const;
export function maskLine(msisdn:string){const digits=msisdn.replace(/\D/g,'');return digits.length===12?`+${digits.slice(0,3)} ${digits.slice(3,5)} ${digits.slice(5,8)} •• ${digits.slice(-2)}`:'••••'}
export function chronological<T extends {month:string}>(months:T[]){return [...months].sort((a,b)=>a.month.localeCompare(b.month))}
export function limitPercent(used:number,limit:number){return limit>0?used/limit*100:null}
export function progressTone(pct:number|null){return pct==null?'none':pct>=100?'danger':pct>=90?'warning':'normal'}
export function nonZeroCosts(costs:Record<CostKey,number>){return costKeys.filter(key=>costs[key]>0).map(key=>({key,value:costs[key]}))}
export function validateUsage<T extends LineUsageResponse|SummaryResponse>(body:T):T{
 const validNumber=(n:unknown)=>typeof n==='number'&&Number.isFinite(n)&&n>=0;
 const validCosts=(costs:Record<CostKey,number>)=>costs&&costKeys.every(key=>validNumber(costs[key]));
 if(!body||body.currency!=='AZN'||!Array.isArray(body.months)||body.months.some(m=>{
  if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(m.month)||m.currency!=='AZN')return true;
  if('total'in m)return !validCosts(m.costs)||![m.total,m.credits_total,m.forecast_total,m.potential_savings,m.days_elapsed,m.days_in_month].every(validNumber)||typeof m.net_total!=='number'||!Number.isFinite(m.net_total)||!m.usage||![m.usage.data_mb,m.usage.data_limit_mb,m.usage.voice_min,m.usage.voice_limit_min,m.usage.sms,m.usage.sms_limit].every(validNumber)||![m.usage.data_pct,m.usage.voice_pct].every(n=>n==null||validNumber(n))||!m.data_by_category||!Array.isArray(m.credits)||!Array.isArray(m.insights)||!Array.isArray(m.packages)||!Array.isArray(m.vas)||!Array.isArray(m.daily_data_mb)||!m.daily_data_mb.every(validNumber);
  return !validCosts(m.cost_breakdown)||![m.lines,m.avg_total,m.avg_data_mb,m.avg_voice_min,m.revenue_total,m.credits_total,m.credits_count,m.potential_savings_total,m.roaming_trips].every(validNumber)||!m.data_by_category||!m.tariff_mix;
 }))throw new Error('usage.invalidResponse');return body;
}
