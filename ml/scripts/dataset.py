"""Dataset build and materialize (issue #12). The retrain job (#16) runs both before it trains.

Usage:
    uv run python ml/scripts/dataset.py build ROOT
    uv run python ml/scripts/dataset.py materialize ROOT VERSION OUT
    uv run --group ml yolo train cfg=ml/configs/train.yaml model=yolo11s.pt data=OUT/data.yaml

ROOT is a local directory or s3://bucket with the S3 layout in ml/README.md.
`build` lists every `ready` capture (one with a manifest) in datasets/{version}/manifest.json and
copies no images. `materialize` turns that manifest into a local YOLO folder: data.yaml,
images/{train,val}/, labels/{train,val}/ with catalog class IDs, and swipes/{sku}/ (raw swipe videos).
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from annotate import KINDS, Store

CATALOG = Path(__file__).resolve().parents[2] / "backend" / "app" / "catalog.json"


def classes(store: Store | None = None) -> dict[str, str]:
    """Class ID -> SKU for every product (retired included), so IDs match /recognize.
    Reads the store's catalog.json when present, else the repo seed (#20)."""
    data, _ = store.get_with_etag("catalog.json") if store is not None else (None, None)
    doc = json.loads(data) if data is not None else json.loads(CATALOG.read_text(encoding="utf-8"))
    products = sorted(doc["products"], key=lambda p: p["class_id"])
    ids = [p["class_id"] for p in products]
    # YOLO needs IDs 0..n-1; a retired product keeps its ID, so it must stay in the catalog
    assert ids == list(range(len(ids))), f"catalog class_id values must be 0..{len(ids) - 1}: {ids}"
    return {str(p["class_id"]): p["sku"] for p in products}


def build(store: Store, version: str | None = None) -> dict:
    names = classes(store)
    captures = {kind: [] for kind in KINDS}
    counts = {kind: {} for kind in KINDS}  # labelled frames for train and val, clips for swipe
    for key in store.keys("captures/"):
        if not key.endswith("/manifest.json"):
            continue
        m = json.loads(store.get(key))
        if m["sku"] not in names.values():
            raise ValueError(f"Capture {m['capture_id']} has SKU {m['sku']!r}, which is not in the catalog")
        captures[m["kind"]].append(m["capture_id"])
        n = 1 if m["kind"] == "swipe" else m["frames"]["labelled"]
        counts[m["kind"]][m["sku"]] = counts[m["kind"]].get(m["sku"], 0) + n
    version = version or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    manifest = {"version": version, "classes": names, "captures": captures, "counts": counts}
    store.put(f"datasets/{version}/manifest.json", json.dumps(manifest, indent=2).encode())
    return manifest


def materialize(store: Store, version: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=False)  # never mix two versions in one folder
    m = json.loads(store.get(f"datasets/{version}/manifest.json"))
    class_id = {sku: i for i, sku in m["classes"].items()}
    # shortcut: one request per file; add a thread pool when downloads slow the retrain down
    for split in ("train", "val"):
        (out / "labels" / split).mkdir(parents=True)
        for cid in m["captures"][split]:
            sku = json.loads(store.get(f"captures/{cid}/manifest.json"))["sku"]
            for key in store.keys(f"captures/{cid}/labels/"):
                stem = f"{cid}_{Path(key).stem}"
                box = store.get(key).decode().split()[1:]  # stored class is a placeholder
                (out / "labels" / split / f"{stem}.txt").write_text(f"{class_id[sku]} {' '.join(box)}\n")
                store.download(f"captures/{cid}/images/{Path(key).stem}.jpg", out / "images" / split / f"{stem}.jpg")
    for cid in m["captures"]["swipe"]:
        sku = json.loads(store.get(f"captures/{cid}/manifest.json"))["sku"]
        [raw] = store.keys(f"raw/{cid}/")
        store.download(raw, out / "swipes" / sku / f"{cid}{Path(raw).suffix}")
    names = "\n".join(f"  {i}: {sku}" for i, sku in m["classes"].items())
    (out / "data.yaml").write_text(
        f"# Dataset {version}, from ml/scripts/dataset.py\ntrain: images/train\nval: images/val\nnames:\n{names}\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build").add_argument("root")
    mat = sub.add_parser("materialize")
    mat.add_argument("root")
    mat.add_argument("version")
    mat.add_argument("out", type=Path)
    a = p.parse_args()
    if a.cmd == "build":
        print(json.dumps(build(Store(a.root)), indent=2))
    else:
        materialize(Store(a.root), a.version, a.out)
        print(f"Wrote {a.out / 'data.yaml'}")
