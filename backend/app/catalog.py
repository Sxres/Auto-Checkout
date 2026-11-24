# The model only knows numbers (0, 1, 2, 3). This turns those numbers into real products
# with a name and a price. The training data takes its class IDs from this catalog too
# (ml/scripts/dataset.py): give a new product the next unused class_id, and never reuse or reorder them.
#
# Issue #20: catalog.json at the store root is the source of truth. read_catalog() is a fresh
# read for the products API; load_catalog() is a cached read for /recognize that skips retired
# products and reloads with the model (reset_catalog, called from inference).

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from store import Store

CATALOG_PATH = Path(__file__).with_name("catalog.json")


def _repo_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def read_catalog(store: Store) -> dict[str, Any]:
    """Fresh full catalog document: the store's catalog.json if present, else the repo seed."""
    data, _ = store.get_with_etag("catalog.json")
    return json.loads(data) if data is not None else _repo_catalog()


@lru_cache(maxsize=8)
def _load_by_root(root: str | None) -> dict[int, dict[str, Any]]:
    if root is not None:
        data, _ = Store(root).get_with_etag("catalog.json")
        doc = json.loads(data) if data is not None else _repo_catalog()
    else:
        doc = _repo_catalog()
    return {p["class_id"]: p for p in doc["products"] if not p.get("retired", False)}


def load_catalog() -> dict[int, dict[str, Any]]:
    """Cached class_id -> product for /recognize. Reads the store catalog when AVC_STORE is set,
    else the repo file; skips retired products. Cleared by reset_catalog when the model reloads."""
    return _load_by_root(os.environ.get("AVC_STORE"))


def product_for(class_id: int) -> dict[str, Any] | None:
    return load_catalog().get(class_id)


def reset_catalog() -> None:
    _load_by_root.cache_clear()