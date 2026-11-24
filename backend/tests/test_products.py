import asyncio
import io
import json

import boto3
import pytest
from httpx import ASGITransport, AsyncClient
from moto import mock_aws
from PIL import Image
from store import Store

from app.main import app
from app.storage import get_store


@pytest.fixture(params=["local", "s3"])
def store(request, tmp_path, monkeypatch):
    if request.param == "local":
        yield Store(str(tmp_path / "bucket"))
        return
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    with mock_aws():
        boto3.client("s3").create_bucket(
            Bucket="captures", CreateBucketConfiguration={"LocationConstraint": "us-east-2"}
        )
        yield Store("s3://captures")


def call(store, method, path, **kwargs):
    async def run():
        app.dependency_overrides[get_store] = lambda: store
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                return await client.request(method, path, **kwargs)
        finally:
            app.dependency_overrides.clear()

    return asyncio.run(run())


def add_product(store, name="Water", price=1.0, category="Drinks", art="can"):
    return call(store, "POST", "/products", json={"name": name, "price": price, "category": category, "art": art})


def manifest(store, cid, sku, kind, labelled):
    store.put(f"captures/{cid}/capture.json", json.dumps({"capture_id": cid, "sku": sku, "kind": kind}).encode())
    store.put(
        f"captures/{cid}/manifest.json",
        json.dumps({"capture_id": cid, "sku": sku, "kind": kind, "frames": {"sampled": labelled, "labelled": labelled}}).encode(),
    )


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (120, 40, 40)).save(buf, format="PNG")
    return buf.getvalue()


def test_products_lists_the_catalog(store):
    response = call(store, "GET", "/products")
    assert response.status_code == 200
    assert [p["sku"] for p in response.json()] == ["COKE-330", "HEINZ-570", "BJ-473", "NUT-750"]


def test_get_products_derives_status_and_photos(store):
    manifest(store, "c1", "COKE-330", "train", 90)
    manifest(store, "c2", "COKE-330", "val", 44)
    manifest(store, "c3", "HEINZ-570", "val", 44)
    manifest(store, "c4", "BJ-473", "swipe", 0)
    body = {p["sku"]: p for p in call(store, "GET", "/products").json()}
    assert body["COKE-330"]["status"] == "Ready"
    assert body["COKE-330"]["photos"] == 134
    assert body["HEINZ-570"]["status"] == "Needs images"  # val-only is not Ready
    assert body["HEINZ-570"]["photos"] == 44
    assert body["BJ-473"]["photos"] == 0  # swipe frames don't count as photos
    assert body["NUT-750"]["status"] == "Needs images"


def test_post_product_bootstraps_and_assigns_contiguous_ids(store):
    r1 = add_product(store, name="Sparkling Water")
    assert r1.status_code == 201
    p1 = r1.json()
    assert (p1["class_id"], p1["sku"], p1["retired"], p1["status"]) == (4, "PRD-004", False, "Needs images")
    r2 = add_product(store, name="Chips", category="Snacks", art="bar")
    assert (r2.json()["class_id"], r2.json()["sku"]) == (5, "PRD-005")
    doc = json.loads(store.get("catalog.json"))
    assert [p["class_id"] for p in doc["products"]] == [0, 1, 2, 3, 4, 5]


def test_post_product_rejects_client_supplied_sku(store):
    response = call(
        store, "POST", "/products",
        json={"name": "X", "price": 1, "category": "Drinks", "art": "can", "sku": "HACK-1", "class_id": 99},
    )
    assert response.status_code == 422


def test_patch_edits_fields_but_keeps_sku_and_id(store):
    add_product(store)
    response = call(store, "PATCH", "/products/PRD-004", json={"name": "Sparkling Water", "price": 1.75})
    assert response.status_code == 200
    p = response.json()
    assert (p["sku"], p["class_id"], p["name"], p["price"]) == ("PRD-004", 4, "Sparkling Water", 1.75)


