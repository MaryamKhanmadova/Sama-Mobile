export type AvatarState='idle'|'listening'|'thinking'|'speaking';
export type AvatarEmotion='happy'|'empathetic'|'serious'|'concerned'|'neutral';
export type AvatarFraming='face'|'bust';
export interface AvatarOptions{src?:string;framing?:AvatarFraming;transparent?:boolean;pixelRatioCap?:number;followPointer?:boolean;reducedMotion?:boolean}
export interface AvatarPort{
 load():Promise<AvatarPort>;mount(container:HTMLElement,options?:{framing?:AvatarFraming}):void;resize():void;dispose():void;
 setState(state:AvatarState):void;setEmotion(emotion:AvatarEmotion,options?:{intensity?:number;durationMs?:number}):void;
 reactToText(text:string):void;speakText(text:string,charsPerSec?:number):Promise<void>;
 useFrequencySource(source:()=>Uint8Array,range?:number|[number,number]):void;connectAudio(source:HTMLAudioElement|MediaStream):void;stopAudio():void;lookAt(x:number|null,y?:number):void;
}
