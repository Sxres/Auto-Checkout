from pydantic import BaseModel


class Item(BaseModel):
    key: str
    sku: str
    name: str
    price: float
    art: str


class Detection(BaseModel):
    label: str
    sku: str
    class_id: int
    confidence: float
    x: float
    y: float
    w: float
    h: float


class ImageSize(BaseModel):
    width: int
    height: int


class RecognizeResponse(BaseModel):
    items: list[Item]
    detections: list[Detection]
    image: ImageSize