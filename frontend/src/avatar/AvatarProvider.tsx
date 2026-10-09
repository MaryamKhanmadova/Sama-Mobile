import {createContext,useContext,useEffect,useRef,useSyncExternalStore,type ReactNode} from 'react';
import {AvatarController} from './controller';
import {avatarModel,avatarPortrait} from './assets';
import type {AvatarFraming} from './contracts';
import {t} from '../lib/i18n';
const Context=createContext<AvatarController|null>(null);
export function AvatarProvider({children}:{children:ReactNode}){
 const controller=useRef<AvatarController|null>(null);const parkingNode=useRef<HTMLDivElement|null>(null);const parking=useRef<HTMLDivElement>(null);const active=useRef(false);
 if(!controller.current){const store=document.createElement('div');store.className='avatar-parking';parkingNode.current=store;controller.current=new AvatarController(async host=>{const {MaryamAvatar}=await import('../vendor/maryam/maryam-avatar.js');const device=navigator as Navigator&{deviceMemory?:number};return new MaryamAvatar(host,{src:avatarModel,transparent:true,pixelRatioCap:device.hardwareConcurrency<=4||(device.deviceMemory??8)<=4||matchMedia('(max-width:800px)').matches?1:2})},store);}
 useEffect(()=>{active.current=true;const root=parking.current;const store=parkingNode.current;if(store&&root)root.appendChild(store);return()=>{active.current=false;queueMicrotask(()=>{if(!active.current)controller.current?.dispose()})}},[]);
 return <Context.Provider value={controller.current}>{children}<div ref={parking} hidden aria-hidden="true"/></Context.Provider>
}
export function useAvatar(){const avatar=useContext(Context);if(!avatar)throw new Error('AvatarProvider is required');return avatar}
export function AvatarView({framing='bust',className=''}:{framing?:AvatarFraming;className?:string}){
 const host=useRef<HTMLDivElement>(null);const avatar=useAvatar();const status=useSyncExternalStore(avatar.subscribe,avatar.snapshot,avatar.snapshot);
 useEffect(()=>host.current?avatar.attach(host.current,framing):undefined,[avatar,framing]);
 return <div className={`maryam-view ${className}`} data-avatar-status={status} role="img" aria-label={t('avatar.label')}><div className="maryam-canvas" ref={host}/>{status==='loading'&&<div className="avatar-shimmer" aria-label={t('avatar.loading')}/>} {status==='fallback'&&<img className="avatar-portrait" src={avatarPortrait} alt=""/>}</div>
}
