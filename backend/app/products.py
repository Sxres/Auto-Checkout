# Products API (issue #20): catalog.json at the store root is the source of truth.
# GET derives status/photos from the captures; POST and PATCH are read-modify-write with an
# S3 conditional write (IfMatch on the read ETag), re-read and re-applied on conflict.

import json

from fastapi import APIRouter, HTTPException
from store import PreconditionFailed, Store

from .catalog import CATALOG_PATH, read_catalog
from .schemas import ProductCreate, ProductPatch
from .storage import StoreDep

router = APIRouter()

MAX_WRITE_ATTEMPTS = 5


def error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _derive(store: Store) -> tuple[dict[str, int], set[str]]:
    """Labelled train+val frames per SKU, and the SKUs that have a ready train capture."""
    photos: dict[str, int] = {}
    has_train: set[str] = set()
    for key in store.keys("captures/"):
        if not key.endswith("/manifest.json"):
            continue
        m = json.loads(store.get(key))
        if m["kind"] in ("train", "val"):
            photos[m["sku"]] = photos.get(m["sku"], 0) + m["frames"]["labelled"]
        if m["kind"] == "train":
            has_train.add(m["sku"])
    return photos, has_train


def _view(product: dict, photos: dict[str, int], has_train: set[str]) -> dict:
    if product.get("retired", False):
        status = "Retired"
    elif product["sku"] in has_train:
        status = "Ready"
    else:
        status = "Needs images"
    return {**product, "status": status, "photos": photos.get(product["sku"], 0)}


def _update_catalog(store: Store, mutate):
    """Apply mutate(doc) and write catalog.json conditionally, re-reading and re-applying on
    conflict. Bootstraps from the repo seed when catalog.json is missing. Returns mutate's result."""
    for _ in range(MAX_WRITE_ATTEMPTS):
        data, etag = store.get_with_etag("catalog.json")
        creating = data is None
        doc = json.loads(CATALOG_PATH.read_text(encoding="utf-8")) if creating else json.loads(data)
        result = mutate(doc)
        payload = json.dumps(doc, indent=2).encode()
        try:
            if creating:
                store.put("catalog.json", payload, if_none_match="*")
            else:
                store.put("catalog.json", payload, if_match=etag)
            return result
        except PreconditionFailed:
            continue
    raise error(409, "catalog_conflict", "The catalog kept changing under us; please try again.")


@router.get("/products")
def products(store: StoreDep) -> list[dict]:
    doc = read_catalog(store)
    photos, has_train = _derive(store)
    return [_view(p, photos, has_train) for p in doc["products"]]


@router.post("/products", status_code=201)
def create_product(body: ProductCreate, store: StoreDep) -> dict:
    def add(doc: dict) -> dict:
        products = doc["products"]
        ids = [p["class_id"] for p in products]
        assert ids == list(range(len(ids))), f"catalog class_id values must be 0..{len(ids) - 1}: {ids}"
        class_id = len(products)  # retirement never removes entries, so IDs stay contiguous
        sku = f"PRD-{class_id:03d}"
        if any(p["sku"] == sku for p in products):
            raise error(409, "sku_exists", f"SKU {sku} already exists.")
        product = {
            "class_id": class_id,
            "sku": sku,
            "name": body.name,
            "price": body.price,
            "art": body.art,
            "category": body.category,
            "retired": False,
        }
        products.append(product)
        return product

    product = _update_catalog(store, add)
    photos, has_train = _derive(store)
    return _view(product, photos, has_train)


@router.patch("/products/{sku}")
def patch_product(sku: str, body: ProductPatch, store: StoreDep) -> dict:
    changes = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}

    def edit(doc: dict) -> dict:
        product = next((p for p in doc["products"] if p["sku"] == sku), None)
        if product is None:
            raise error(404, "not_found", f'Product "{sku}" not found.')
        product.update(changes)
        return product

    product = _update_catalog(store, edit)
    photos, has_train = _derive(store)
    return _view(product, photos, has_train)