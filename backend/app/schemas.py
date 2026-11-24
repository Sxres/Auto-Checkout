from pydantic import BaseModel, ConfigDict, Field


class CaptureRequest(BaseModel):
    sku: str
    kind: str


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # the server assigns sku and class_id, not the client
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    category: str
    art: str


class ProductPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")  # sku and class_id are immutable
    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, ge=0)
    category: str | None = None
    art: str | None = None
    retired: bool | None = None


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