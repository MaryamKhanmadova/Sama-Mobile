import {startManagedVoice,type ManagedVoiceSession} from '../lib/managed-voice';
import {captionText,callContext} from '../lib/voice-copy';
import type {Message} from '../lib/types';
import {Mic,MicOff,Phone,PhoneOff,Volume2,MessageSquare} from 'lucide-react';
import {useCallback,useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {t} from '../lib/i18n';
import {config} from '../lib/api';
import {brandText} from '../lib/ui-branding';
import {VoiceSessionOwner} from '../lib/voice-session';
import {useAvatar} from '../avatar/AvatarProvider';
import {VoiceRing} from './VoiceRing';
import {Button} from './ui/button';
interface Props{msisdn:string;onActiveChange:(active:boolean)=>void;onMessagesChange:(messages:Message[])=>void;onCaptionsChange:(show:boolean)=>void}
export function VoiceWidget({msisdn,onActiveChange,onMessagesChange,onCaptionsChange}:Props){
 const avatar=useAvatar();const owner=useRef(new VoiceSessionOwner<ManagedVoiceSession>());const mounted=useRef(true);const epoch=useRef(0);const starting=useRef(false);const onActive=useRef(onActiveChange);onActive.current=onActiveChange;
 const [status,setStatus]=useState<'idle'|'connecting'|'connected'>('idle');const [phase,setPhase]=useState('idle');const [muted,setMuted]=useState(false);const [muting,setMuting]=useState(false);const [seconds,setSeconds]=useState(0);const [error,setError]=useState('');const [messages,setMessages]=useState<Message[]>([]);const [volume,setVolume]=useState(1);const [captions,setCaptions]=useState(true);const [ringHost,setRingHost]=useState<HTMLElement|null>(null);
 const startedAt=useRef(0);const onMessages=useRef(onMessagesChange);onMessages.current=onMessagesChange;const captionsCallback=useRef(onCaptionsChange);captionsCallback.current=onCaptionsChange;const callbacks=useRef({stop:()=>{},mute:()=>{}});
 const getSession=useCallback(()=>owner.current.session,[]);
 useEffect(()=>{onMessages.current(messages)},[messages]);
 useEffect(()=>{mounted.current=true;captionsCallback.current(true);setRingHost(document.getElementById('voice-avatar-ring'));const unload=()=>{void owner.current.stop().catch(()=>{});avatar.endVoice()};window.addEventListener('pagehide',unload);return()=>{mounted.current=false;++epoch.current;unload();onActive.current(false);window.removeEventListener('pagehide',unload)}},[avatar]);
 useEffect(()=>{if(status!=='connected')return;const timer=setInterval(()=>setSeconds(Math.floor((Date.now()-startedAt.current)/1000)),1000);return()=>clearInterval(timer)},[status]);
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if(status!=='connected'||e.target instanceof HTMLInputElement||e.target instanceof HTMLTextAreaElement)return;if(e.key.toLowerCase()==='m'){e.preventDefault();callbacks.current.mute()}if(e.key==='Escape'&&confirm(t('voice.endConfirm'))){callbacks.current.stop()}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)},[status]);
 function reset(){starting.current=false;setStatus('idle');setPhase('idle');setMuted(false);avatar.endVoice();onActive.current(false)}
 async function start(){if(starting.current||status!=='idle')return;starting.current=true;const token=++epoch.current;setStatus('connecting');setPhase('connecting');setError('');setMessages([]);setMuted(false);setMuting(false);setSeconds(0);onActive.current(true);avatar.beginVoice();
  try{
   if(!window.isSecureContext)throw new Error('insecure');if(!navigator.mediaDevices?.getUserMedia||!window.RTCPeerConnection)throw new Error('unsupported');
   const session=await owner.current.start(()=>startManagedVoice({agentId:config.voiceAgent,textOnly:false,connectionType:'webrtc',customLlmExtraBody:callContext(msisdn,crypto.randomUUID()),
    onModeChange:({mode})=>{if(mounted.current&&token===epoch.current){setPhase(mode);avatar.setState(mode==='speaking'?'speaking':'listening')}},
    onMessage:({role,message})=>{if(!mounted.current||token!==epoch.current)return;if(role==='agent')avatar.react(message);else{setPhase('thinking');avatar.setState('thinking')}setMessages(ms=>[...ms,{role:role==='agent'?'assistant':'user',text:captionText(role==='agent'?brandText(message):message)}])},
    onDisconnect:details=>{if(mounted.current&&token===epoch.current){++epoch.current;void owner.current.stop().catch(()=>{});reset();if(details.reason==='error')setError(t('voice.networkError'))}},
    onError:()=>{if(mounted.current&&token===epoch.current){++epoch.current;void owner.current.stop().catch(()=>{});reset();setError(t('voice.connectionError'))}}
   }));
   if(session&&mounted.current&&token===epoch.current){starting.current=false;startedAt.current=Date.now();session.setVolume({volume});avatar.connectVoice(()=>session.getOutputByteFrequencyData());avatar.setState('listening');setPhase('listening');setStatus('connected')}
  }catch(e){if(mounted.current&&token===epoch.current){reset();setError(e instanceof DOMException&&e.name==='NotAllowedError'?t('voice.permissionError'):e instanceof DOMException&&e.name==='NotFoundError'?t('voice.noMicrophone'):e instanceof Error&&e.message==='insecure'?t('voice.insecure'):e instanceof Error&&e.message==='unsupported'?t('voice.unsupported'):t('voice.connectionError'))}}
 }
 async function stop(){++epoch.current;reset();try{await owner.current.stop()}catch{if(mounted.current)setError(t('voice.connectionError'))}}
 async function toggleMute(){if(muting)return;const token=epoch.current;const next=!muted;setMuting(true);if(next)setMuted(true);try{if(await owner.current.mute(next)&&mounted.current&&token===epoch.current)setMuted(next)}catch{if(mounted.current&&token===epoch.current){await stop();setError(t('voice.connectionError'))}}finally{if(mounted.current&&token===epoch.current)setMuting(false)}}
 callbacks.current={stop:()=>void stop(),mute:()=>void toggleMute()};
 const label=status==='connecting'?t('voice.connecting'):status==='idle'?t('voice.ready'):phase==='speaking'?t('voice.speaking'):muted?t('voice.micOff'):phase==='thinking'?t('voice.thinking'):t('voice.listening');
 return <div className={`inline-voice ${status==='connected'?'voice-connected':''}`}>
  {ringHost&&createPortal(<VoiceRing getSession={getSession} phase={phase} muted={muted}/>,ringHost)}
  <p className="voice-status" aria-live="polite"><i className={status==='connected'?'connected':''}/>{label}</p>
  {status==='connected'&&<p className="call-time">{String(Math.floor(seconds/60)).padStart(2,'0')}:{String(seconds%60).padStart(2,'0')}</p>}
  <div className="call-buttons">{status==='idle'?<Button className="start-call" onClick={()=>void start()}><Phone size={17}/>{error?t('voice.retry'):t('voice.startLiveCall')}</Button>:<>{status==='connected'&&<Button variant="outline" size="icon" aria-label={muted?t('voice.unmute'):t('voice.mute')} aria-pressed={muted} disabled={muting} onClick={()=>void toggleMute()}>{muted?<MicOff size={21}/>:<Mic size={21}/>}</Button>}<Button className="end-call" onClick={()=>void stop()}><PhoneOff size={20}/>{status==='connecting'?t('common.cancel'):t('voice.endCall')}</Button></>}</div>
  {status==='connected'&&<div className="voice-options">{muted&&<span className="muted-indicator" role="status"><MicOff size={14}/>{t('voice.micOff')}</span>}<label><Volume2 size={16}/><span className="sr-only">{t('voice.volume')}</span><input type="range" min="0" max="1" step="0.05" value={volume} onChange={e=>{const value=Number(e.target.value);setVolume(value);owner.current.session?.setVolume({volume:value})}}/></label><Button variant="ghost" aria-pressed={captions} onClick={()=>{setCaptions(v=>!v);onCaptionsChange(!captions)}}><MessageSquare size={16}/>{t('voice.captions')}</Button></div>}
  {error&&<p role="alert" className="voice-error">{error}</p>}
 </div>
}
