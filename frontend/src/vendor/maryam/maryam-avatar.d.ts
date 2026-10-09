import type {AvatarOptions,AvatarPort,AvatarState,AvatarEmotion,AvatarFraming} from '../../avatar/contracts';
export class MaryamAvatar implements AvatarPort{
 constructor(container:HTMLElement,options?:AvatarOptions);
 load():Promise<this>;mount(container:HTMLElement,options?:{framing?:AvatarFraming}):void;resize():void;dispose():void;
 setState(state:AvatarState):void;setEmotion(emotion:AvatarEmotion,options?:{intensity?:number;durationMs?:number}):void;
 reactToText(text:string):void;speakText(text:string,charsPerSec?:number):Promise<void>;
 useFrequencySource(source:()=>Uint8Array,range?:number|[number,number]):void;connectAudio(source:HTMLAudioElement|MediaStream):void;stopAudio():void;lookAt(x:number|null,y?:number):void;
}
export {MaryamAvatar as AylaAvatar};
