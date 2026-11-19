"""Compare out-of-the-box and fine-tuned models on single-item frames, then score fine-tuned ones on swipe clips.

Usage: uv run --group ml python ml/scripts/evaluate.py runs/detect/yolo11m/weights/best.pt ...

Top-1 = the highest-confidence detection has the right class and IoU >= 0.5 with the label,
which is what a single-item checkout frame needs. Misses are split into wrong class, loose box
(right class, IoU < 0.5) and no box. Latency is preprocess + inference + postprocess per frame
on the local GPU.
"""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import cv2
import torch
from PIL import Image
from ultralytics import YOLO, YOLOE
from ultralytics.utils import YAML
from ultralytics.utils.metrics import box_iou
from ultralytics.utils.ops import xywhn2xyxy

from annotate import normalize
from dataset import CATALOG
from import_fooddata import kind

# Capture folder -> class name in the hand-checked v4 dataset; same order as the catalog's class IDs
CLASSES = {
    "coca cola": "coca_cola",
    "ketchup": "ketchup",
    "ice cream": "ice_cream",
    "nutella": "nutella",
}

DATA = Path(__file__).resolve().parents[1] / "datasets" / "food"
RAW = Path(__file__).resolve().parents[2] / "fooddata"
NAMES = list(YAML.load(DATA / "data.yaml")["names"].values())
# YOLOE text prompts, same order as NAMES
PROMPTS = [
    "red Coca-Cola can",
    "Heinz ketchup bottle",
    "Ben & Jerry's ice cream tub",
    "Nutella jar",
]
# Pipeline-trained models name their classes by SKU (ml/scripts/dataset.py)
SKUS = {p["sku"]: p["class_id"] for p in json.loads(CATALOG.read_text(encoding="utf-8"))["products"]}
LOOKUP = {n: i for i, n in enumerate(NAMES)} | {p: i for i, p in enumerate(PROMPTS)} | SKUS
SPLITS = ("val", "test")
ERRORS = ("wrong class", "loose box", "no box")


def video_frames(f: Path):
    """Every frame of a video, as RGB images."""
    cap = cv2.VideoCapture(str(f))
    while cap.grab():
        _, bgr = cap.retrieve()  # OpenCV applies the iPhone rotation flag
        yield Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def ours(model) -> dict[int, int]:
    """Model class id -> our class id, for the classes it shares with us."""
    return {k: LOOKUP[n] for k, n in model.names.items() if n in LOOKUP}


def judge(model, split: str, img: Path):
    """(outcome, result) for one labelled image; outcome is "ok" or one of ERRORS."""
    r = model.predict(img, conf=0.25, verbose=False)[0]
    if not len(r.boxes):
        return "no box", r
    c, *xywhn = map(float, (DATA / "labels" / split / f"{img.stem}.txt").read_text().split())
    i = int(r.boxes.conf.argmax())
    if ours(model).get(int(r.boxes.cls[i])) != int(c):
        return "wrong class", r
    h, w = r.orig_shape
    gt = xywhn2xyxy(torch.tensor([xywhn]), w, h).to(r.boxes.xyxy.device)
    return ("ok" if box_iou(r.boxes.xyxy[i : i + 1], gt).item() >= 0.5 else "loose box"), r


def top1(model, split: str) -> tuple[float, float, Counter]:
    """Top-1 accuracy, mean ms/frame and the outcome counts."""
    imgs = sorted((DATA / "images" / split).glob("*.jpg"))
    outcomes, ms = Counter(), 0.0
    for img in imgs:
        outcome, r = judge(model, split, img)
        outcomes[outcome] += 1
        ms += sum(r.speed.values())
    return outcomes["ok"] / len(imgs), ms / len(imgs), outcomes


