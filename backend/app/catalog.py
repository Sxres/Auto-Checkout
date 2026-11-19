# The model only knows numbers (0, 1, 2, 3). This turns those numbers into real products
# with a name and a price. Keep the numbers in the same order ml/scripts/prepare_dataset.py
# used when it built the training data, or every product gets the wrong label.

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).with_name("catalog.json")


@lru_cache(maxsize=1)
def load_catalog() -> dict[int, dict[str, Any]]:
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return {product["class_id"]: product for product in raw["products"]}


def product_for(class_id: int) -> dict[str, Any] | None:
    return load_catalog().get(class_id)