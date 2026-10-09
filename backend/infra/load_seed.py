"""Upsert seed data (data/seed/out/*.json) into DynamoDB. Re-running overwrites the same keys (idempotent).

    python -m infra.load_seed            # upsert everything
    python -m infra.load_seed --reset    # wipe events + runtime tables first (clean demo state), then upsert
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor

import boto3

from app.config import settings
from app.rag.index import load_chunks
from app.store.dynamo import TABLES, to_ddb


def _table(name: str):
    return boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.table_prefix + name)


def wipe(name: str) -> int:
    table = _table(name)
    pk, sk, _ = TABLES[name]
    keys = [k for k in (pk, sk) if k]
    n, start = 0, None
    with table.batch_writer() as bw:
        while True:
            kw = {"ProjectionExpression": ",".join(f"#k{i}" for i in range(len(keys))),
                  "ExpressionAttributeNames": {f"#k{i}": k for i, k in enumerate(keys)}}
            if start:
                kw["ExclusiveStartKey"] = start
            resp = table.scan(**kw)
            for it in resp.get("Items", []):
                bw.delete_item(Key={k: it[k] for k in keys})
                n += 1
            start = resp.get("LastEvaluatedKey")
            if not start:
                return n


def upsert(name: str, items: list[dict]) -> int:
    pk, sk, _ = TABLES[name]
    with _table(name).batch_writer(overwrite_by_pkeys=[k for k in (pk, sk) if k]) as bw:
        for it in items:
            bw.put_item(Item=to_ddb(it))
    return len(items)


def main(reset: bool = False) -> None:
    load = lambda n: json.loads((settings.seed_dir / f"{n}.json").read_text(encoding="utf-8"))  # noqa: E731
    if reset:
        names = ("events", "cases", "sessions", "resolutions", "adjustments", "lines")
        with ThreadPoolExecutor(6) as ex:
            for name, n in zip(names, ex.map(wipe, names)):
                print(f"cleared {name}: {n}")
    batches = {
        "customers": load("customers"), "lines": load("lines"), "events": load("events"),
        "incidents": load("incidents"), "catalog": load("catalog"), "kb_chunks": load_chunks(settings.kb_dir),
    }
    # events are the bulk: split into chunks and write in parallel
    ev = batches.pop("events")
    parts = [ev[i:i + 1500] for i in range(0, len(ev), 1500)]
    with ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(upsert, n, items) for n, items in batches.items()]
        futs += [ex.submit(upsert, "events", p) for p in parts]
        for f in futs:
            f.result()
    for n, items in batches.items():
        print(f"upserted {n}: {len(items)}")
    print(f"upserted events: {len(ev)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    main(reset=ap.parse_args().reset)
