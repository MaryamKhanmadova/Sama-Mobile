"""Hybrid RAG over data/kb/*.md: BM25 (AZ/RU normalized) + optional embeddings, fused with RRF."""
from __future__ import annotations

import json
import logging
import math
import re
from pathlib import Path

import httpx
from rank_bm25 import BM25Okapi

log = logging.getLogger("sema.rag")
FOLD = str.maketrans("əıöüğşçİ", "eiougsci")


class Normalizer:
    def __init__(self, glossary: dict[str, str]):
        self.glossary = {k.lower(): v for k, v in glossary.items()}

    def tokens(self, text: str, expand: bool = False) -> list[str]:
        words = re.findall(r"[\wəıöüğşçİ]+", text.lower())
        if expand:
            words += [w2 for w in words if w in self.glossary for w2 in self.glossary[w].lower().split()]
        return [w.translate(FOLD)[:6] for w in words if len(w) > 1]


def load_chunks(kb_dir: Path) -> list[dict]:
    out = []
    for p in sorted(kb_dir.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip()
        meta = re.search(r"qaydalar:\s*(.+)", text)
        rules = re.findall(r"R-[A-Z]+-\d+", meta.group(1)) if meta else []
        for sec in re.split(r"^## ", text, flags=re.M)[1:]:
            head = sec.splitlines()[0].strip()
            slug = re.sub(r"[^a-z0-9]+", "-", head.lower().translate(FOLD)).strip("-")
            out.append({"chunk_id": f"{p.stem}#{slug}", "doc_id": p.stem, "title": title, "section": head,
                        "text": f"[{title} › {head}]\n{sec.strip()}",
                        "rule_ids": sorted(set(re.findall(r"R-[A-Z]+-\d+", sec)) or rules)})
    return out


class KnowledgeBase:
    def __init__(self, kb_dir: Path, embed_cfg: dict | None = None):
        glossary_file = kb_dir / "glossary_ru_az.json"
        glossary = json.loads(glossary_file.read_text(encoding="utf-8")) if glossary_file.exists() else {}
        self.norm = Normalizer(glossary)
        self.chunks = load_chunks(kb_dir)
        self.bm25 = BM25Okapi([self.norm.tokens(c["text"]) for c in self.chunks]) if self.chunks else None
        self.embed_cfg = embed_cfg or {}
        self.vectors: list[list[float]] | None = None

    # ---- optional dense retrieval via OpenRouter embeddings ----
    def _embed(self, texts: list[str]) -> list[list[float]] | None:
        cfg = self.embed_cfg
        if not cfg.get("api_key") or not cfg.get("model"):
            return None
        try:
            r = httpx.post(f'{cfg["base_url"]}/embeddings', timeout=20,
                           headers={"Authorization": f'Bearer {cfg["api_key"]}'},
                           json={"model": cfg["model"], "input": texts})
            r.raise_for_status()
            return [d["embedding"] for d in r.json()["data"]]
        except Exception as e:  # noqa: BLE001 — retrieval must degrade to BM25, never fail
            log.warning("embeddings unavailable, BM25 only: %s", e)
            return None

    def warm(self) -> None:
        if self.chunks and self.embed_cfg.get("enabled"):
            self.vectors = self._embed([c["text"] for c in self.chunks])
            log.info("kb dense index: %s", "on" if self.vectors else "off")

    @staticmethod
    def _cos(a, b) -> float:
        num = sum(x * y for x, y in zip(a, b))
        den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1.0
        return num / den

    def search(self, query: str, k: int = 6, category: str | None = None) -> list[dict]:
        if not self.bm25:
            return []
        scores = self.bm25.get_scores(self.norm.tokens(query, expand=True))
        bm_rank = sorted(range(len(self.chunks)), key=lambda i: -scores[i])[:20]
        ranks = [bm_rank]
        if self.vectors:
            qv = self._embed([query])
            if qv:
                sims = [self._cos(qv[0], v) for v in self.vectors]
                ranks.append(sorted(range(len(self.chunks)), key=lambda i: -sims[i])[:20])
        fused: dict[int, float] = {}
        for rank in ranks:
            for pos, i in enumerate(rank):
                fused[i] = fused.get(i, 0.0) + 1.0 / (60 + pos + 1)
        out, per_doc = [], {}
        for i in sorted(fused, key=lambda i: -fused[i]):
            c = self.chunks[i]
            if category and category not in c["doc_id"]:
                continue
            if per_doc.get(c["doc_id"], 0) >= 2:
                continue
            per_doc[c["doc_id"]] = per_doc.get(c["doc_id"], 0) + 1
            out.append({**c, "score": round(fused[i], 4)})
            if len(out) >= k:
                break
        return out
