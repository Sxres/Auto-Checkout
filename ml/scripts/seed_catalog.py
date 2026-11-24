"""One-off seed of catalog.json into the store (issue #20).

Usage:
    uv run python ml/scripts/seed_catalog.py s3://bucket
    uv run python ml/scripts/seed_catalog.py ml/data/pipeline

Writes backend/app/catalog.json into the store root only if catalog.json is not already there
(IfNoneMatch="*"), so a rerun never overwrites edits. After this the repo file is only the
local-dev seed. Default dependencies only — no cv2/numpy, so it runs without the ml group.
"""

import sys
from pathlib import Path

from store import PreconditionFailed, Store

CATALOG = Path(__file__).resolve().parents[2] / "backend" / "app" / "catalog.json"


def main(root: str) -> None:
    store = Store(root)
    try:
        store.put("catalog.json", CATALOG.read_bytes(), if_none_match="*")
        print(f"Seeded catalog.json into {root}")
    except PreconditionFailed:
        print(f"catalog.json already exists in {root}; skipped")


if __name__ == "__main__":
    main(sys.argv[1])