def test_patch_unknown_sku_is_404(store):
    response = call(store, "PATCH", "/products/NOPE-999", json={"name": "x"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


def test_retire_keeps_id_and_refuses_capture(store):
    response = call(store, "PATCH", "/products/COKE-330", json={"retired": True})
    assert response.status_code == 200
    assert response.json()["status"] == "Retired"
    assert response.json()["class_id"] == 0
    assert json.loads(store.get("catalog.json"))["products"][0]["class_id"] == 0  # ID stays

    capture = call(store, "POST", "/captures", json={"sku": "COKE-330", "kind": "train"})
    assert capture.status_code == 400
    assert capture.json()["detail"]["code"] == "retired_sku"

    call(store, "PATCH", "/products/COKE-330", json={"retired": False})
    assert call(store, "POST", "/captures", json={"sku": "COKE-330", "kind": "train"}).status_code == 201


def test_stale_etag_retries_and_keeps_ids_contiguous(store, monkeypatch):
    if not store.bucket:
        pytest.skip("conditional writes need S3 ETags")
    add_product(store, name="First")
    original = store.get_with_etag
    fired = {"once": False}

    def racing_get(key):
        data, etag = original(key)
        if key == "catalog.json" and not fired["once"]:
            fired["once"] = True
            doc = json.loads(data)  # a competing writer adds a product after our read
            cid = len(doc["products"])
            doc["products"].append(
                {"class_id": cid, "sku": f"PRD-{cid:03d}", "name": "Rival", "price": 9, "art": "can", "category": "Snacks", "retired": False}
            )
            store.put("catalog.json", json.dumps(doc).encode())
        return data, etag  # stale ETag -> the API's IfMatch put 412s and retries

    monkeypatch.setattr(store, "get_with_etag", racing_get)
    response = add_product(store, name="Mine")
    assert response.status_code == 201
    doc = json.loads(store.get("catalog.json"))
    ids = [p["class_id"] for p in doc["products"]]
    assert ids == list(range(len(ids)))
    assert {"Rival", "Mine"} <= {p["name"] for p in doc["products"]}


def test_retry_exhaustion_is_409(store, monkeypatch):
    if not store.bucket:
        pytest.skip("conditional writes need S3 ETags")
    add_product(store, name="First")
    original = store.get_with_etag

    def always_racing(key):
        data, etag = original(key)
        if key == "catalog.json":
            doc = json.loads(data)
            cid = len(doc["products"])
            doc["products"].append(
                {"class_id": cid, "sku": f"PRD-{cid:03d}", "name": "Rival", "price": 9, "art": "can", "category": "Snacks", "retired": False}
            )
            store.put("catalog.json", json.dumps(doc).encode())
        return data, etag

    monkeypatch.setattr(store, "get_with_etag", always_racing)
    response = add_product(store, name="Mine")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "catalog_conflict"


def test_seed_runs_once(store):
    import seed_catalog

    root = f"s3://{store.bucket}" if store.bucket else str(store.dir)
    seed_catalog.main(root)
    assert store.exists("catalog.json")
    doc = json.loads(store.get("catalog.json"))
    doc["products"][0]["name"] = "Edited"
    store.put("catalog.json", json.dumps(doc).encode())
    seed_catalog.main(root)  # rerun must not overwrite the edit
    assert json.loads(store.get("catalog.json"))["products"][0]["name"] == "Edited"


def test_recognize_skips_retired(store, monkeypatch):
    if not store.bucket:
        pytest.skip("recognize reads the store catalog via the AVC_STORE env")
    from app.catalog import reset_catalog
    from app.inference import RawDetection, reset_predictor
    from app.main import require_predictor

    monkeypatch.setenv("AVC_STORE", f"s3://{store.bucket}")
    call(store, "PATCH", "/products/COKE-330", json={"retired": True})
    reset_catalog()

    class FakePredictor:
        def predict(self, image):
            return [RawDetection(0, 0.95, (0, 0, 64, 48))]  # class 0 = COKE-330, now retired

    async def run():
        app.dependency_overrides[require_predictor] = lambda: FakePredictor()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                return await client.post("/recognize", files={"file": ("f.png", png_bytes(), "image/png")})
        finally:
            app.dependency_overrides.clear()

    try:
        response = asyncio.run(run())
    finally:
        reset_predictor()
    assert response.status_code == 200
    assert response.json()["items"] == []