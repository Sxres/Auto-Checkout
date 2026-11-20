# Loads our trained YOLO model and asks it what it can see in a photo.
# The heavy ML library is only imported when we actually need it, so the API still starts
# on machines that don't have it installed.

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from PIL import Image


# Raised when there's no model to use: the weights file is missing, or the ML libraries
# aren't installed. The API catches it and says "recognition is unavailable" instead of crashing.
class ModelUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class RawDetection:
    class_id: int
    confidence: float
    box: tuple[float, float, float, float]  # x1, y1, x2, y2 in image pixels


class Predictor(Protocol):
    def predict(self, image: Image.Image) -> list[RawDetection]: ...


def model_path() -> Path:
    return Path(os.environ.get("AVC_MODEL_PATH", "ml/model/best.pt"))


def conf_threshold() -> float:
    # High enough to drop spurious boxes on non-products; close-up product scans score ~0.45+.
    return float(os.environ.get("AVC_CONF_THRESHOLD", "0.35"))


class YoloPredictor:
    def __init__(self, weights: Path, conf: float) -> None:
        if not weights.is_file():
            raise ModelUnavailable(
                f"Model weights not found at {weights}. Set AVC_MODEL_PATH to a valid checkpoint."
            )
        try:
            from ultralytics import YOLO

            self._model = YOLO(str(weights))
        except ImportError as exc:
            raise ModelUnavailable(
                "The ml dependency group is not installed. Run: uv sync --group ml"
            ) from exc
        except Exception as exc:
            raise ModelUnavailable(f"Could not load checkpoint {weights}: {exc}") from exc
        self._conf = conf

    def predict(self, image: Image.Image) -> list[RawDetection]:
        result = self._model.predict(image, conf=self._conf, verbose=False)[0]
        detections = []
        for box in result.boxes:
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            detections.append(
                RawDetection(
                    class_id=int(box.cls.item()),
                    confidence=float(box.conf.item()),
                    box=(x1, y1, x2, y2),
                )
            )
        return detections


_predictor: Predictor | None = None
_predictor_key: tuple[str, float] | None = None


# Loading the model is slow, so we keep the one we already loaded and reuse it for every scan.
# It only loads again if someone changes the weights path or the confidence cutoff.
def get_predictor() -> Predictor:
    global _predictor, _predictor_key
    key = (str(model_path()), conf_threshold())
    if _predictor is None or _predictor_key != key:
        _predictor = YoloPredictor(model_path(), conf_threshold())
        _predictor_key = key
    return _predictor


def reset_predictor() -> None:
    global _predictor, _predictor_key
    _predictor = None
    _predictor_key = None