def row(label: str, model, finetuned: bool) -> str:
    model.predict(next((DATA / "images" / "val").glob("*.jpg")), verbose=False)  # warmup
    cells, errors = [label], Counter()
    for split in SPLITS:
        acc, ms, outcomes = top1(model, split)
        cells.append(f"{acc:.0%}")
        errors.update(outcomes)
    cells.append(", ".join(f"{e} {errors[e]}" for e in ERRORS))
    if finetuned:
        box = model.val(data=str(DATA / "data.yaml"), split="test", verbose=False, plots=False).box
        cells += [f"{box.map50:.3f}", f"{box.map:.3f}"]
    else:
        cells += ["-", "-"]
    return "| " + " | ".join(cells + [f"{ms:.1f}"]) + " |"


def compare(finetuned: list[str]) -> str:
    """Markdown table: COCO and YOLOE baselines (m, l), then each fine-tuned checkpoint."""
    rows = [
        "| Model | Val top-1 | Test top-1 | Val+test errors | Test mAP50 | Test mAP50-95 | ms/frame |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for size in ("m", "l"):
        rows.append(row(f"yolo11{size} COCO (no matching classes)", YOLO(f"yolo11{size}.pt"), False))
        yoloe = YOLOE(f"yoloe-11{size}-seg.pt")
        yoloe.set_classes(PROMPTS, yoloe.get_text_pe(PROMPTS))
        rows.append(row(f"yoloe-11{size} zero-shot", yoloe, False))
    for w in finetuned:
        rows.append(row(f"{Path(w).parents[1].name} fine-tuned", YOLO(w), True))
    return "\n".join(rows)


def swipes(model) -> str:
    """Markdown table for the short checkout-swipe clips, every frame, prepared like the dataset.

    Per frame first: the top box's class (no box is expected while the item is entering or leaving).
    Then the vote: each frame's top box adds its confidence to its class, the clip goes to the highest total.
    """
    to_ours = ours(model)
    rows = ["| Clip | Item | Frames | No box | Right | Wrong | Vote |", "| --- | --- | --- | --- | --- | --- | --- |"]
    total, seen, notes = Counter(), {}, []
    for folder, name in CLASSES.items():
        for f in sorted((RAW / folder).glob("*.MOV")):
            if kind(f) != "swipe":
                continue
            first = seen.setdefault(hashlib.md5(f.read_bytes()).hexdigest(), f)
            if first != f:  # shortcut: catches a clip copied into a second product folder; drop once fooddata is clean
                notes.append(f"Skipped {folder}/{f.name}: same file as {first.parent.name}/{first.name}.")
                continue
            frames = no_box = 0
            wrong, votes = Counter(), Counter()
            for im in video_frames(f):
                frames += 1
                b = model.predict(normalize(im), conf=0.25, verbose=False)[0].boxes
                if not len(b):
                    no_box += 1
                    continue
                i = int(b.conf.argmax())
                pred = NAMES[to_ours[int(b.cls[i])]]
                votes[pred] += float(b.conf[i])
                wrong[pred] += pred != name
            right = frames - no_box - wrong.total()
            vote = votes.most_common(1)[0][0] if votes else "nothing"
            mistakes = ", ".join(f"{k} {v}" for k, v in wrong.most_common() if v)
            rows.append(
                f"| {folder}/{f.name} | {name} | {frames} | {no_box} | {right} | {wrong.total()}"
                f"{f' ({mistakes})' if mistakes else ''} | {vote}{'' if vote == name else ' (wrong)'} |"
            )
            total.update(frames=frames, boxed=frames - no_box, right=right, clips=1, voted=vote == name)
    boxed = total["boxed"] or 1
    return "\n".join(
        rows
        + [
            "",
            f"Per frame: {total['right']} of {total['boxed']} frames with a box are right ({total['right'] / boxed:.0%}); "
            f"{total['frames'] - total['boxed']} of {total['frames']} frames have no box.",
            f"Vote: {total['voted']} of {total['clips']} clips right.",
            *notes,
        ]
    )


if __name__ == "__main__":
    print(compare(sys.argv[1:]))
    for w in sys.argv[1:]:
        print(f"\n{Path(w).parents[1].name} on swipe clips:\n\n{swipes(YOLO(w))}")
