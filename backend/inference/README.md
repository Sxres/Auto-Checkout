# Inference and recognition contract

Model loading and prediction live in `backend/app/inference.py`; the catalog, pricing, and
response shaping live in `backend/app/main.py`. The trained detector is **YOLO11s** (`imgsz=640`),
fine-tuned in #6 on the four starter products.

`ultralytics` is imported lazily inside `YoloPredictor`, so the API and its tests run without the
`ml` dependency group. When the weights or the ML runtime are missing, `/recognize` returns `503`
rather than failing at import time.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `AVC_MODEL_PATH` | `ml/model/best.pt` | Checkpoint to load, once, on first request |
| `AVC_CONF_THRESHOLD` | `0.25` | Minimum detection confidence |
| `AVC_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed kiosk origins |

The checkpoint is git-ignored (`*.pt`). Get `best.pt` from the team Google Drive and place it at
`ml/model/best.pt`, or point `AVC_MODEL_PATH` elsewhere. Install the runtime with
`uv sync --group ml`.

The checkpoint is loaded and warmed up with one dummy inference during application startup, so
the first customer scan is fast. Loading plus CUDA warmup takes roughly 50s on an RTX 4060;
without it the first scan would block for that long. If the weights or runtime are missing,
startup logs a warning and `/recognize` returns `503` — the service still boots and `/health`
still passes.

## Catalog

`backend/app/catalog.json` is the single source of truth mapping model class IDs to SKU, name,
price, and UI art. Class IDs match `ml/scripts/prepare_dataset.py` and the checkpoint's own
`names` dict — do not reorder them.

| Class ID | Class | SKU | Name | Price (USD) |
| --- | --- | --- | --- | --- |
| 0 | `coca_cola` | `COKE-330` | Coca-Cola 330ml | 1.99 |
| 1 | `ketchup` | `HEINZ-570` | Heinz Ketchup 570g | 3.49 |
| 2 | `ice_cream` | `BJ-473` | Ben & Jerry's 473ml | 5.99 |
| 3 | `nutella` | `NUT-750` | Nutella 750g | 6.49 |

Prices are `per_item` in USD. The frontend never duplicates this mapping; it reads names, prices,
and art from API responses.

## `POST /recognize`

`multipart/form-data` with a single field **`file`** containing a JPEG or PNG, max 10 MB.

### Units

- **`confidence`** is a probability in **0–1**.
- **`x`, `y`, `w`, `h`** are **percentages (0–100) of the uploaded image**, origin top-left.
  `x`/`y` are the box's top-left corner; `w`/`h` its extent. They are relative to the image you
  uploaded, not to any display area.
- **`image`** echoes the decoded pixel dimensions, so a client can convert to absolute pixels.

The kiosk uploads the whole camera frame and sizes its preview card to that frame's aspect ratio,
so the frame fills the card with no letterboxing, cropping, or distortion. These percentages
therefore map directly onto the card.

### Recognized product — `200`

```json
{
  "items": [
    { "key": "COKE-330", "sku": "COKE-330", "name": "Coca-Cola 330ml", "price": 1.99, "art": "can" }
  ],
  "detections": [
    { "label": "Coca-Cola 330ml", "sku": "COKE-330", "class_id": 0, "confidence": 0.93,
      "x": 12.5, "y": 20.0, "w": 18.2, "h": 30.1 }
  ],
  "image": { "width": 1280, "height": 720 }
}
```

`detections` and `items` are ordered by descending confidence. `items` is deduplicated by SKU.

### No detections — `200`

A valid image containing nothing recognizable is a success, not an error:

```json
{ "items": [], "detections": [], "image": { "width": 1280, "height": 720 } }
```

### Errors

All errors use `{"detail": {"code": "...", "message": "..."}}`.

| Status | `code` | Cause |
| --- | --- | --- |
| 400 | `invalid_image` | Bytes could not be decoded as an image |
| 413 | `image_too_large` | Upload exceeds 10 MB |
| 415 | `unsupported_media_type` | `Content-Type` is not `image/*` |
| 503 | `model_unavailable` | Weights missing/unreadable, or `ml` group not installed |

```json
{ "detail": { "code": "model_unavailable", "message": "Model weights not found at ml/model/best.pt. Set AVC_MODEL_PATH to a valid checkpoint." } }
```

## Swipe recognition

The kiosk recognizes continuously — there is no scan button. While the camera is live and no modal
is open it captures a frame every 80ms. Capture is not blocked on the response, so a new frame is
grabbed while a request is in flight; `observe()` drops a frame if the previous one has not
returned. Effective rate is ~11 requests/s against a warm model.

Frames are capped at **640px** on the long edge. YOLO letterboxes to `imgsz=640` regardless, so a
larger upload is discarded server-side while costing encode time, bandwidth, and decode. Measured
on the four held-out products, 640 vs 1280 gave the same SKU every time, confidence within ±0.01,
and boxes within ~2 percentage points, at roughly a third of the bytes (~25 KB vs ~100 KB).

Charging follows the swipe voting already validated in `ml/scripts/evaluate.py`: each frame's
top detection adds its confidence to that SKU, and once a SKU's total reaches **1.5** it is added
to the basket. Scanning the same SKU again increments its quantity. Measured time from an item
entering view to being charged: ~200ms.

After an item is charged, further detections are ignored until the frame has been empty for
**450ms** — i.e. the item has left view. That re-arms the kiosk for the next swipe and stops one
item being charged repeatedly while it sits in frame. This guard is deliberately **time-based, not
frame-count-based**: a frame count would shrink as the poll rate rose, letting a brief detection
dropout re-arm and charge the same item twice. An empty frame never changes the basket.

Tunable constants: `VOTE_TO_ADD` and `REARM_EMPTY_MS` in `frontend/src/lib/state.svelte.js`,
`POLL_MS` and `MAX_CAPTURE_EDGE` in `Kiosk.svelte`. Raising `VOTE_TO_ADD` demands more agreeing
frames — slower, but fewer wrong charges given the known Coca-Cola/ketchup confusion.

## Running a local request

```bash
uv sync --group ml
uv run uvicorn app.main:app --reload --app-dir backend --port 8000

curl -s -X POST http://localhost:8000/recognize \
  -F "file=@ml/data/fooddata/coca cola/IMG_0001.HEIC" # use a JPEG/PNG frame
```

Convert a capture to JPEG first if needed; HEIC is not accepted by this endpoint.

## Tests

`backend/tests/test_recognize.py` overrides the `require_predictor` dependency with a fake, so CI
(`uv sync --frozen`, no `ml` group) needs neither a GPU nor a model download.

## Known limitations

- The kiosk uploads the full camera frame, so a portrait viewport no longer changes what the model
  sees. A camera that itself delivers a portrait frame is still off-distribution, since training
  images are 1280x720 landscape.
- The model confuses Coca-Cola with ketchup in roughly 10% of swipes (see `ml/README.md`).
  Raise `AVC_CONF_THRESHOLD` to trade recall for fewer wrong charges.