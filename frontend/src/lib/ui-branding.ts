import { brandText as formatBrandText } from './branding';
import { getLocale } from './i18n';
export const brandText=(text:string)=>formatBrandText(text,getLocale());
