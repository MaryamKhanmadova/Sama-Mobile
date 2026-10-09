"""DynamoDB-backed store. Table layout is created by infra/create_tables.py (see TABLES below)."""
from __future__ import annotations

import json
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from .base import Store

# name -> (partition key, sort key or None, [GSIs as (index_name, pk, sk)]) — matches the tables the backend team
# created (prefix e.g. "paralos."). Time ordering of events is done in code (SK is event_id, not time).
TABLES = {
    "customers": ("customer_id", None, []),
    "lines": ("msisdn", None, [("gsi", "customer_id", None)]),
    "events": ("msisdn", "event_id", []),
    "catalog": ("item_id", None, [("item_type", "item_type", None)]),
    "incidents": ("region", "incident_id", [("status", "status", None)]),
    "cases": ("case_id", None, []),
    "sessions": ("session_id", "seq", []),
    "resolutions": ("resolution_id", None, [("msisdn", "msisdn", None)]),
    "adjustments": ("msisdn", "idempotency_key", []),
    "kb_chunks": ("chunk_id", None, [("doc_id", "doc_id", None)]),
}
NUMERIC_SORT_KEYS = {("sessions", "seq")}


def to_ddb(obj):
    return json.loads(json.dumps(obj), parse_float=Decimal)


def from_ddb(obj):
    if isinstance(obj, list):
        return [from_ddb(x) for x in obj]
    if isinstance(obj, dict):
        return {k: from_ddb(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    return obj


class DynamoStore(Store):
    def __init__(self, region: str, prefix: str = "sema_"):
        self.ddb = boto3.resource("dynamodb", region_name=region)
        self.client = boto3.client("dynamodb", region_name=region)
        self.prefix = prefix
        self.t = {name: self.ddb.Table(prefix + name) for name in TABLES}
        self._ser = TypeSerializer()
        self._catalog_cache: dict | None = None

    def _query_all(self, table, **kw) -> list[dict]:
        items, start = [], None
        while True:
            if start:
                kw["ExclusiveStartKey"] = start
            resp = table.query(**kw)
            items.extend(resp.get("Items", []))
            start = resp.get("LastEvaluatedKey")
            if not start:
                return from_ddb(items)

    # ---- reads ----
    def get_line(self, msisdn):
        item = self.t["lines"].get_item(Key={"msisdn": msisdn}).get("Item")
        return from_ddb(item) if item else None

    def get_customer(self, customer_id):
        item = self.t["customers"].get_item(Key={"customer_id": customer_id}).get("Item")
        return from_ddb(item) if item else None

    def list_events(self, msisdn, since=None, until=None, types=None):
        items = self._query_all(self.t["events"], KeyConditionExpression=Key("msisdn").eq(msisdn))
        items = [e for e in items if (not since or e["ts"] >= since) and (not until or e["ts"] <= until)
                 and (not types or e["type"] in types)]
        items.sort(key=lambda e: (e["ts"], e["event_id"]))
        return items

    def list_incidents(self, region=None):
        if region:
            items = self._query_all(self.t["incidents"], KeyConditionExpression=Key("region").eq(region))
        else:
            items = from_ddb(self.t["incidents"].scan().get("Items", []))
        return items

    def get_catalog(self):
        if self._catalog_cache is None:
            items = from_ddb(self.t["catalog"].scan().get("Items", []))
            cat: dict = {}
            for it in items:
                cat.setdefault(it["item_type"], {})[it["item_id"]] = it
            self._catalog_cache = cat
        return self._catalog_cache

    # ---- writes ----
    def _event_item(self, e: dict) -> dict:
        return to_ddb(e)

    def apply_mutation(self, msisdn, events, line_patch=None):
        ops = []
        for e in events:
            ops.append({"Put": {"TableName": self.prefix + "events",
                                "Item": {k: self._ser.serialize(v) for k, v in self._event_item(e).items()}}})
        if line_patch:
            names, values, sets = {}, {}, []
            for i, (key, val) in enumerate(line_patch.items()):
                path = []
                for j, part in enumerate(key.split(".")):
                    names[f"#p{i}_{j}"] = part
                    path.append(f"#p{i}_{j}")
                values[f":v{i}"] = self._ser.serialize(to_ddb(val))
                sets.append(f"{'.'.join(path)} = :v{i}")
            ops.append({"Update": {"TableName": self.prefix + "lines", "Key": {"msisdn": {"S": msisdn}},
                                   "UpdateExpression": "SET " + ", ".join(sets),
                                   "ExpressionAttributeNames": names, "ExpressionAttributeValues": values}})
        for i in range(0, len(ops), 100):
            self.client.transact_write_items(TransactItems=ops[i:i + 100])

    def put_resolution(self, res):
        self.t["resolutions"].put_item(Item=to_ddb(res))

    def get_resolution(self, resolution_id):
        item = self.t["resolutions"].get_item(Key={"resolution_id": resolution_id}).get("Item")
        return from_ddb(item) if item else None

    def mark_resolution_applied(self, resolution_id):
        try:
            self.t["resolutions"].update_item(
                Key={"resolution_id": resolution_id}, UpdateExpression="SET applied = :t",
                ConditionExpression=Attr("resolution_id").exists() & Attr("applied").ne(True),
                ExpressionAttributeValues={":t": True})
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def put_adjustment(self, adj):
        try:
            self.t["adjustments"].put_item(Item=to_ddb(adj), ConditionExpression=Attr("idempotency_key").not_exists())
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def list_adjustments(self, msisdn, since=None):
        items = self._query_all(self.t["adjustments"], KeyConditionExpression=Key("msisdn").eq(msisdn))
        return [a for a in items if not since or a["ts"] >= since]

    def put_case(self, case):
        self.t["cases"].put_item(Item=to_ddb(case))

    def get_case(self, case_id):
        item = self.t["cases"].get_item(Key={"case_id": case_id}).get("Item")
        return from_ddb(item) if item else None

    def list_cases(self, status=None, msisdn=None, limit=100):
        items, start = [], None
        while True:
            kw = {"ExclusiveStartKey": start} if start else {}
            resp = self.t["cases"].scan(**kw)
            items.extend(from_ddb(resp.get("Items", [])))
            start = resp.get("LastEvaluatedKey")
            if not start:
                break
        items = [c for c in items if (not status or c.get("status") == status) and (not msisdn or c.get("msisdn") == msisdn)]
        items.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        return items[:limit]

    def reset(self) -> None:
        """Demo reset: wipe runtime + world tables and re-upsert the seed (takes ~30-60 s)."""
        from infra.load_seed import main as load  # local import: infra depends on app, not the reverse
        load(reset=True)
        self._catalog_cache = None

    def put_session_meta(self, meta):
        self.t["sessions"].put_item(Item=to_ddb({**meta, "seq": 0}))

    def append_session_turn(self, session_id, seq, turn):
        self.t["sessions"].put_item(Item=to_ddb({**turn, "session_id": session_id, "seq": seq}))

    def get_session(self, session_id):
        items = self._query_all(self.t["sessions"], KeyConditionExpression=Key("session_id").eq(session_id))
        if not items:
            return None
        meta = next((i for i in items if i["seq"] == 0), {})
        return {"meta": meta, "turns": [i for i in items if i["seq"] != 0]}

    def list_kb_chunks(self):
        items, start = [], None
        while True:
            kw = {"ExclusiveStartKey": start} if start else {}
            resp = self.t["kb_chunks"].scan(**kw)
            items.extend(resp.get("Items", []))
            start = resp.get("LastEvaluatedKey")
            if not start:
                return from_ddb(items)

    def put_kb_chunks(self, chunks):
        with self.t["kb_chunks"].batch_writer() as bw:
            for c in chunks:
                bw.put_item(Item=to_ddb(c))
