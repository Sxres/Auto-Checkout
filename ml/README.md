# ML: product detector

Fine-tunes COCO-pretrained YOLO11s, with its backbone frozen, to detect the 4 starter products in single-item checkout frames, and compares it against out-of-the-box models. New products are onboarded by the [annotation pipeline](#annotation-pipeline), which turns a product video into a labelled dataset with no hand labelling.

**Start here:** [notebooks/yolo11_finetune.ipynb](notebooks/yolo11_finetune.ipynb) walks through the dataset, baselines, training, and results, with outputs saved. The scripts below are the same steps without the narrative.

## Setup

Needs an NVIDIA GPU for training (tested on an RTX 4060, 8 GB). The `ml` dependency group pulls CUDA 12.8 PyTorch wheels on Windows/Linux and default wheels on macOS.

```bash
uv sync --group ml
```

Pretrained weights download to the repo root on first use (ignored by Git).

The data isn't in Git. Get it from the team Google Drive: the raw captures go in `fooddata/` and the prepared dataset in `ml/datasets/food/` (both ignored).

## Annotation pipeline

Turns an uploaded product video into a train-ready, annotated YOLO dataset with no hand labelling (#12). The capture UI (#18), the capture API, and the AWS deploy (#14) are implemented in `backend/app/captures.py` and `infra/template.yaml`; the retrain job is #16.

```text
manager console ── POST /captures ──▶ API (Lambda) ── presigned POST ──▶ browser uploads to S3 raw/
S3 raw/ ── ObjectCreated ──▶ annotator (Lambda container, CPU) ──▶ S3 captures/{id}/
retrain job (#16) ──▶ dataset build ──▶ datasets/{version}/manifest.json ──▶ materialize ──▶ yolo train
```

One S3 bucket holds everything, and a capture's status comes from which objects exist: no database, no queue. Every command below takes a `ROOT` that is either a local directory (`ml/data/pipeline/` is ignored by Git) or `s3://bucket`, with the same layout.

### S3 layout

```text
catalog.json                           the product catalog (#20), seeded from backend/app/catalog.json
raw/{capture_id}/source.<ext>          uploaded video
captures/{capture_id}/capture.json     written by the API
captures/{capture_id}/images/*.jpg     sampled frames, 1280x720 (train and val only)
captures/{capture_id}/labels/*.txt     YOLO boxes with a placeholder class 0 (train and val only)
captures/{capture_id}/manifest.json    written last by the annotator
datasets/{version}/manifest.json       written by the dataset build
models/{version}/                      written by the retrain job (#16)
```

`capture_id` is a uuid4 hex, `version` a UTC timestamp like `20261118T120000Z`. Frames are named by their sample number (`0000.jpg`, `0001.jpg`, ...), so a gap means that frame had no box.

```text
capture.json    {"capture_id", "sku": "COKE-330", "kind": "train", "created_at"}
manifest.json   {"capture_id", "sku", "kind", "frames": {"sampled": 93, "labelled": 90}, "annotator": "<image tag>", "finished_at"}
datasets/{version}/manifest.json
                {"version", "classes": {"0": "COKE-330", ...}, "captures": {"train": [ids], "val": [ids], "swipe": [ids]},
                 "counts": {"train": {"COKE-330": 93, ...}, "val": {...}, "swipe": {"COKE-330": 5, ...}}}
```

`counts` holds labelled frames for train and val, clips for swipe. A swipe manifest has `"labelled": 0`; its `sampled` is the number of 3 fps frames the clip decoded to.

API contract (`backend/app/captures.py` #14, `backend/app/products.py` #20):

```text
GET    /products        → every product with derived status and photos (from catalog.json)
POST   /products        {name, price, category, art} → 201 product (assigns class_id and SKU PRD-{id:03d})
PATCH  /products/{sku}  {name?, price?, category?, art?, retired?} → 200 product
POST   /captures        {sku, kind} → 201 {capture_id, upload: {url, fields, expires_in}}   (sku must be live in the catalog)
GET    /captures/{id}   → {capture_id, sku, kind, status, frames}
GET    /captures?sku=   → that product's captures
```

`catalog.json` at the store root is the source of truth (#20); the repo `backend/app/catalog.json` is only the
local-dev seed. Seed it once with `uv run python ml/scripts/seed_catalog.py ROOT` (writes only if absent).
Product `status` is derived: `Retired` if retired, else `Ready` with a ready `train` capture, else `Needs images`;
`photos` is the labelled frames of its ready `train` and `val` captures. `POST /captures` refuses unknown and retired SKUs.

`kind` is `train`, `val`, or `swipe`. `status` is `awaiting_upload` (no video yet), `processing` (video, no manifest), or `ready` (manifest written). A failed run stays `processing`; its error is in the logs.

### Footage

All onboarding footage is recorded at the kiosk, with its camera and surface, in one session of about 2 minutes per product:

| Kind | What staff record | Used for |
| --- | --- | --- |
| `train` | One ~30 s video turning the item through every side, top and bottom included | Training |
| `val` | A second ~15 s take with the other hand | Picking the best checkpoint and seed |
| `swipe` | 5 swipes of ~3 s, as a customer would | Retrain gate, scored per clip, no boxes |

Same-session footage shares the hand, light, and surface with training, so its scores are optimistic. The independent test set is production swipes labelled by the confirmed basket, which needs the checkout flow and its own issue.

### Commands

```bash
# One video and its SKU -> frames, YOLO labels, and a manifest (prints the manifest)
uv run --group ml python ml/scripts/annotate.py ml/data/pipeline video.webm COKE-330 train

# The 4 starter products in fooddata/ as captures. Locally this also annotates them;
# on S3 the upload triggers the annotator, so run it without the ml group.
uv run --group ml python ml/scripts/import_fooddata.py fooddata ml/data/pipeline

# Every ready capture -> datasets/{version}/manifest.json (prints it; copies no images)
uv run python ml/scripts/dataset.py build ml/data/pipeline

# A dataset -> a local YOLO folder, then train as usual
uv run python ml/scripts/dataset.py materialize ml/data/pipeline <version> ml/datasets/auto
uv run --group ml yolo train cfg=ml/configs/train.yaml model=yolo11s.pt data=ml/datasets/auto/data.yaml name=auto
```

`materialize` writes `data.yaml`, `images/{train,val}/`, `labels/{train,val}/` with the catalog's class IDs, and `swipes/{sku}/{capture_id}.<ext>` (the raw swipe videos, for the gate in #16). It refuses an existing folder, so two versions never mix. S3 roots use the default AWS credentials and region.

The first local annotation saves `yoloe-11l-shapes.pt` in the repo root (YOLOE-11l with the prompts set; downloads once). The import derives each capture ID from the file's MD5, so a clip copied into two product folders is imported once and a rerun skips what is already there.

### Annotation rules

- The class comes from the capture's SKU, never from the model. Stored labels hold only the box (class 0). The dataset build writes the `class_id` values from `backend/app/catalog.json` into the labels and into `data.yaml`, whose `names` are the SKUs for every ID up to the highest, including products with no captures yet. A new product gets the next unused `class_id`; IDs are never reused or reordered.
- The box is YOLOE-11l's most confident detection (`conf=0.005`) for the shape prompts `can`, `bottle`, `jar`, `tub`, `container`, `cup`, saved in the weights.
- Frames are sampled by decoded timestamp at 3 fps (the first frame at or after each 1/3 s), never from the header, so browser recordings work. Each is normalized like the checkout frames: portrait rotated 90° clockwise, then a centre crop to 1280x720.
- No frame is dropped for a loose box: loose boxes cluster on single views (white caps and lids), so dropping them would remove those views. A sampled frame with no box is skipped.
- Swipe clips are not annotated: the annotator writes only their manifest, and #16 scores the video itself frame by frame, as `evaluate.py` does.
- No usability checks (the team records the footage itself). An unreadable file fails the run.
- Splits follow captures: `train` captures go to train, `val` to val, `swipe` to the swipe clips.

### Container

[`infra/annotator.Dockerfile`](../infra/annotator.Dockerfile) builds the annotator as a Lambda container image: the Python 3.12 Lambda base image, CPU PyTorch, Ultralytics, and headless OpenCV. A build stage saves YOLOE-11l with the shape prompts set (71 MB) and only that file goes into the image, so it ships no text encoder and downloads nothing at run time (`YOLO_OFFLINE=1`). The handler is `annotate.handler`, for S3 `ObjectCreated` events on `raw/`. Weights are never committed.

```bash
docker build -f infra/annotator.Dockerfile -t annotator:local .
```

To run it locally with no AWS account, imitate S3 with a moto server and invoke the container once through the base image's runtime interface emulator (Git Bash, repo root):

```bash
docker network create annet
docker run -d --name moto --network annet -p 5000:5000 motoserver/moto:5.0.28
docker run -d --name annotator --network annet --memory=10g --cpus=6 -p 9000:8080 \
  -e AWS_ENDPOINT_URL=http://moto:5000 -e AWS_ACCESS_KEY_ID=x -e AWS_SECRET_ACCESS_KEY=x -e AWS_REGION=us-east-2 \
  annotator:local

# Create the bucket and a capture, as the API and the browser upload will (#14); prints the capture ID
export AWS_ENDPOINT_URL=http://localhost:5000 AWS_ACCESS_KEY_ID=x AWS_SECRET_ACCESS_KEY=x AWS_REGION=us-east-2
uv run python -c "
import sys, boto3; sys.path.insert(0, 'ml/scripts')
from pathlib import Path
from annotate import Store, add_capture
boto3.client('s3').create_bucket(Bucket='captures', CreateBucketConfiguration={'LocationConstraint': 'us-east-2'})
print(add_capture(Store('s3://captures'), Path('fooddata/coca cola/IMG_1103.MOV'), 'COKE-330', 'train'))"

# The S3 event Lambda would get; prints the manifest
curl -XPOST http://localhost:9000/2015-03-31/functions/function/invocations \
  -d '{"Records":[{"s3":{"bucket":{"name":"captures"},"object":{"key":"raw/<capture_id>/source.mov"}}}]}'

docker rm -f annotator moto && docker network rm annet
```

### Limits and catalog changes

- Products are cans, bottles, jars, and tubs: the shapes the prompts name.
- The kiosk surface is white, so mostly white products are out of scope: the labeller may find no box.
- Background masking was left out. YOLOE's masks are cut to its box, so a box that misses a cap would delete the cap from the image, and checkout frames would need the same masking.

When the catalog gets a new kind of product (for example produce):

1. Add it to `backend/app/catalog.json` with the next unused `class_id`.
2. If no prompt in `LABEL_PROMPTS` (`ml/scripts/annotate.py`) names its shape, add one. A product name alone does not work (52% of boxes right, see Results); name + shapes does, but needs YOLOE's 600 MB text encoder at run time.
3. Record one ~30 s turn video of it, annotate it locally, and check every box by eye, for example with `ultralytics.data.utils.visualize_image_annotations(jpg, txt, {0: "item"})`.
4. Rebuild and redeploy the container: the prompts are saved into the weights at build time.

### Pipeline results

**Auto-label agreement (2026-11-17, v4).** Fresh auto-labels against the 433 hand-checked boxes: 96.3% agree at IoU ≥ 0.9, 1.8% fall below 0.75, 0.9% below 0.5, and 3 frames get no box. The 16 disagreements are 7 ketchup, 7 nutella, 1 coca_cola, and 1 ice_cream. Detection confidence does not separate them: a threshold of 0.3 flags 30% of frames to catch 7 of the 8 boxes below IoU 0.75.

**The pipeline against v4 (2026-11-18).** `import_fooddata.py` on `fooddata/` gives 28 captures (4 train, 4 val, 20 swipe) in 2 min 45 s on the RTX 4060. Timestamp sampling picks the same frames as v4's every 10th frame. Against v4's hand-checked train labels, the 369 boxed frames agree at IoU ≥ 0.9 for 94.6%, 7 fall below 0.75, none below 0.5 (median 0.992), and 4 of 373 frames get no box. The dataset has 369 train and 199 val frames.

**Raw auto-labels vs hand-checked labels (2026-11-18).** yolo11s, same config, 8 seeds each, judged on the hand-checked photos and the swipe clips:

| Train labels | Photo errors of 60 | Swipes right of 20 | Swipe frames right | Ketchup swipe frames right |
| --- | --- | --- | --- | --- |
| Hand-checked v4 | 2.0 ± 1.9 | 16.5 ± 1.9 | 81.6% ± 9.4 | 68.6% ± 16.2 |
| Raw auto-labels | 2.3 ± 1.2 | 16.5 ± 1.5 | 85.9% ± 6.2 | 59.1% ± 12.4 |
| Mann-Whitney p | 0.47 | 0.96 | 0.44 | 0.23 |

No measurable difference, so the raw labels are used with no hand check. Ketchup (white cap) trails, but within seed noise, and its swipes are mostly lost to nutella with either set of labels. With 3 seeds the gap looked real (4 swipe clips); 8 seeds settled it. Seed variance matters more than labels: only 4 of 8 seeds in each arm reach 18 of 20 swipes, so the retrain gate (#16) must judge every new model on held-out swipes.

**The pipeline dataset vs v4 (2026-11-19, #12 acceptance).** yolo11s trained with `configs/train.yaml` on `datasets/auto_20261119T033623Z`, the build of the `fooddata/` import with no hand check, for 8 seeds (52–106 epochs each, 56 min in total on the RTX 4060). It is compared against the 8 v4 checkpoints from the table above. Both arms were re-scored with this branch's `evaluate.py` and environment, which is why the v4 row differs from that table:

| Train data | Photo errors of 60 | Swipes right of 20 | Swipe frames right | Ketchup swipe frames right |
| --- | --- | --- | --- | --- |
| Hand-checked v4 | 3.0 ± 2.8 | 14.9 ± 2.1 | 73.2% ± 10.6 | 71.5% ± 15.1 |
| Pipeline dataset | 3.0 ± 2.3 | 15.2 ± 1.8 | 81.0% ± 7.0 | 61.0% ± 20.0 |
| Mann-Whitney p | 0.90 | 0.57 | 0.10 | 0.49 |

No measurable difference, so the pipeline dataset meets the acceptance bar. Its higher swipe-frame rate comes from boxing fewer frames, not from getting more right: per seed it boxes 328 swipe frames to v4's 385 and gets 266 of them right to v4's 279. Ketchup still trails within noise. The two arms pick `best.pt` differently: the pipeline dataset validates on 199 frames from the val videos, while v4 validates on its 28 val photos.

**Which prompt finds the box (2026-11-18).** Against the 433 hand-checked boxes:

| Prompts | IoU ≥ 0.9 | Below 0.5 | No box |
| --- | --- | --- | --- |
| Shapes (current) | 96.3% | 4 | 3 |
| Product name alone ("ketchup") | 52.0% | 170 | 108 |
| Described name ("Heinz ketchup bottle") | 91.5% | 14 | 11 |
| Product name + shapes | 96.5% | 2 | 1 |
| "product" / "object" | 85.9% / 88.9% | 37 / 37 | 16 / 34 |
| "non-hand item" | 71.6% | 103 | 0 |

A product name describes the brand, not the thing in the hand; the shape word does the work. "non-hand item" boxes the hand, because the text encoder ignores the negation. Name + shapes ties with shapes but needs the 600 MB text encoder at run time. YOLOE-11l saved after `set_classes` (71 MB) gives identical boxes when reloaded, so the image needs no CLIP model.

**Left out.** Borrowing a box from neighbouring sampled frames: median IoU 0.79 against the hand-checked box at 3 fps. Swapping in the nearest frame when a sampled frame has no box: it rescued 1 frame in 93.

**Browser recordings (2026-11-18).** A 31 s product video fed to headless Chrome as a 1280x720 fake camera and recorded with MediaRecorder as VP8 WebM (Chrome's default), VP9 WebM, H.264 Matroska, and VP9 MP4 decodes with increasing timestamps; 3 fps sampling gives 88 frames, 88 with a box (87 for H.264). The WebM headers have no duration, a frame count of −9×10¹⁸, and 1000 fps, which is why sampling uses decoded timestamps. The kiosk's `getUserMedia` call asks for no resolution, so the capture UI must request 1280x720 (#14).

**CPU speed.** 247 ms per frame on 6 desktop threads, about 25 s for the ~95 frames of one video.

**Container timing, local Docker.** Run with Lambda's CPU and memory limits imitated by Docker; Lambda's own CPUs may be slower, so the real numbers come from the first deploy (#14).

| Date | Limits | Image | 31 s iPhone HEVC video (93 frames) | 31 s Chrome VP8 WebM (88 frames) | Peak memory |
| --- | --- | --- | --- | --- | --- |
| 2026-11-18 (prototype) | 10 GB, 6 vCPU | 2.76 GB | 59–68 s | 47–49 s | 0.9 GB |
| 2026-11-18 (prototype) | 3 GB, ~1.8 vCPU (if the account is capped) | 2.76 GB | 98 s | 67 s | 0.8 GB |
| 2026-11-18 (`infra/annotator.Dockerfile`) | 10 GB, 6 vCPU | 2.79 GB | 43–68 s, 93 sampled / 90 labelled | – | 0.85 GB |

Model load takes about 2 s, and starting a container and loading the model about 6 s. The container's boxes match the GPU run on the same video: the same 90 frames, every box at IoU ≥ 0.999. A 6-frame swipe clip takes 1 s and writes only its manifest. All of this is far inside Lambda's 15 minute limit, at about US$0.01 per video at 10 GB. A GPU would need a SageMaker job or an EC2 instance that takes minutes to start or costs money while idle, to save about a minute per video, so the annotator stays on CPU Lambda unless a video needs more than 15 minutes, more than 10 GB, or a GPU.

### First deploy measurements (#14)

To be recorded on the first real Lambda deploy (the local Docker numbers above imitate Lambda's
limits; Lambda's own CPUs may be slower). Measure the annotator's cold start (first invocation
after a deploy and after being idle), time per 30 s video, and peak memory from CloudWatch Logs
and the invocation reports. If the account caps Lambda memory at 3 GB, run at 3 GB (about
1.6 min per video) and note it here. This account (405145778116) caps Lambda at 3008 MB, so the
annotator runs at 3008 MB.

| Date | Memory | Cold start (after deploy / after idle) | Time per 30 s video | Peak memory |
| --- | --- | --- | --- | --- |
| _pending first deploy_ | | | | |

## Dataset v4 (`datasets/food/`, hand-checked)

The reference set every model is judged on: its val and test photos are hand-checked, from a different capture session than any training video. It was built from the raw captures in `fooddata/` by `prepare_dataset.py`, which #12 turned into the annotator (the old script is in Git history), and is no longer rebuilt.

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

Boxes cover the whole item, cap and lid included, never the holding hand. Where the hand hides an end, the box covers the item's estimated full extent; where the item leaves the frame, it stops at the edge. The class comes from the capture folder; the box is YOLOE-11l's most confident detection for generic shape prompts (`can`, `bottle`, `jar`, `tub`, `container`, `cup`). Product-name prompts missed about half the frames. All 433 boxes were checked by eye and 19 were fixed by hand, mostly white caps and lids that blend into the bedsheet.

Limits: everything shows a hand holding the item over the same white bedsheet in the same lighting, and train frames from one video are highly correlated.

## Train

Settings live in [configs/train.yaml](configs/train.yaml):

- **Model:** yolo11s with `freeze: 10`, so the backbone keeps its COCO features and only the neck and head train. Early stop after 20 epochs without a better val mAP.
- **Augmentation:** color, full 360° rotation, scale, and shift. Flips are off because a camera never sees a product mirrored. Mosaic, mixup, cutmix, and copy-paste are off because production frames hold one item.

```bash
uv run --group ml yolo train cfg=ml/configs/train.yaml model=yolo11s.pt name=yolo11s
```

Output goes to `runs/detect/<name>/`. `weights/best.pt` is selected on the val split. About 4–7 minutes on an RTX 4060, depending on when early stopping kicks in. The config trains on v4; add `data=<folder>/data.yaml` for a dataset from `dataset.py materialize`.

## Evaluate

```bash
uv run --group ml python ml/scripts/evaluate.py runs/detect/yolo11s/weights/best.pt
```

Baselines: COCO YOLO11 (none of our classes) and YOLOE-11 zero-shot with a text prompt per class. The table splits val+test misses into wrong class, loose box (right class, IoU < 0.5) and no box. Models trained on a pipeline dataset name their classes by SKU; the script maps them through the catalog.

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
