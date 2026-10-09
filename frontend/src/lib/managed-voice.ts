import type { VoiceConversation } from '@elevenlabs/client';
import type { Room } from 'livekit-client';
import { MicrophoneGate } from './microphone-gate';
export type ManagedVoiceSession=Pick<VoiceConversation,'getInputByteFrequencyData'|'getOutputByteFrequencyData'|'endSession'|'getInputVolume'|'getOutputVolume'|'setVolume'> & {setMicMuted(value:boolean):Promise<void>};
export async function startManagedVoice(options:Extract<Parameters<typeof VoiceConversation.startSession>[0],{agentId:string}>):Promise<ManagedVoiceSession>{
 const {Conversation}=await import('@elevenlabs/client');
 const {setSetupStrategy,createConnection,setupWebRTCSession}=await import('@elevenlabs/client/internal');
 let gate:MicrophoneGate|undefined;
 // Use the SDK's exported setup hook rather than accessing private session fields.
 setSetupStrategy(async fullOptions=>{
  const permission=await navigator.mediaDevices.getUserMedia({audio:true});
  try{
   const connection=await createConnection(fullOptions);
   try{
    const setup=setupWebRTCSession(connection);
    if(!('getRoom'in connection)||typeof connection.getRoom!=='function')throw new Error('Voice microphone unavailable');
    const room=connection.getRoom() as Room;
    gate=new MicrophoneGate(()=>[...room.localParticipant.audioTrackPublications.values()].find(publication=>publication.source==='microphone')?.audioTrack,muted=>setup.input.setMuted(muted));
    return setup;
   }catch(error){connection.close();throw error}
  }finally{permission.getTracks().forEach(track=>track.stop())}
 });
 const conversation=await Conversation.startSession({...options,connectionType:'webrtc'});
 if(conversation.type!=='voice'){await conversation.endSession();throw new Error('Expected voice session')}
 if(!gate){await conversation.endSession();throw new Error('Voice microphone unavailable')}
 const microphone=gate;
 // Keep the public conversation methods, but return a mute operation we can await.
 return {
  setMicMuted:value=>microphone.mute(value),
  endSession:async()=>{await microphone.close();await conversation.endSession()},
  getInputByteFrequencyData:()=>conversation.getInputByteFrequencyData(),
  getOutputByteFrequencyData:()=>conversation.getOutputByteFrequencyData(),
  getInputVolume:()=>conversation.getInputVolume(),getOutputVolume:()=>conversation.getOutputVolume(),setVolume:value=>conversation.setVolume(value),
 };
}
