import {t,useLocale} from './lib/i18n';
import {lazy,Suspense,useEffect,useRef,useState} from 'react';
import {flushSync} from 'react-dom';
import type {SupportRequest} from './pages/Dashboard';
import {AvatarProvider} from './avatar/AvatarProvider';
import {AppShell} from './components/AppShell';
const loadSupport=()=>import('./App');const loadDashboard=()=>import('./pages/Dashboard');
const SupportPage=lazy(loadSupport);const Dashboard=lazy(loadDashboard);
type Page='support'|'dashboard';
type TransitionDocument=Document&{startViewTransition?:(update:()=>void)=>{finished:Promise<void>}};
const route=():Page=>location.hash==='#/dashboard'||location.pathname==='/dashboard'?'dashboard':'support';
export default function Root(){
 const locale=useLocale();const [page,setPage]=useState<Page>(route);const [request,setRequest]=useState<SupportRequest>();const positions=useRef(new Map<string,number>());const address=useRef(location.href);const restore=useRef<number|null>(null);const content=useRef<HTMLElement>(null);
 useEffect(()=>{document.documentElement.lang=locale;document.title=t('brand.pageTitle')},[locale]);
 function change(next:Page,scroll:number){restore.current=scroll;const commit=()=>flushSync(()=>setPage(next));const documentWithTransition=document as TransitionDocument;if(!matchMedia('(prefers-reduced-motion: reduce)').matches&&documentWithTransition.startViewTransition)void documentWithTransition.startViewTransition(commit).finished.catch(()=>{});else commit()}
 useEffect(()=>{const back=()=>{positions.current.set(address.current,scrollY);address.current=location.href;change(route(),positions.current.get(location.href)||0)};window.addEventListener('popstate',back);return()=>window.removeEventListener('popstate',back)},[]);
 useEffect(()=>{const root=content.current;if(!root||restore.current===null)return;const focus=()=>{const heading=root.querySelector<HTMLElement>('h1');if(!heading||heading.closest('.page-skeleton'))return;heading.tabIndex=-1;heading.focus({preventScroll:true});window.scrollTo(0,restore.current||0);restore.current=null;observer.disconnect()};const observer=new MutationObserver(focus);observer.observe(root,{childList:true,subtree:true});focus();return()=>observer.disconnect()},[page]);
 const navigate=(next:Page)=>{if(page===next)return;positions.current.set(location.href,scrollY);history.pushState(null,'',`/#/${next}`);address.current=location.href;change(next,0)};
 return <AvatarProvider><AppShell page={page} navigate={navigate} prefetch={target=>{void (target==='support'?loadSupport():loadDashboard())}}><main id="main-content" ref={content} tabIndex={-1} className="page-content"><Suspense fallback={<div className="page-skeleton" aria-busy="true"><h1>{t('common.loading')}</h1><div/><div/></div>}>{page==='dashboard'?<Dashboard onSupport={message=>{setRequest(message);navigate('support')}}/>:<SupportPage initialRequest={request} onDashboard={()=>{setRequest(undefined);navigate('dashboard')}}/>}</Suspense></main><div className="sr-only" aria-live="polite">{t(page==='dashboard'?'navigation.dashboard':'navigation.support')}</div></AppShell></AvatarProvider>
}
