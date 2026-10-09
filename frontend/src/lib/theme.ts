import {useSyncExternalStore} from 'react';
export type ThemeChoice='system'|'light'|'dark';
const key='sama-mobile-theme';let choice:ThemeChoice='system';try{const saved=localStorage.getItem(key);if(saved==='light'||saved==='dark')choice=saved}catch{}
const media=matchMedia('(prefers-color-scheme: dark)');const listeners=new Set<()=>void>();
function apply(){const dark=choice==='dark'||choice==='system'&&media.matches;document.documentElement.dataset.theme=dark?'dark':'light';document.documentElement.style.colorScheme=dark?'dark':'light';document.querySelector('meta[name="theme-color"]')?.setAttribute('content',getComputedStyle(document.documentElement).getPropertyValue('--browser-bar').trim());for(const listener of listeners)listener()}
export function setTheme(next:ThemeChoice){choice=next;try{localStorage.setItem(key,next)}catch{}apply()}
export function useTheme(){return useSyncExternalStore(listener=>{listeners.add(listener);return()=>{listeners.delete(listener)}},()=>choice,()=> 'system' as ThemeChoice)}
media.addEventListener('change',()=>{if(choice==='system')apply()});apply();
