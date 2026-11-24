import asyncio
import base64
import json

import boto3
import pytest
from httpx import ASGITransport, AsyncClient
from moto import mock_aws
from store import Store

from app import captures
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


def new_capture(store, sku="COKE-330", kind="train"):
    return call(store, "POST", "/captures", json={"sku": sku, "kind": kind}).json()["capture_id"]


def test_products_lists_the_catalog(store):
    response = call(store, "GET", "/products")
    assert response.status_code == 200
    assert [p["sku"] for p in response.json()] == ["COKE-330", "HEINZ-570", "BJ-473", "NUT-750"]


def test_create_capture_rejects_unknown_kind(store):
    response = call(store, "POST", "/captures", json={"sku": "COKE-330", "kind": "nope"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_kind"


def test_create_capture_rejects_unknown_sku(store):
    response = call(store, "POST", "/captures", json={"sku": "PEPSI-330", "kind": "train"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_sku"


def test_create_capture_writes_capture_json_first(store):
    response = call(store, "POST", "/captures", json={"sku": "COKE-330", "kind": "train"})
    assert response.status_code == 201
    cid = response.json()["capture_id"]
    capture = json.loads(store.get(f"captures/{cid}/capture.json"))
    assert (capture["sku"], capture["kind"]) == ("COKE-330", "train")
    assert response.json()["upload"]["expires_in"] == 900


def test_presigned_post_locks_key_type_and_size(store):
    if not store.bucket:
        pytest.skip("presigned POST is S3-only")
    response = call(store, "POST", "/captures", json={"sku": "COKE-330", "kind": "train"})
    cid = response.json()["capture_id"]
    key = f"raw/{cid}/source.webm"
    fields = response.json()["upload"]["fields"]
    assert fields["key"] == key
    assert fields["Content-Type"] == "video/webm"
    conditions = json.loads(base64.b64decode(fields["policy"]))["conditions"]
    assert ["content-length-range", 1024, 104857600] in conditions
    assert {"Content-Type": "video/webm"} in conditions
    assert any(c == ["eq", "$key", key] or c == {"key": key} for c in conditions)


def test_local_store_points_upload_at_the_local_route(store):
    if store.bucket:
        pytest.skip("local directory store only")
    response = call(store, "POST", "/captures", json={"sku": "COKE-330", "kind": "train"})
    cid = response.json()["capture_id"]
    upload = response.json()["upload"]
    assert upload["url"].endswith(f"/captures/{cid}/source")
    assert upload["fields"] == {}


def test_status_follows_the_objects(store):
    cid = new_capture(store)
    assert call(store, "GET", f"/captures/{cid}").json()["status"] == "awaiting_upload"
    assert call(store, "GET", f"/captures/{cid}").json()["frames"] is None

    store.put(f"raw/{cid}/source.webm", b"x" * 2048)
    assert call(store, "GET", f"/captures/{cid}").json()["status"] == "processing"

    store.put(f"captures/{cid}/manifest.json", json.dumps({"frames": {"sampled": 90, "labelled": 88}}).encode())
    body = call(store, "GET", f"/captures/{cid}").json()
    assert body["status"] == "ready"
    assert body["frames"] == {"sampled": 90, "labelled": 88}


def test_unknown_capture_is_404(store):
    response = call(store, "GET", "/captures/doesnotexist")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "not_found"


def test_list_captures_filters_by_sku(store):
    coke = new_capture(store, "COKE-330", "train")
    new_capture(store, "NUT-750", "val")
    body = call(store, "GET", "/captures", params={"sku": "COKE-330"}).json()
    assert [c["capture_id"] for c in body] == [coke]


def test_local_upload_writes_the_video(store):
    if store.bucket:
        pytest.skip("local upload route is for the directory store")
    cid = new_capture(store)
    response = call(store, "POST", f"/captures/{cid}/source", files={"file": ("source.webm", b"x" * 2048, "video/webm")})
    assert response.status_code == 204
    assert store.get(f"raw/{cid}/source.webm") == b"x" * 2048
    assert call(store, "GET", f"/captures/{cid}").json()["status"] == "processing"


def test_local_upload_rejects_wrong_type(store):
    if store.bucket:
        pytest.skip("local upload route is for the directory store")
    cid = new_capture(store)
    response = call(store, "POST", f"/captures/{cid}/source", files={"file": ("source.webm", b"x" * 2048, "text/plain")})
    assert response.status_code == 415
    assert response.json()["detail"]["code"] == "unsupported_media_type"


def test_local_upload_rejects_oversized(store, monkeypatch):
    if store.bucket:
        pytest.skip("local upload route is for the directory store")
    monkeypatch.setattr(captures, "MAX_UPLOAD_BYTES", 1024)
    cid = new_capture(store)
    response = call(store, "POST", f"/captures/{cid}/source", files={"file": ("source.webm", b"x" * 2048, "video/webm")})
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "video_too_large"