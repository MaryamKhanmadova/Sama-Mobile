import { locales, setLocale, t, useLocale } from '../lib/i18n';
export function LanguageSwitcher(){const current=useLocale();return <div className="language-switcher" role="group" aria-label={t('common.languageSwitcher')}>
 {locales.map(locale=><button key={locale} type="button" lang={locale} aria-label={t(`common.languages.${locale}`)} aria-pressed={locale===current} onClick={()=>setLocale(locale)}>{locale.toUpperCase()}</button>)}
 </div>}
