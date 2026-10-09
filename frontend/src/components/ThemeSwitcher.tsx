import {Moon,Sun,Monitor} from 'lucide-react';
import {setTheme,useTheme,type ThemeChoice} from '../lib/theme';
import {t} from '../lib/i18n';
export function ThemeSwitcher(){const choice=useTheme();const Icon=choice==='dark'?Moon:choice==='light'?Sun:Monitor;return <label className="theme-switcher"><Icon size={18}/><span className="sr-only">{t('theme.label')}</span><select aria-label={t('theme.label')} value={choice} onChange={e=>setTheme(e.target.value as ThemeChoice)}>{(['system','light','dark'] as const).map(value=><option key={value} value={value}>{t(`theme.${value}`)}</option>)}</select></label>}
