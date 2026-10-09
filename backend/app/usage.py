"""Read side of the monthly usage dashboard (table <prefix>usage_monthly, see docs/USAGE_TABLE.md).

DynamoDB in production; with STORE=local the same items are generated in memory by data/seed/usage.py.
"""
from __future__ import annotations

from decimal import Decimal
from functools import lru_cache

from app.config import settings

SUMMARY_KEY = "#ALL"


def plain(x):
    if isinstance(x, Decimal):
        return int(x) if x == x.to_integral_value() else float(x)
    if isinstance(x, list):
        return [plain(i) for i in x]
    if isinstance(x, dict):
        return {k: plain(v) for k, v in x.items()}
    return x


class UsageRepo:
    def months(self, msisdn: str, limit: int) -> list[dict]:
        """Newest month first."""
        raise NotImplementedError

    def month(self, msisdn: str, month: str) -> dict | None:
        raise NotImplementedError


class DynamoUsage(UsageRepo):
    def __init__(self):
        import boto3
        self.table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.table_prefix + "usage_monthly")

    def months(self, msisdn, limit):
        from boto3.dynamodb.conditions import Key
        items = self.table.query(KeyConditionExpression=Key("msisdn").eq(msisdn), ScanIndexForward=False,
                                 Limit=limit)["Items"]
        return [plain(i) for i in items]

    def month(self, msisdn, month):
        item = self.table.get_item(Key={"msisdn": msisdn, "month": month}).get("Item")
        return plain(item) if item else None


class LocalUsage(UsageRepo):
    def __init__(self):
        from data.seed.usage import build
        self.by_line: dict[str, list[dict]] = {}
        for it in build(settings.now()):
            self.by_line.setdefault(it["msisdn"], []).append(it)
        for its in self.by_line.values():
            its.sort(key=lambda i: i["month"], reverse=True)

    def months(self, msisdn, limit):
        return self.by_line.get(msisdn, [])[:limit]

    def month(self, msisdn, month):
        return next((i for i in self.by_line.get(msisdn, []) if i["month"] == month), None)


@lru_cache(maxsize=1)
def get_usage_repo() -> UsageRepo:
    return DynamoUsage() if settings.store == "dynamodb" else LocalUsage()
