"""Streaming text post-processing.
- web: strip all [tags]
- voice: keep only whitelisted emotion tags, spell AZN amounts and clock times in Azerbaijani words,
  drop '...', and release text sentence by sentence (better TTS prosody)."""
from __future__ import annotations

import re

ALLOWED_TAGS = {"calm", "warm", "empathetic", "softly", "reassuring", "serious", "relieved", "cheerfully", "sighs"}
ONES = ["", "bir", "iki", "üç", "dörd", "beş", "altı", "yeddi", "səkkiz", "doqquz"]
TENS = ["", "on", "iyirmi", "otuz", "qırx", "əlli", "altmış", "yetmiş", "səksən", "doxsan"]


def az_words(n: int) -> str:
    if n == 0:
        return "sıfır"
    parts = []
    if n >= 1000:
        th = n // 1000
        parts.append("min" if th == 1 else f"{az_words(th)} min")
        n %= 1000
    if n >= 100:
        h = n // 100
        parts.append("yüz" if h == 1 else f"{ONES[h]} yüz")
        n %= 100
    if n >= 10:
        parts.append(TENS[n // 10])
        n %= 10
    if n:
        parts.append(ONES[n])
    return " ".join(parts)


MONEY = re.compile(r"(\d+)(?:[.,](\d{1,2}))?\s*(AZN|azn|manat)(?:\s*(\d{1,2})\s*qəpik)?")
TIME = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")


def _money(m: re.Match) -> str:
    man = int(m.group(1))
    qep = m.group(2)
    if m.group(4):
        qep = m.group(4)
    q = int(qep.ljust(2, "0")) if qep else 0
    s = f"{az_words(man)} manat"
    return s + (f" {az_words(q)} qəpik" if q else "")


def _time(m: re.Match) -> str:
    h, mi = int(m.group(1)), int(m.group(2))
    if mi == 0:
        return az_words(h)
    return f"{az_words(h)} {'sıfır ' + az_words(mi) if mi < 10 else az_words(mi)}"


def normalize_for_voice(text: str, language: str) -> str:
    text = text.replace("...", ",").replace("…", ",")
    text = re.sub(r"[*_#`>|]", "", text)  # no markdown in speech
    if language != "ru":
        text = MONEY.sub(_money, text)
        text = TIME.sub(_time, text)
    return text


class StreamFilter:
    """Feed model deltas, get back text safe to emit for the channel."""

    def __init__(self, channel: str, language: str = "az"):
        self.channel = channel
        self.language = language
        self.buf = ""

    def _clean_tags(self, s: str) -> str:
        def repl(m):
            tag = m.group(1).strip().lower()
            return f"[{tag}]" if self.channel == "voice" and tag in ALLOWED_TAGS else ""
        return re.sub(r"\[([^\]\n]{1,40})\]", repl, s)

    def feed(self, chunk: str) -> str:
        self.buf += chunk
        if self.channel != "voice":
            # emit everything except a possibly unfinished trailing [tag
            cut = self.buf.rfind("[")
            if cut != -1 and "]" not in self.buf[cut:] and len(self.buf) - cut < 42:
                out, self.buf = self.buf[:cut], self.buf[cut:]
            else:
                out, self.buf = self.buf, ""
            return self._clean_tags(out)
        # voice: release complete sentences only
        m = list(re.finditer(r"[.!?](\s|$)|\n", self.buf))
        if not m:
            return ""
        end = m[-1].end()
        out, self.buf = self.buf[:end], self.buf[end:]
        return normalize_for_voice(self._clean_tags(out), self.language)

    def flush(self) -> str:
        out, self.buf = self.buf, ""
        out = self._clean_tags(out)
        return normalize_for_voice(out, self.language) if self.channel == "voice" else out


FILLERS = {"az": "Bir saniyə, yoxlayıram. ", "ru": "Секунду, сейчас проверю. "}
