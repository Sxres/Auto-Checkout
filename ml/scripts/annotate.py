"""Annotator: one capture in, frames + YOLO labels + manifest out (issue #12).

Usage (one video and its SKU, into a local directory or an S3 bucket):
    uv run --group ml python ml/scripts/annotate.py ml/data/pipeline video.mp4 COKE-330 train
    uv run --group ml python ml/scripts/annotate.py s3://bucket video.mp4 COKE-330 train

On Lambda, `handler` runs on each S3 ObjectCreated event for raw/{capture_id}/source.<ext>
(infra/annotator.Dockerfile). The layout under the root is the S3 layout in ml/README.md.

Frames are sampled at 3 fps by decoded timestamp, never the header: browser WebM recordings
have no duration and a bogus frame count. Each sampled frame is normalized to 1280x720 landscape
and gets YOLOE-11l's most confident box for generic shape prompts. The class comes from the
capture's SKU, so labels store a placeholder class 0 and the dataset build sets the real ID.
A frame with no box is skipped. Swipe clips get only a manifest: #16 scores them as whole clips.
"""

import argparse
import io
import json
import math
import os
import sys
import tempfile
import uuid
from functools import cache
from pathlib import Path
from urllib.parse import unquote_plus

import cv2
import numpy as np
from PIL import Image, ImageOps
from store import Store, now

FPS = 3  # closer frames are near-duplicates
SIZE = (1280, 720)  # every image ends up landscape at the video frame size
# Generic shapes, not product names: the shape word finds the box, and the class comes from the SKU.
# Saved into the weights, so the image needs no text encoder (see ml/README.md).
LABEL_PROMPTS = ["can", "bottle", "jar", "tub", "container", "cup"]
WEIGHTS = Path(os.environ.get("ANNOTATOR_WEIGHTS", "yoloe-11l-shapes.pt"))
KINDS = ("train", "val", "swipe")


def frames(video: Path, fps: float = FPS):
    """(timestamp ms, RGB image) for the first decoded frame at or after each 1/fps s."""
    cap = cv2.VideoCapture(str(video))
    grabbed, k, ms = 0, 0, 0.0
    while cap.grab():
        grabbed += 1
        ms = cap.get(cv2.CAP_PROP_POS_MSEC)
        if ms * fps >= k * 1000 - 1e-6:  # tolerance: 30 fps frame 10 and the 1/3 s mark are the same instant
            k = math.floor(ms * fps / 1000 + 1e-6) + 1  # one frame can cover several marks after a gap
            _, bgr = cap.retrieve()  # OpenCV applies the iPhone rotation flag
            yield ms, Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    if not grabbed:
        raise ValueError(f"No frames decoded from {video.name}")  # an unreadable file fails the run
    if grabbed > 1 and ms == 0:
        raise ValueError(f"{video.name} has no frame timestamps, so it can't be sampled by time")


def normalize(im: Image.Image) -> Image.Image:
    """Landscape SIZE like the video frames: portrait rotated 90° clockwise, then a plain centre crop.

    The crop ignores the label (the kiosk won't have one), so a tall item in a 4:3 photo can be cut off.
    """
    if im.height > im.width:
        im = im.transpose(Image.Transpose.ROTATE_270)
    return ImageOps.fit(im, SIZE)


assert normalize(Image.new("RGB", (1080, 1920))).size == SIZE


@cache
def model():
    from ultralytics import YOLOE

    if not WEIGHTS.exists():  # once per machine (needs the network); the container image ships the result
        m = YOLOE("yoloe-11l-seg.pt")
        m.set_classes(LABEL_PROMPTS, m.get_text_pe(LABEL_PROMPTS))
        m.save(WEIGHTS)
    return YOLOE(WEIGHTS)


def yoloe_box(jpg: bytes) -> list[float] | None:
    """Normalized xywh of the most confident shape-prompt box in the stored JPEG, or None."""
    im = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
    # Low conf: the top box is the same at any threshold, this only rescues blurry frames
    boxes = model().predict(im, conf=0.005, verbose=False)[0].boxes
    return boxes.xywhn[boxes.conf.argmax()].tolist() if len(boxes) else None


def add_capture(store: Store, video: Path, sku: str, kind: str, capture_id: str | None = None) -> str:
    """What POST /captures and the browser upload do (#14): capture.json first, then the video.

    On S3 the video upload is what triggers the annotator, so capture.json must already exist.
    """
    capture_id = capture_id or uuid.uuid4().hex
    capture = {"capture_id": capture_id, "sku": sku, "kind": kind, "created_at": now()}
    store.put(f"captures/{capture_id}/capture.json", json.dumps(capture).encode())
    store.upload(video, f"raw/{capture_id}/source{video.suffix.lower()}")
    return capture_id


def annotate(store: Store, capture_id: str, detect=None) -> dict:
    """Sample, normalize, and box one capture's video, then write its manifest last (status `ready`)."""
    detect = detect or yoloe_box
    capture = json.loads(store.get(f"captures/{capture_id}/capture.json"))
    [raw] = store.keys(f"raw/{capture_id}/")
    out = f"captures/{capture_id}"
    sampled = labelled = 0
    with tempfile.TemporaryDirectory() as tmp:  # /tmp on Lambda
        video = Path(tmp) / Path(raw).name
        store.download(raw, video)
        for _, im in frames(video):
            name = f"{sampled:04d}"
            sampled += 1
            if capture["kind"] == "swipe":
                continue
            buf = io.BytesIO()
            normalize(im).save(buf, "JPEG", quality=90)
            box = detect(buf.getvalue())
            if box is None:
                continue
            store.put(f"{out}/images/{name}.jpg", buf.getvalue())
            store.put(f"{out}/labels/{name}.txt", ("0 " + " ".join(f"{v:.6f}" for v in box) + "\n").encode())
            labelled += 1
    manifest = {
        "capture_id": capture_id,
        "sku": capture["sku"],
        "kind": capture["kind"],
        "frames": {"sampled": sampled, "labelled": labelled},
        "annotator": os.environ.get("ANNOTATOR_IMAGE", "local"),
        "finished_at": now(),
    }
    store.put(f"{out}/manifest.json", json.dumps(manifest).encode())
    return manifest


def handler(event, context=None):
    """Lambda entry point: annotate the capture of each raw/{capture_id}/source.<ext> in an S3 event."""
    manifests = []
    for record in event["Records"]:
        prefix, capture_id, _ = unquote_plus(record["s3"]["object"]["key"]).split("/")
        if prefix != "raw":
            raise ValueError(f"Not a raw upload: {record['s3']['object']['key']}")
        manifests.append(annotate(Store(f"s3://{record['s3']['bucket']['name']}"), capture_id))
    print(json.dumps(manifests))  # CloudWatch log
    return manifests


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Turn one video and its SKU into an annotated capture.")
    p.add_argument("root", help="local directory or s3://bucket")
    p.add_argument("video", type=Path)
    p.add_argument("sku", help="a sku in backend/app/catalog.json")
    p.add_argument("kind", choices=KINDS, nargs="?", default="train")
    a = p.parse_args()
    store = Store(a.root)
    json.dump(annotate(store, add_capture(store, a.video, a.sku, a.kind)), sys.stdout, indent=2)
