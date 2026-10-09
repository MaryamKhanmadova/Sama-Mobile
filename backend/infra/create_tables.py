"""Create the 10 Səma Mobile DynamoDB tables (on-demand). Idempotent.

    python -m infra.create_tables            # create missing tables
    python -m infra.create_tables --drop     # delete sema_* tables first (DESTRUCTIVE)
"""
from __future__ import annotations

import argparse

import boto3
from botocore.exceptions import ClientError

from app.config import settings
from app.store.dynamo import NUMERIC_SORT_KEYS, TABLES


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop", action="store_true")
    args = ap.parse_args()
    ddb = boto3.client("dynamodb", region_name=settings.aws_region)
    existing = set(ddb.list_tables()["TableNames"])
    for name, (pk, sk, gsis) in TABLES.items():
        table = settings.table_prefix + name
        if args.drop and table in existing:
            ddb.delete_table(TableName=table)
            ddb.get_waiter("table_not_exists").wait(TableName=table)
            existing.discard(table)
            print("dropped", table)
        if table in existing:
            print("exists ", table)
            continue
        attrs = {pk: "S"}
        keys = [{"AttributeName": pk, "KeyType": "HASH"}]
        if sk:
            attrs[sk] = "N" if (name, sk) in NUMERIC_SORT_KEYS else "S"
            keys.append({"AttributeName": sk, "KeyType": "RANGE"})
        gsi_defs = []
        for idx, gpk, gsk in gsis:
            attrs.setdefault(gpk, "S")
            ks = [{"AttributeName": gpk, "KeyType": "HASH"}]
            if gsk:
                attrs.setdefault(gsk, "S")
                ks.append({"AttributeName": gsk, "KeyType": "RANGE"})
            gsi_defs.append({"IndexName": idx, "KeySchema": ks, "Projection": {"ProjectionType": "ALL"}})
        kw = {"TableName": table, "KeySchema": keys, "BillingMode": "PAY_PER_REQUEST",
              "AttributeDefinitions": [{"AttributeName": a, "AttributeType": t} for a, t in attrs.items()]}
        if gsi_defs:
            kw["GlobalSecondaryIndexes"] = gsi_defs
        ddb.create_table(**kw)
        print("created", table)
    for name in TABLES:
        ddb.get_waiter("table_exists").wait(TableName=settings.table_prefix + name)
    try:
        ddb.update_time_to_live(TableName=settings.table_prefix + "resolutions",
                                TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_epoch"})
    except ClientError as e:
        if "already enabled" not in str(e).lower():
            print("ttl:", e)
    print("all tables ACTIVE")


if __name__ == "__main__":
    main()
