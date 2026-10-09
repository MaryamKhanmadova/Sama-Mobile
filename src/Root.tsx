import { useEffect, useState } from 'react';
import SupportPage from './App';
import Dashboard from './pages/Dashboard';
export default function Root(){const route=()=>location.hash==='#/dashboard'||location.pathname==='/dashboard'?'dashboard':'support';const [page,setPage]=useState(route);useEffect(()=>{const update=()=>setPage(route());window.addEventListener('hashchange',update);return()=>window.removeEventListener('hashchange',update)},[]);const navigate=(target:string)=>{history.replaceState(null,'','/');location.hash=`/${target}`;setPage(target);window.scrollTo(0,0)};return page==='dashboard'?<Dashboard onSupport={()=>navigate('support')}/>:<SupportPage onDashboard={()=>navigate('dashboard')}/>}
