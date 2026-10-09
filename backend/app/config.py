"""Runtime configuration from environment variables (.env is loaded if present)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BAKU = timezone(timedelta(hours=4))


def _load_dotenv() -> None:
    f = ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    store: str = field(default_factory=lambda: _env("STORE", "local"))  # local | dynamodb
    seed_dir: Path = field(default_factory=lambda: Path(_env("SEED_DIR", str(ROOT / "data" / "seed" / "out"))))
    table_prefix: str = field(default_factory=lambda: _env("TABLE_PREFIX", "sema_"))
    aws_region: str = field(default_factory=lambda: _env("AWS_REGION", "eu-central-1"))

    openrouter_key: str = field(default_factory=lambda: _env("OPENROUTER_API_KEY"))
    openrouter_url: str = field(default_factory=lambda: _env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
    provider_order: str = field(default_factory=lambda: _env("OPENROUTER_PROVIDER_ORDER", "anthropic"))
    fallback_model: str = field(default_factory=lambda: _env("OPENROUTER_FALLBACK_MODEL"))
    app_title: str = field(default_factory=lambda: _env("OPENROUTER_APP_TITLE", "Sema Mobile"))
    referer: str = field(default_factory=lambda: _env("OPENROUTER_HTTP_REFERER"))
    chat_model: str = field(default_factory=lambda: _env("CHAT_MODEL", "anthropic/claude-sonnet-5.5"))
    voice_model: str = field(default_factory=lambda: _env("VOICE_MODEL", "anthropic/claude-haiku-5.5"))
    chat_effort: str = field(default_factory=lambda: _env("CHAT_EFFORT", "medium"))
    voice_effort: str = field(default_factory=lambda: _env("VOICE_EFFORT", "low"))
    llm_timeout_s: float = field(default_factory=lambda: float(_env("LLM_TIMEOUT_S", "45")))

    embeddings: str = field(default_factory=lambda: _env("EMBEDDINGS", "none"))  # none | openrouter
    embed_model: str = field(default_factory=lambda: _env("EMBED_MODEL"))
    kb_dir: Path = field(default_factory=lambda: Path(_env("KB_DIR", str(ROOT / "data" / "kb"))))
    prompt_file: Path = field(default_factory=lambda: Path(_env("PROMPT_FILE", str(ROOT / "docs" / "MARYAM_SYSTEM_PROMPT.md"))))

    api_keys: tuple[str, ...] = field(default_factory=lambda: tuple(k for k in _env("API_KEYS").split(",") if k))
    sema_now: str = field(default_factory=lambda: _env("SEMA_NOW"))
    default_voice_msisdn: str = field(default_factory=lambda: _env("DEFAULT_VOICE_MSISDN"))

    def now(self) -> datetime:
        """Demo clock: seed data is generated relative to SEMA_NOW, so the app must use the same clock."""
        if self.sema_now:
            return datetime.fromisoformat(self.sema_now)
        return datetime.now(BAKU).replace(microsecond=0)

    def model_for(self, channel: str) -> tuple[str, str]:
        if channel == "voice":
            return self.voice_model, self.voice_effort
        return self.chat_model, self.chat_effort


settings = Settings()
