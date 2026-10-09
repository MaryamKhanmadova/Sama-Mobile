export type TranslationValues = Record<string, string | number>;
export function flattenMessages(value:unknown,prefix=''):Record<string,string>{
 const result:Record<string,string>={};
 if(typeof value==='string'){result[prefix]=value;return result}
 if(value&&typeof value==='object')for(const [key,child] of Object.entries(value))Object.assign(result,flattenMessages(child,prefix?`${prefix}.${key}`:key));
 return result;
}
export function interpolate(text:string,values:TranslationValues={}){return text.replace(/\{([A-Za-z][A-Za-z0-9]*)\}/g,(match,key)=>values[key]===undefined?match:String(values[key]))}
export function placeholders(text:string){return [...new Set([...text.matchAll(/\{([A-Za-z][A-Za-z0-9]*)\}/g)].map(m=>m[1]))].sort()}
export function validateCatalog(base:Record<string,string>,other:Record<string,string>){
 const errors:string[]=[];
 for(const [key,value] of Object.entries(base)){
  if(typeof other[key]!=='string'||!other[key].trim()){errors.push(`${key}: missing translation`);continue}
  if(JSON.stringify(placeholders(value))!==JSON.stringify(placeholders(other[key])))errors.push(`${key}: placeholder mismatch`);
 }
 for(const key of Object.keys(other))if(!(key in base))errors.push(`${key}: unexpected key`);
 return errors;
}
