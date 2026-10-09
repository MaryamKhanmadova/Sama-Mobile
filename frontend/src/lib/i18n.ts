import { useSyncExternalStore } from 'react';
import az from '../locales/az.json';
import en from '../locales/en.json';
import ru from '../locales/ru.json';
import { flattenMessages, interpolate, type TranslationValues } from './i18n-core';
export type Locale='az'|'en'|'ru';
export const locales:Locale[]=['az','en','ru'];
export const catalogs={az:flattenMessages(az.messages),en:flattenMessages(en.messages),ru:flattenMessages(ru.messages)};
const storageKey='sama-care-ui-locale';
let locale:Locale='az';
try{const saved=localStorage.getItem(storageKey);if(locales.includes(saved as Locale))locale=saved as Locale}catch{/* Private browsing may restrict storage. */}
const listeners=new Set<()=>void>();
export function getLocale(){return locale}
export function setLocale(next:Locale){if(!locales.includes(next)||next===locale)return;locale=next;try{localStorage.setItem(storageKey,next)}catch{}for(const listener of listeners)listener()}
export function useLocale(){return useSyncExternalStore(callback=>{listeners.add(callback);return()=>{listeners.delete(callback)}},getLocale,()=> 'az' as Locale)}
export function t(key:string,values:TranslationValues={}){return interpolate(catalogs[locale][key]??catalogs.az[key]??key,values)}
// Local UI errors/data may have been stored before the user changed language.
// Preserve arbitrary backend replies and user messages; call only for UI labels/errors.
export function localizeText(text:string,allowTemplates=false){
 for(const catalog of Object.values(catalogs))for(const [key,value] of Object.entries(catalog)){
  if(value===text)return t(key);
  if(!allowTemplates||!key.startsWith('errors.')||!value.includes('{'))continue;
  const names:string[]=[];const pattern=value.split(/(\{[A-Za-z][A-Za-z0-9]*\})/g).map(part=>{
   if(/^\{\w+\}$/.test(part)){names.push(part.slice(1,-1));return '(.+?)'}return part.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  }).join('');
  const match=text.match(new RegExp(`^${pattern}$`));if(match)return t(key,Object.fromEntries(names.map((name,i)=>[name,match[i+1]])));
 }
 return text;
}
if(typeof window!=='undefined')window.addEventListener('storage',event=>{if(event.key===storageKey&&locales.includes(event.newValue as Locale)){locale=event.newValue as Locale;for(const listener of listeners)listener()}});
