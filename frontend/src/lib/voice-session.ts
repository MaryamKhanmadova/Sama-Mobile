export interface VoiceSession {setMicMuted(muted:boolean):void|Promise<void>;endSession():Promise<void>}
// Own the microphone session, including a connection that resolves after cancellation.
export class VoiceSessionOwner<T extends VoiceSession>{
 session:T|null=null;private generation=0;
 async start(factory:()=>Promise<T>){const generation=++this.generation;const session=await factory();if(generation!==this.generation){try{await session.setMicMuted(true)}finally{await session.endSession()}return null}this.session=session;return session}
 async mute(value:boolean){if(!this.session)return false;await this.session.setMicMuted(value);return true}
 async stop(){++this.generation;const session=this.session;this.session=null;if(session){try{await session.setMicMuted(true)}finally{await session.endSession()}}}
}
