"""Retrieval check against eval/cases.json using the app's RAG (BM25 only unless embeddings configured).

    python -m data.kb.check_retrieval

Reports recall@4 (any expected kb_doc among the top-4 chunks) and MRR.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.rag.index import KnowledgeBase

KB = Path(__file__).resolve().parent
ROOT = KB.parents[1]


def main() -> None:
    kb = KnowledgeBase(KB)
    cases = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))["cases"]
    hits, rr, n, misses = 0, 0.0, 0, []
    for c in cases:
        exp = set(c["expected"]["kb_docs"])
        if not exp:
            continue
        n += 1
        res = kb.search(" ".join(c["turns"]), k=20)
        docs = list(dict.fromkeys(r["doc_id"] for r in res))
        if exp & {r["doc_id"] for r in res[:4]}:
            hits += 1
        else:
            misses.append((c["id"], sorted(exp), docs[:3]))
        rank = next((i + 1 for i, d in enumerate(docs) if d in exp), None)
        rr += 1 / rank if rank else 0
    print(f"chunks={len(kb.chunks)} cases_with_kb={n} recall@4={hits / n:.2f} MRR={rr / n:.2f}")
    for m in misses:
        print("  miss", m)


if __name__ == "__main__":
    main()
