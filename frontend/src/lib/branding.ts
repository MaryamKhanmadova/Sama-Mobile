// Display-only migration for legacy assistant responses; never change user messages.
export function brandText(text:string,locale:'az'|'en'|'ru'='en'){
 const product=locale==='az'?'Səma Mobile':'Sama Mobile';
 const agent=locale==='az'?'Məryəm Agent':'Maryam Agent';
 return text.replace(/Maryam Care|Məryəm Care|Sama Care|Səma Care|Sama Mobile|Səma Mobile|Sema Mobile/gi,product).replace(/Maryam Agent|Məryəm Agent/gi,agent).replace(/\bAyla(?: agenti| agent)?\b/gi,agent);
}
