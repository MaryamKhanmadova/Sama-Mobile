from __future__ import annotations

from functools import lru_cache

from app.config import settings

from .base import Store


@lru_cache(maxsize=1)
def get_store() -> Store:
    if settings.store == "dynamodb":
        from .dynamo import DynamoStore
        return DynamoStore(settings.aws_region, settings.table_prefix)
    from .local import LocalStore
    return LocalStore(settings.seed_dir)
