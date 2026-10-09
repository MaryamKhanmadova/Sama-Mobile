const spokenTags=/\[(?:calm|empathetic|warm|serious|reassuring|relieved|cheerfully|softly|sighs|happy|sad|laughs|chuckles|whispers|excited)\]/gi;
export function captionText(text:string){return text.replace(spokenTags,'').replace(/ {2,}/g,' ').trim()}
export function callContext(msisdn:string,conversationId:string){return {msisdn,conversation_id:conversationId}}
