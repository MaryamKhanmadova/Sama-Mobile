export interface MicrophoneTrack {
 mediaStreamTrack: { enabled: boolean; stop(): void };
 stopOnMute: boolean;
}
// Stop capture synchronously. The transport then mutes its publication; unmute
// reacquires a microphone through the SDK and reconnects its input analyser.
export class MicrophoneGate {
 private pending:Promise<void>=Promise.resolve();private closed=false;
 private track:()=>MicrophoneTrack|undefined;private setMuted:(value:boolean)=>Promise<void>;
 constructor(track:()=>MicrophoneTrack|undefined,setMuted:(value:boolean)=>Promise<void>){this.track=track;this.setMuted=setMuted}
 private silence(){const track=this.track();if(track){track.stopOnMute=true;track.mediaStreamTrack.enabled=false;track.mediaStreamTrack.stop()}}
 mute(value:boolean){
  if(value)this.silence();
  const operation=this.pending.then(async()=>{if(this.closed)return;const track=this.track();if(track)track.stopOnMute=true;try{await this.setMuted(value);if(this.closed||value)this.silence()}catch(error){this.silence();throw error}});
  this.pending=operation.catch(()=>{});return operation;
 }
 async close(){this.closed=true;this.silence();await this.pending;this.silence()}
}
