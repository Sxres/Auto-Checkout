import asyncio
import io
import os

from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.inference import RawDetection, reset_predictor
from app.main import app, require_predictor

WIDTH, HEIGHT = 640, 480


def png_bytes(width=WIDTH, height=HEIGHT):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (120, 40, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


class FakePredictor:
    def __init__(self, detections):
        self.detections = detections
        self.calls = 0

    def predict(self, image):
        self.calls += 1
        return self.detections


def post(data, content_type="image/png", predictor=None):
    async def run():
        if predictor is not None:
            app.dependency_overrides[require_predictor] = lambda: predictor
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                return await client.post(
                    "/recognize",
                    files={"file": ("frame.png", data, content_type)},
                )
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(run())


def test_known_detection_maps_to_catalog():
    # Box (64, 48, 192, 240) on 640x480 -> 10%, 10%, 20%, 40%.
    predictor = FakePredictor([RawDetection(0, 0.93, (64, 48, 192, 240))])
    response = post(png_bytes(), predictor=predictor)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == [
        {
            "key": "COKE-330",
            "sku": "COKE-330",
            "name": "Coca-Cola 330ml",
            "price": 1.99,
            "art": "can",
        }
    ]
    assert body["detections"] == [
        {
            "label": "Coca-Cola 330ml",
            "sku": "COKE-330",
            "class_id": 0,
            "confidence": 0.93,
            "x": 10.0,
            "y": 10.0,
            "w": 20.0,
            "h": 40.0,
        }
    ]
    assert body["image"] == {"width": WIDTH, "height": HEIGHT}
    assert predictor.calls == 1


def test_no_detections_is_a_success():
    response = post(png_bytes(), predictor=FakePredictor([]))

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "detections": [],
        "image": {"width": WIDTH, "height": HEIGHT},
    }


def test_unknown_class_id_is_ignored():
    predictor = FakePredictor([RawDetection(99, 0.99, (0, 0, 10, 10))])
    response = post(png_bytes(), predictor=predictor)

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["detections"] == []


def test_detections_sorted_and_items_deduplicated():
    predictor = FakePredictor(
        [
            RawDetection(3, 0.40, (0, 0, 64, 48)),
            RawDetection(0, 0.95, (64, 48, 192, 240)),
            RawDetection(0, 0.60, (128, 96, 256, 192)),
        ]
    )
    body = post(png_bytes(), predictor=predictor).json()

    assert [d["confidence"] for d in body["detections"]] == [0.95, 0.6, 0.4]
    assert [i["sku"] for i in body["items"]] == ["COKE-330", "NUT-750"]


def test_undecodable_upload_is_a_client_error():
    response = post(b"this is not an image", predictor=FakePredictor([]))

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_image"


def test_non_image_content_type_is_rejected():
    response = post(png_bytes(), content_type="text/plain", predictor=FakePredictor([]))

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_media_type"


def test_oversized_upload_is_rejected():
    response = post(b"x" * (10 * 1024 * 1024 + 1), predictor=FakePredictor([]))

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "image_too_large"


def test_missing_weights_is_unavailable():
    previous = os.environ.get("AVC_MODEL_PATH")
    os.environ["AVC_MODEL_PATH"] = "ml/model/does-not-exist.pt"
    reset_predictor()
    try:
        response = post(png_bytes())
    finally:
        reset_predictor()
        if previous is None:
            del os.environ["AVC_MODEL_PATH"]
        else:
            os.environ["AVC_MODEL_PATH"] = previous

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "model_unavailable"