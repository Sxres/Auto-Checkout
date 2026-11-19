"""One-off import of the 4 starter products in fooddata/ as captures (issue #12).

Usage:
    uv run --group ml python ml/scripts/import_fooddata.py fooddata ml/data/pipeline   # also annotates
    uv run python ml/scripts/import_fooddata.py fooddata s3://bucket   # the upload triggers the annotator

By duration (these iPhone files have correct headers): 20 s or more -> train, the older ~15 s
videos -> val, under 8 s -> swipe. The capture ID is derived from the file's MD5, so a file copied
into two folders becomes one capture and a rerun skips what is already imported.
"""

import hashlib
import sys
import uuid
from pathlib import Path

import cv2

from annotate import Store, add_capture, annotate
from dataset import classes

FOLDERS = {"coca cola": "COKE-330", "ketchup": "HEINZ-570", "ice cream": "BJ-473", "nutella": "NUT-750"}


def kind(video: Path) -> str:
    cap = cv2.VideoCapture(str(video))
    seconds = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)  # header: fine for iPhone files only
    return "train" if seconds >= 20 else "swipe" if seconds < 8 else "val"


def main(src: Path, root: str) -> None:
    assert set(FOLDERS.values()) <= set(classes().values()), "every starter SKU must be in the catalog"
    store, seen = Store(root), {}
    for folder, sku in FOLDERS.items():
        for video in sorted((src / folder).glob("*.MOV")):
            cid = uuid.UUID(hashlib.md5(video.read_bytes()).hexdigest(), version=4).hex
            if cid in seen:
                print(f"Skipped {folder}/{video.name}: same file as {seen[cid]}")
                continue
            seen[cid] = f"{folder}/{video.name}"
            if not store.exists(f"captures/{cid}/capture.json"):
                add_capture(store, video, sku, kind(video), cid)
            # On S3 the upload triggers the annotator; locally nothing does
            if not store.bucket and not store.exists(f"captures/{cid}/manifest.json"):
                annotate(store, cid)
            print(f"{folder}/{video.name} -> {cid}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])
