# ML: product detector

Fine-tunes COCO-pretrained YOLO11s, with its backbone frozen, to detect the 4 starter products in single-item checkout frames, and compares it against out-of-the-box models.

**Start here:** [notebooks/yolo11_finetune.ipynb](notebooks/yolo11_finetune.ipynb) walks through the dataset, baselines, training, and results, with outputs saved. The scripts below are the same steps without the narrative.

## Setup

Needs an NVIDIA GPU for training (tested on an RTX 4060, 8 GB). The `ml` dependency group pulls CUDA 12.8 PyTorch wheels on Windows/Linux and default wheels on macOS.

```bash
uv sync --group ml
```

Pretrained weights download to the repo root on first use (ignored by Git).

The data isn't in Git. Get it from the team Google Drive: the raw captures go in `fooddata/` and the prepared dataset in `ml/datasets/food/` (both ignored).

## Dataset (`datasets/food/`, v4)

Built from the raw captures in `fooddata/`, with YOLO-format labels.

- **Train:** frames sampled every 10th frame (3 fps) from each product's ~30 s video. The videos turn the item through every side, including end-on views (can top, cap, lid), which is how many swipes see it.
- **Val / test:** the 15 HEIC photos per product, split 7 / 8. A different capture session from train.
- Every image is 1280x720 landscape: portrait ones are rotated 90°, and the 4:3 photos get a plain centre crop. The crop ignores the box (the kiosk won't know where the item is), so a tall item can be cut off. Orientation and shape can't hint at the class.
- Left out: the short checkout-swipe clips (`evaluate.py` scores them as whole swipes) and the older ~15 s product videos, which scored worse (see Results).

| ID | Class | Train (frames) | Val | Test |
| --- | --- | --- | --- | --- |
| 0 | coca_cola | 93 | 7 | 8 |
| 1 | ketchup | 93 | 7 | 8 |
| 2 | ice_cream | 94 | 7 | 8 |
| 3 | nutella | 93 | 7 | 8 |

Boxes cover the whole item, cap and lid included, never the holding hand. Where the hand hides an end, the box covers the item's estimated full extent; where the item leaves the frame, it stops at the edge. The class comes from the capture folder; the box is YOLOE-11l's most confident detection for generic shape prompts (`can`, `bottle`, `jar`, `tub`, `container`, `cup`). Product-name prompts missed about half the frames. All 433 boxes were checked by eye and 19 were fixed by hand, mostly white caps and lids that blend into the bedsheet. Rebuild from the raw captures (existing labels are kept and follow their image across splits):

```bash
uv run --group ml python ml/scripts/prepare_dataset.py fooddata
```

Limits: everything shows a hand holding the item over the same white bedsheet in the same lighting, and train frames from one video are highly correlated.

## Train

Settings live in [configs/train.yaml](configs/train.yaml):

- **Model:** yolo11s with `freeze: 10`, so the backbone keeps its COCO features and only the neck and head train. Early stop after 20 epochs without a better val mAP.
- **Augmentation:** color, full 360° rotation, scale, and shift. Flips are off because a camera never sees a product mirrored. Mosaic, mixup, cutmix, and copy-paste are off because production frames hold one item.

```bash
uv run --group ml yolo train cfg=ml/configs/train.yaml model=yolo11s.pt name=yolo11s
```

Output goes to `runs/detect/<name>/`. `weights/best.pt` is selected on the val split. About 4–7 minutes on an RTX 4060, depending on when early stopping kicks in.

## Evaluate

```bash
uv run --group ml python ml/scripts/evaluate.py runs/detect/yolo11s/weights/best.pt
```

Baselines: COCO YOLO11 (none of our classes) and YOLOE-11 zero-shot with a text prompt per class. The table splits val+test misses into wrong class, loose box (right class, IoU < 0.5) and no box.

Each fine-tuned checkpoint is then run on every frame of the 20 short swipe clips (5 per product, 1.2–2.8 s, never trained on): per-frame results first, then a vote per clip (each frame's top box adds its confidence to its class). A clip that is a byte-for-byte copy of one in another product folder is skipped and reported.

## Results

Each setup was trained with 3 seeds. Photos = top-1 on the 60 val+test photos; swipes = clips the vote got right (20 clips × 3 seeds = 60).

| Setup | Val / test top-1 (mean) | Lowest seed on photos | Swipes right | Train time |
| --- | --- | --- | --- | --- |
| yolo11m, ~15 s videos | 89% / 88% | 72% | 46 / 60 | 6.9 min |
| yolo11s, ~15 s videos | 93% / 93% | 86% | 50 / 60 | 3.2 min |
| yolo11n, ~15 s videos | 87% / 86% | 78% | 44 / 60 | 2.2 min |
| yolo11s, half the ~30 s frames | 96% / 96% | 93% | 51 / 60 | 3.4 min |
| **yolo11s, ~30 s videos (current)** | **95% / 99%** | **93%** | **53 / 60** | **6.3 min** |

MVP targets:

- Photo top-1 ≥ 90% on every seed: **met** (93% at worst).
- ≥ 90% of swipes right: **2 of 3 seeds**.
- ≤ 5% wrong charges: **not met**. In the notebook's run (seed 0) both missed clips were Coca-Cola voted as ketchup, so 2 of 20 swipes (10%) would charge the wrong item. One of them (IMG_1056) had only 2 boxed frames, so a rescan rule (too few votes or too small a lead → ask for a rescan) would catch it. That rule is the next step.

## Inference

```python
from ultralytics import YOLO
r = YOLO("runs/detect/yolo11s/weights/best.pt").predict("ml/datasets/food/images/test/nutella_IMG_0976.jpg")[0]
print(r.names[int(r.boxes.cls[0])], float(r.boxes.conf[0]))
```
