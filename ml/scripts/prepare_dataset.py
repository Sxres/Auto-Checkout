"""Build the food dataset from raw captures and auto-label boxes.

Usage: uv run --group ml python ml/scripts/prepare_dataset.py fooddata

Train = frames sampled from each product's ~30 s video (with end-on views). Val/test = the HEIC photos,
split in half, so evaluation is on a different capture session than training.
Short checkout-swipe clips are left out (evaluate.py scores them as whole swipes), and so are the
older ~15 s product videos: training on them alone scored worse on swipes than the 30 s videos.
Every image ends up 1280x720 landscape like the video frames (see normalize), so
orientation and shape can't hint at the class.

Class comes from the capture folder; YOLOE with generic object prompts only supplies the
box: its most confident detection, which covers the item and not the hand holding it.
Existing labels are never overwritten and follow their image if it changes split, so
hand fixes survive reruns.
"""

import random
import sys
from pathlib import Path

import cv2
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
from ultralytics import YOLOE

register_heif_opener()

# Capture folder -> class name. Order defines class IDs.
CLASSES = {
    "coca cola": "coca_cola",
    "ketchup": "ketchup",
    "ice cream": "ice_cream",
    "nutella": "nutella",
}
OUT = Path(__file__).resolve().parents[1] / "datasets" / "food"
FRAME_STEP = 10  # 3 fps from 30 fps video; closer frames are near-duplicates
MIN_PRODUCT_VIDEO_S = 8  # longer clips are product videos, shorter ones checkout swipes
MIN_TRAIN_VIDEO_S = 20  # train on the ~30 s product videos only, not the older ~15 s ones
SIZE = (1280, 720)  # every image ends up landscape at the video frame size
# Generic shapes, not product names: product-name prompts miss many frames, and the class comes from the folder
LABEL_PROMPTS = ["can", "bottle", "jar", "tub", "container", "cup"]


def photo_split(i: int, n: int) -> str:
    return "val" if i < n // 2 else "test"


assert [photo_split(i, 15) for i in range(15)].count("test") == 8


def seconds(f: Path) -> float:
    cap = cv2.VideoCapture(str(f))
    return cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)


def is_swipe(f: Path) -> bool:
    return seconds(f) < MIN_PRODUCT_VIDEO_S


def video_frames(f: Path, step: int = FRAME_STEP):
    cap = cv2.VideoCapture(str(f))
    i = 0
    while cap.grab():
        if i % step == 0:
            _, bgr = cap.retrieve()  # OpenCV applies the iPhone rotation flag
            yield f"{f.stem}_f{i:04d}", Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        i += 1


def add(stem, load, split, cls_id, model, missing):
    img_path = OUT / "images" / split / f"{stem}.jpg"
    lbl_path = OUT / "labels" / split / f"{stem}.txt"
    img_path.parent.mkdir(parents=True, exist_ok=True)
    lbl_path.parent.mkdir(parents=True, exist_ok=True)
    for kind, dst in (("images", img_path), ("labels", lbl_path)):
        old = next((p for p in OUT.glob(f"{kind}/*/{dst.name}") if p != dst), None)
        if old and not dst.exists():
            old.rename(dst)
    if not img_path.exists():
        normalize(load()).save(img_path, quality=90)
    if not lbl_path.exists():
        # Low conf: the top box is the same at any threshold, this only rescues ~30 blurry frames (all checked by eye)
        boxes = model.predict(img_path, conf=0.005, verbose=False)[0].boxes
        if not len(boxes):
            missing.append(img_path.name)
            return
        x, y, w, h = boxes.xywhn[boxes.conf.argmax()].tolist()
        lbl_path.write_text(f"{cls_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")


def normalize(im: Image.Image) -> Image.Image:
    """Landscape SIZE like the video frames: portrait rotated 90° clockwise, then a plain centre crop.

    The crop ignores the label (the kiosk won't have one), so a tall item in a 4:3 photo can be cut off.
    """
    if im.height > im.width:
        im = im.transpose(Image.Transpose.ROTATE_270)
    return ImageOps.fit(im, SIZE)


assert normalize(Image.new("RGB", (3024, 4032))).size == SIZE


def main(src: Path) -> None:
    rng = random.Random(0)
    model = YOLOE("yoloe-11l-seg.pt")
    model.set_classes(LABEL_PROMPTS, model.get_text_pe(LABEL_PROMPTS))
    missing = []
    for cls_id, (folder, name) in enumerate(CLASSES.items()):
        photos = sorted((src / folder).glob("*.HEIC"))
        rng.shuffle(photos)
        for i, f in enumerate(photos):
            load = lambda f=f: ImageOps.exif_transpose(Image.open(f)).convert("RGB")
            add(f"{name}_{f.stem}", load, photo_split(i, len(photos)), cls_id, model, missing)
        for video in sorted((src / folder).glob("*.MOV")):
            if seconds(video) < MIN_TRAIN_VIDEO_S:  # swipe clips and the older ~15 s videos
                continue
            for stem, im in video_frames(video):
                add(f"{name}_{stem}", lambda im=im: im, "train", cls_id, model, missing)

    names = "\n".join(f"  {i}: {n}" for i, n in enumerate(CLASSES.values()))
    (OUT / "data.yaml").write_text(
        f"# Generated by ml/scripts/prepare_dataset.py\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n{names}\n"
    )
    for split in ("train", "val", "test"):
        print(split, len(list((OUT / "images" / split).glob("*.jpg"))), "images")
    if missing:
        print("No box found, label by hand:", *missing, sep="\n  ")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
