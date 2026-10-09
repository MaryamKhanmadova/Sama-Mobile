"""Storage interface. LocalStore (JSON in memory) and DynamoStore implement the same methods,
so the agent, eval and API never know which backend they run on."""
from __future__ import annotations

from abc import ABC, abstractmethod


class Store(ABC):
    # ---- reads: customer world ----
    @abstractmethod
    def get_line(self, msisdn: str) -> dict | None: ...

    @abstractmethod
    def get_customer(self, customer_id: str) -> dict | None: ...

    def get_customer_by_msisdn(self, msisdn: str) -> dict | None:
        line = self.get_line(msisdn)
        return self.get_customer(line["customer_id"]) if line else None

    @abstractmethod
    def list_events(self, msisdn: str, since: str | None = None, until: str | None = None,
                    types: set[str] | None = None) -> list[dict]:
        """Events for one line, ascending by time."""

    @abstractmethod
    def list_incidents(self, region: str | None = None) -> list[dict]: ...

    @abstractmethod
    def get_catalog(self) -> dict: ...

    # ---- writes: customer world ----
    @abstractmethod
    def apply_mutation(self, msisdn: str, events: list[dict], line_patch: dict | None = None) -> None:
        """Append events and patch the line atomically (dotted keys allowed, e.g. 'settings.roaming_enabled')."""

    # ---- resolutions / adjustments (idempotent money movement) ----
    @abstractmethod
    def put_resolution(self, res: dict) -> None: ...

    @abstractmethod
    def get_resolution(self, resolution_id: str) -> dict | None: ...

    @abstractmethod
    def mark_resolution_applied(self, resolution_id: str) -> bool:
        """True if this call flipped applied False->True; False if it was already applied."""

    @abstractmethod
    def put_adjustment(self, adj: dict) -> bool:
        """Conditional write on idempotency_key. False if an adjustment with that key already exists."""

    @abstractmethod
    def list_adjustments(self, msisdn: str, since: str | None = None) -> list[dict]: ...

    # ---- cases ----
    @abstractmethod
    def put_case(self, case: dict) -> None: ...

    @abstractmethod
    def get_case(self, case_id: str) -> dict | None: ...

    @abstractmethod
    def list_cases(self, status: str | None = None, msisdn: str | None = None, limit: int = 100) -> list[dict]: ...

    # ---- sessions ----
    @abstractmethod
    def put_session_meta(self, meta: dict) -> None: ...

    @abstractmethod
    def append_session_turn(self, session_id: str, seq: int, turn: dict) -> None: ...

    @abstractmethod
    def get_session(self, session_id: str) -> dict | None: ...

    # ---- knowledge base ----
    @abstractmethod
    def list_kb_chunks(self) -> list[dict]: ...

    @abstractmethod
    def put_kb_chunks(self, chunks: list[dict]) -> None: ...


def apply_patch(obj: dict, patch: dict) -> None:
    """Apply {'a.b': v} style patches in place."""
    for key, value in patch.items():
        target = obj
        parts = key.split(".")
        for p in parts[:-1]:
            target = target.setdefault(p, {})
        target[parts[-1]] = value
