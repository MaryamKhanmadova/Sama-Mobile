import type {AvatarPort,AvatarState,AvatarEmotion,AvatarFraming} from './contracts';
export type AvatarStatus='loading'|'ready'|'fallback';
export class AvatarController{
 private instance:AvatarPort|null=null;private loading:Promise<void>|null=null;private disposed=false;
 private host:HTMLElement|null=null;private framing:AvatarFraming='bust';private state:AvatarState='idle';
 private frequency:(()=>Uint8Array)|null=null;private voiceActive=false;private speech:Promise<void>|null=null;private queuedSpeech:string|null=null;
 private status:AvatarStatus='loading';private listeners=new Set<()=>void>();
 constructor(privateFactory:(host:HTMLElement)=>Promise<AvatarPort>,parking:HTMLElement){this.factory=privateFactory;this.parking=parking}
 private factory:(host:HTMLElement)=>Promise<AvatarPort>;private parking:HTMLElement;
 subscribe=(listener:()=>void)=>{this.listeners.add(listener);return()=>{this.listeners.delete(listener)}};
 snapshot=()=>this.status;
 private notify(status:AvatarStatus){this.status=status;for(const l of this.listeners)l()}
 private sync(){this.instance?.setState(this.state);if(this.frequency)this.instance?.useFrequencySource(this.frequency)}
 async ensure(){if(this.loading)return this.loading;this.loading=(async()=>{try{const avatar=await this.factory(this.parking);this.instance=avatar;if(this.disposed){avatar.dispose();this.instance=null;return}await avatar.load();if(this.disposed){avatar.dispose();this.instance=null;return}if(this.host)avatar.mount(this.host,{framing:this.framing});this.sync();this.notify('ready');if(this.queuedSpeech&&!this.voiceActive){const text=this.queuedSpeech;this.queuedSpeech=null;this.speak(text)}}catch{this.instance?.dispose();this.instance=null;this.notify('fallback')}})();return this.loading}
 attach(host:HTMLElement,framing:AvatarFraming){this.host=host;this.framing=framing;if(this.instance&&this.status==='ready')this.instance.mount(host,{framing});void this.ensure();return()=>{if(this.host===host){this.host=null;if(this.instance&&this.status==='ready')this.instance.mount(this.parking)}}}
 setState(state:AvatarState){if(this.state!==state&&this.speech&&!this.voiceActive&&state!=='speaking'){this.queuedSpeech=null;void this.instance?.speakText('').then(()=>{if(!this.disposed)this.sync()})}this.state=state;this.instance?.setState(state)}
 emotion(name:AvatarEmotion,options?:{intensity?:number;durationMs?:number}){this.instance?.setEmotion(name,options)}
 react(text:string){this.instance?.reactToText(text)}
 speak(text:string){if(this.voiceActive||!text.trim())return;if(!this.instance||this.status!=='ready'){this.queuedSpeech=text;return}if(this.speech){this.queuedSpeech=text;return}this.state='speaking';this.speech=this.instance.speakText(text).catch(()=>{}).finally(()=>{this.speech=null;if(this.disposed)return;if(this.voiceActive){this.sync();return}const next=this.queuedSpeech;this.queuedSpeech=null;if(next)this.speak(next);else{if(this.state==='speaking')this.state='idle';this.sync()}})}
 beginVoice(){this.voiceActive=true;this.queuedSpeech=null;this.instance?.stopAudio();this.state='thinking';this.sync();if(this.speech){void this.instance?.speakText('').then(()=>{if(!this.disposed)this.sync()})}}
 connectVoice(source:()=>Uint8Array){this.frequency=source;this.voiceActive=true;this.sync()}
 endVoice(){this.frequency=null;this.voiceActive=false;this.instance?.stopAudio();this.state='idle';this.sync()}
 dispose(){this.disposed=true;this.queuedSpeech=null;this.instance?.stopAudio();this.instance?.dispose();this.instance=null;this.listeners.clear()}
}
