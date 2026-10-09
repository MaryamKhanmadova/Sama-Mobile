# Məryəm 3D avatar — frontend inteqrasiyası

Danışan, göz qırpan, emosiya göstərən 3D Məryəm. Three.js, bir ES modul, asılılıq yalnız `three@0.170.0`.

| Fayl | Nədir |
|---|---|
| `maryam.glb` | Model (Meshopt + WebP, 2.3 MB). `Maryam`: 9 üz morph-u (`jawOpen, mouthSmile, mouthStretch, mouthFunnel, mouthPucker, mouthRollLower, mouthPress, browInnerUp, browDown`) · `MouthGap`: ağız boşluğu lenti · `Eyelids`: göz qırpma · `EyeLeft`/`EyeRight`: fırlanan göz almaları |
| `maryam-avatar.js` | `MaryamAvatar` klası — render, viseme lipsync, canlı baxış, vəziyyətlər, emosiyalar, mimika |
| `demo.html` | Test səhifəsi (bütün funksiyalar düymələrlə) |
| `sample.mp3` | Məryəmin səs nümunəsi (lipsync testi) |

## 1. Lokal işə salmaq
```bash
cd frontend/avatar
python -m http.server 8777
```
Brauzerdə `http://localhost:8777/demo.html` (file:// ilə açmayın — GLB yüklənməz).

## 2. Layihəyə qoşmaq
```bash
npm i three@0.170.0
```
`maryam.glb`-ni `public/avatar/`-a, `maryam-avatar.js`-i `src/avatar/`-a qoyun.

```tsx
import { useEffect, useRef } from "react";
import { MaryamAvatar } from "./avatar/maryam-avatar.js";

export function MaryamView({ onReady }: { onReady?: (a: MaryamAvatar) => void }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const maryam = new MaryamAvatar(box.current!, { src: "/avatar/maryam.glb", framing: "bust" }); // "face" = yaxın plan
    maryam.load().then(() => onReady?.(maryam));
    return () => maryam.dispose();
  }, []);
  return <div ref={box} style={{ width: "100%", aspectRatio: "1 / 1.05" }} />;
}
```
Fon şəffafdır — glassmorphism kartın içinə qoyun.

## 3. API
| Metod | Nə edir |
|---|---|
| `setState("idle" \| "listening" \| "thinking" \| "speaking")` | Başın pozası, göz qırpma tezliyi, sakit ifadə |
| `setEmotion("happy" \| "empathetic" \| "serious" \| "concerned" \| "neutral", { intensity, durationMs })` | Üz ifadəsi (default 2.5 s) |
| `reactToText(text)` | Mətndə `[empathetic]`, `[warm]`, `[serious]` kimi tag varsa emosiyanı qoşur |
| `connectAudio(audioEl \| MediaStream)` | **Real lipsync** istənilən səsdən: spektrdən viseme (a/e/i · o/u/w · f/v · b/m/p), hecalar arası və fasilədə ağız tam bağlanır |
| `useFrequencySource(fn, range?)` | Kənar FFT mənbəyi. Default `[100, 8000]` Hz = ElevenLabs SDK `getOutputByteFrequencyData()`. Xam AnalyserNode üçün sample rate (rəqəm) verin |
| `stopAudio()` | Səs lipsync-ini ayır (zəng bitəndə) |
| `mount(container, { framing })` | Eyni avatarı (GLB yenidən yüklənmədən) başqa konteynerə köçür — səhifə keçidləri, chat → zəng |
| `speakText(text)` | Səssiz lipsync (chat rejimi) — hər hərf öz viseme-si ilə, vergül/nöqtədə real fasilə |
| `lookAt(x, y)` | Baxışı ekran nöqtəsinə yönəlt (-1..1); `null` — buraxmaq. Default olaraq kursoru yüngülcə izləyir (`followPointer: false` ilə söndürülür) |
| `dispose()` | Təmizləmə |

Opsiyalar: `{ src, framing: "bust"|"face", transparent, pixelRatioCap, followPointer, reducedMotion }` (`reducedMotion` default olaraq OS-un `prefers-reduced-motion` ayarıdır). Avatar ekrandan kənarda olanda render dayanır.

## 4. Backend event-ləri → avatar (chat, SSE/WS)
| Event | Avatar |
|---|---|
| `ack` | `setState("thinking")` |
| `status` | `setState("thinking")` (gözlər yana, qaşlar azca çatılır) |
| `delta` | ilk delta-da `reactToText(text)`; bütün mətn gələndə `speakText(fullText)` (və ya TTS səsi varsa `connectAudio`) |
| `action` (`ok: true`, `credited_azn`) | `setEmotion("happy", { durationMs: 3000 })` |
| `handoff` | `setEmotion("empathetic", { durationMs: 4000 })` |
| `error` | `setEmotion("concerned")` |
| `done` | `setState("idle")` |
| İstifadəçi yazmağa başlayanda | `setState("listening")` |

## 5. Səsli zəng (ElevenLabs `@elevenlabs/react`)
```tsx
const conversation = useConversation({
  onModeChange: ({ mode }) => maryam.setState(mode === "speaking" ? "speaking" : "listening"),
  onMessage: ({ message, source }) => source === "ai" && maryam.reactToText(message),
  onDisconnect: () => maryam.setState("idle"),
});
// zəng başlayandan sonra — Məryəmin səsinin FFT-si ilə lipsync:
maryam.useFrequencySource(() => conversation.getOutputByteFrequencyData());
```
Agent ID: `.env` → `ELEVENLABS_AGENT_ID`. SDK öz səsini oxudur; avatar yalnız FFT-ni oxuyur (ikinci audio element lazım deyil).

## 6. Canlılıq (avtomatik, heç nə çağırmaq lazım deyil)
- **Baxış:** sakkadlar — idle-da ətrafa baxır, dinləyəndə göz təması + mikro-sakkadlar, danışanda fikir başlayanda yana baxıb qayıdır, düşünəndə yuxarı-yana. Baş baxışı ~30% izləyir, aşağı baxanda göz qapaqları enir, böyük göz sıçrayışında bəzən qırpır.
- **Danışıq mimikası:** vurğulu hecada qaşlar qalxır + başla yüngül baş əymə; ≥350 ms fasilədə ağız bağlanır, göz qırpır, cümlə sonunda yüngül təbəssüm.
- **Fon:** nəfəs, mikro baş hərəkəti, arabir ikiqat göz qırpma, sakit üz ifadəsində kiçik dəyişkənlik.

## 7. Performans
- ~120k üçbucaq, 2K teksturalar — müasir noutbuk/telefonda 60 fps.
- Aşağı güclü cihaz: `new MaryamAvatar(el, { pixelRatioCap: 1 })`.
- Chat rejimində avatar kiçik (`framing: "face"`, 160–220 px), zəng rejimində böyük (`"bust"`).

## 8. Modelin necə qurulduğu (yenidən generasiya)
`assets/avatar/build_avatar.py` (Blender 5.2):
`maryam.png` → Tripo h3.1 (fal.ai) → yönəltmə, UV-qoruyan decimate (2M → 240k), dodaq yarığı (Dijkstra ilə təbii çökəkdən),
ağız bölgəsi decimate-dən qorunur, procedural morph target-lər, dodaq çökəyi ayrıca tünd "MouthGap" lentinə çevrilir (çənə ilə uzanır), viseme morph-ları (`mouthRollLower` f/v, `mouthPress` b/m/p), göz qapaqları (üzə ray-cast ilə yapışdırılmış), göz yerində ayrıca göz almaları (procedural qəhvəyi iris) → `gltf-transform meshopt`.
```bash
blender -b --python assets/avatar/build_avatar.py -- assets/avatar/ayla_tripo.glb assets/avatar/ayla_rigged_raw.glb
npx @gltf-transform/cli meshopt assets/avatar/ayla_rigged_raw.glb frontend/avatar/maryam.glb
```

## Məlum məhdudiyyətlər
- Ağız içində diş/dil yoxdur — açılan hissə tünd boşluqdur (stilizə üslubda təbii görünür).
- Bütün büst bir mesh-dir: baş hərəkəti çiyinləri də azca döndərir (bucaqlar ±5°-dən kiçikdir).
