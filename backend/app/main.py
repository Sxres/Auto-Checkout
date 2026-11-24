import io
import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from .captures import router as captures_router
from .catalog import product_for
from .inference import ModelUnavailable, Predictor, get_predictor
from .products import router as products_router
from .schemas import Detection, ImageSize, Item, RecognizeResponse

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
logger = logging.getLogger(__name__)


def warm_up() -> None:
    # Loading the checkpoint and the first CUDA inference together take ~50s. Doing it
    # here keeps that wait out of the first customer's scan.
    get_predictor().predict(Image.new("RGB", (640, 640)))


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await run_in_threadpool(warm_up)
    except ModelUnavailable as exc:
        logger.warning("Recognition unavailable at startup: %s", exc)
    yield


app = FastAPI(title="Auto Vision Checkout API", lifespan=lifespan)

DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("AVC_CORS_ORIGINS", DEFAULT_ORIGINS).split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(captures_router)
app.include_router(products_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def require_predictor() -> Predictor:
    try:
        return get_predictor()
    except ModelUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "model_unavailable", "message": str(exc)},
        ) from exc


def error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


@app.post("/recognize", response_model=RecognizeResponse)
async def recognize(
    file: Annotated[UploadFile, File(...)],
    predictor: Annotated[Predictor, Depends(require_predictor)],
) -> RecognizeResponse:
    if not (file.content_type or "").startswith("image/"):
        raise error(415, "unsupported_media_type", "Upload a JPEG or PNG image.")

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise error(413, "image_too_large", "Images must be 10 MB or smaller.")

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise error(400, "invalid_image", "The upload could not be decoded as an image.") from exc

    image = image.convert("RGB")
    width, height = image.size

    detections: list[Detection] = []
    for raw in await run_in_threadpool(predictor.predict, image):
        product = product_for(raw.class_id)
        if product is None:
            continue
        x1, y1, x2, y2 = raw.box
        detections.append(
            Detection(
                label=product["name"],
                sku=product["sku"],
                class_id=raw.class_id,
                confidence=round(raw.confidence, 4),
                x=round(x1 / width * 100, 2),
                y=round(y1 / height * 100, 2),
                w=round((x2 - x1) / width * 100, 2),
                h=round((y2 - y1) / height * 100, 2),
            )
        )
    detections.sort(key=lambda d: d.confidence, reverse=True)

    items: list[Item] = []
    seen: set[str] = set()
    for detection in detections:
        if detection.sku in seen:
            continue
        seen.add(detection.sku)
        product = product_for(detection.class_id)
        items.append(
            Item(
                key=product["sku"],
                sku=product["sku"],
                name=product["name"],
                price=product["price"],
                art=product["art"],
            )
        )

    return RecognizeResponse(
        items=items,
        detections=detections,
        image=ImageSize(width=width, height=height),
    )