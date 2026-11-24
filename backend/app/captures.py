# Capture API (issue #14): products, capture creation with a presigned S3 POST, and
# capture status derived from which objects exist (no database). Storage is AVC_STORE:
# an S3 bucket or a local directory with the same layout, via the shared Store.

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from store import Store, now

from .catalog import read_catalog
from .schemas import CaptureRequest
from .storage import StoreDep

router = APIRouter()

KINDS = ("train", "val", "swipe")
SOURCE_CONTENT_TYPE = "video/webm"
MIN_UPLOAD_BYTES = 1024
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
UPLOAD_EXPIRES_IN = 900


def error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def capture_status(store: Store, capture_id: str) -> tuple[str, dict | None]:
    if store.exists(f"captures/{capture_id}/manifest.json"):
        manifest = json.loads(store.get(f"captures/{capture_id}/manifest.json"))
        return "ready", manifest["frames"]
    if store.keys(f"raw/{capture_id}/"):
        return "processing", None
    return "awaiting_upload", None


def capture_view(store: Store, capture: dict) -> dict:
    status, frames = capture_status(store, capture["capture_id"])
    return {
        "capture_id": capture["capture_id"],
        "sku": capture["sku"],
        "kind": capture["kind"],
        "status": status,
        "frames": frames,
    }


@router.post("/captures", status_code=201)
def create_capture(body: CaptureRequest, request: Request, store: StoreDep) -> dict:
    if body.kind not in KINDS:
        raise error(400, "invalid_kind", f'Unknown capture kind "{body.kind}".')
    product = next((p for p in read_catalog(store)["products"] if p["sku"] == body.sku), None)
    if product is None:
        raise error(400, "invalid_sku", f'SKU "{body.sku}" is not in the catalog.')
    if product.get("retired", False):
        raise error(400, "retired_sku", f'SKU "{body.sku}" is retired.')

    capture_id = uuid.uuid4().hex
    capture = {"capture_id": capture_id, "sku": body.sku, "kind": body.kind, "created_at": now()}
    # capture.json must exist before the video upload: on S3 that upload triggers the annotator.
    store.put(f"captures/{capture_id}/capture.json", json.dumps(capture).encode())

    key = f"raw/{capture_id}/source.webm"
    if store.bucket:
        presigned = store.s3.generate_presigned_post(
            Bucket=store.bucket,
            Key=key,
            Fields={"Content-Type": SOURCE_CONTENT_TYPE},
            Conditions=[
                ["eq", "$key", key],
                {"Content-Type": SOURCE_CONTENT_TYPE},
                ["content-length-range", MIN_UPLOAD_BYTES, MAX_UPLOAD_BYTES],
            ],
            ExpiresIn=UPLOAD_EXPIRES_IN,
        )
        upload = {"url": presigned["url"], "fields": presigned["fields"], "expires_in": UPLOAD_EXPIRES_IN}
    else:
        # No S3 to presign against: the browser posts to the local upload route below.
        url = f"{str(request.base_url).rstrip('/')}/captures/{capture_id}/source"
        upload = {"url": url, "fields": {}, "expires_in": UPLOAD_EXPIRES_IN}
    return {"capture_id": capture_id, "upload": upload}


@router.post("/captures/{capture_id}/source", status_code=204)
async def upload_source(
    capture_id: str, file: Annotated[UploadFile, File(...)], store: StoreDep
) -> Response:
    if not store.exists(f"captures/{capture_id}/capture.json"):
        raise error(404, "not_found", "Capture not found.")
    if not (file.content_type or "").startswith("video/webm"):
        raise error(415, "unsupported_media_type", "Upload a WebM video.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise error(413, "video_too_large", "Videos must be 100 MB or smaller.")
    if len(data) < MIN_UPLOAD_BYTES:
        raise error(400, "video_too_small", "The video is empty or too small.")
    store.put(f"raw/{capture_id}/source.webm", data)
    return Response(status_code=204)


@router.get("/captures/{capture_id}")
def get_capture(capture_id: str, store: StoreDep) -> dict:
    if not store.exists(f"captures/{capture_id}/capture.json"):
        raise error(404, "not_found", "Capture not found.")
    return capture_view(store, json.loads(store.get(f"captures/{capture_id}/capture.json")))


@router.get("/captures")
def list_captures(sku: str, store: StoreDep) -> list[dict]:
    views = []
    for key in store.keys("captures/"):
        if not key.endswith("/capture.json"):
            continue
        capture = json.loads(store.get(key))
        if capture["sku"] == sku:
            views.append(capture_view(store, capture))
    return views