# Shared store dependency (issue #20): one get_store object so every API router and the
# tests' dependency_overrides key on the same function. AVC_STORE is an S3 bucket
# ("s3://bucket") or a local directory with the same layout.

import os
from typing import Annotated

from fastapi import Depends
from store import Store


def store_root() -> str:
    return os.environ.get("AVC_STORE", "ml/data/pipeline")


def get_store() -> Store:
    return Store(store_root())


StoreDep = Annotated[Store, Depends(get_store)]