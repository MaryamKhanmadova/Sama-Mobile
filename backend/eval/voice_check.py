"""Voice pipeline check through ElevenLabs (uses .env keys).

    python -m eval.voice_check            # 1) simulated conversation via the agent (ElevenLabs -> our backend)
                                          # 2) TTS -> STT round trip with latency

Saves the synthesized audio to eval/results/voice_check.mp3.
"""
from __future__ import annotations

import difflib
import re
import time

import httpx

from app.agent.voice import normalize_for_voice
from app.config import ROOT, _env

H = {"xi-api-key": _env("ELEVENLABS_API_KEY")}
API = "https://api.elevenlabs.io/v1"


def simulate(first_message: str) -> None:
    spec = {"simulation_specification": {"simulated_user_config": {
        "first_message": first_message, "language": "az",
        "prompt": {"prompt": "Sən Səma Mobile müştərisisən, Azərbaycan dilində qısa danışırsan. Problemin həll olunanda "
                             "təşəkkür edib söhbəti bitir.", "llm": "gemini-2.5-flash"}}}, "new_turns_limit": 6}
    t = time.time()
    r = httpx.post(f"{API}/convai/agents/{_env('ELEVENLABS_AGENT_ID')}/simulate-conversation", headers=H, json=spec, timeout=240)
    print(f"[simulate] HTTP {r.status_code} in {time.time() - t:.1f}s")
    r.raise_for_status()
    for m in r.json().get("simulated_conversation", []):
        print(f'  {m.get("role"):6} {(m.get("message") or "").strip()[:300]}')


def roundtrip(sentence: str) -> None:
    text = normalize_for_voice(sentence, "az")
    t, first, audio = time.time(), None, b""
    with httpx.stream("POST", f"{API}/text-to-speech/{_env('ELEVENLABS_VOICE_ID')}/stream", headers=H, timeout=60,
                      json={"text": text, "model_id": _env("ELEVENLABS_TTS_MODEL", "eleven_v4_turbo")}) as r:
        r.raise_for_status()
        for chunk in r.iter_bytes():
            first = first or time.time() - t
            audio += chunk
    out = ROOT / "eval" / "results" / "voice_check.mp3"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)
    print(f"[tts] first audio {first * 1000:.0f} ms, total {(time.time() - t) * 1000:.0f} ms -> {out}")
    t = time.time()
    s = httpx.post(f"{API}/speech-to-text", headers=H, data={"model_id": "scribe_v1", "language_code": "aze"},
                   files={"file": ("a.mp3", audio, "audio/mpeg")}, timeout=120)
    s.raise_for_status()
    heard = s.json().get("text", "")
    norm = lambda x: re.sub(r"[^\w\s]", "", re.sub(r"\[[^\]]+\]", "", x.lower())).split()  # noqa: E731
    sim = difflib.SequenceMatcher(None, norm(text), norm(heard)).ratio()
    print(f"[stt] {(time.time() - t) * 1000:.0f} ms, word similarity {sim:.2f}\n  said:  {text}\n  heard: {heard}")


if __name__ == "__main__":
    simulate("Salam, Gürcüstanda idim, rouminqi söndürmüşdüm, yenə də 4 manat 50 qəpik kəsilib.")
    roundtrip("[empathetic] Aysel xanım, haqlısınız. Rouminq söndürülü olduğu halda 4.50 AZN kəsilib. "
              "[warm] Məbləği balansınıza qaytardım, yeni balansınız 14 manatdır.")
