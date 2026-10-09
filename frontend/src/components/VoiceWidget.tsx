import { t, localizeText } from '../lib/i18n';
import { useEffect, useRef, useState } from 'react';
import { config } from '../lib/api';
export function VoiceWidget(){
 const host=useRef<HTMLDivElement>(null);const [enabled,setEnabled]=useState(false);const [error,setError]=useState('');
 useEffect(()=>{if(!enabled||!host.current)return;let widget:HTMLElement|undefined;let live=true;
 let script=document.querySelector<HTMLScriptElement>('script[data-sema-voice]');
 const mount=()=>{if(!live||!host.current)return;widget=document.createElement('elevenlabs-convai');widget.setAttribute('agent-id',config.voiceAgent);host.current.appendChild(widget)};
 if(customElements.get('elevenlabs-convai'))mount();else{
  if(!script){script=document.createElement('script');script.dataset.semaVoice='true';script.src='https://unpkg.com/@elevenlabs/convai-widget-embed';script.async=true;document.body.appendChild(script)}
  script.addEventListener('error',()=>{if(live)setError(t('voice.loadError'))},{once:true});
  customElements.whenDefined('elevenlabs-convai').then(mount);
 }
 return()=>{live=false;widget?.remove()};
 },[enabled]);
 return <div className="live-voice"><button className="voice-connect" onClick={()=>setEnabled(s=>!s)}>{enabled?t('voice.closePanel'):t('voice.startLiveCall')}</button><p>{enabled?t('voice.startInstructions'):t('voice.providerDescription')}</p>{error&&<p role="alert">{localizeText(error,true)}</p>}<div ref={host}/></div>
}
