"""Annotator, dataset build, materialize, and import, on a local directory and on mocked S3.

The detector is faked, so no GPU or weights are needed; fixture videos are written with cv2.
"""

import json
import shutil

import boto3
import cv2
import numpy as np
import pytest
from moto import mock_aws
from PIL import Image

import annotate
import import_fooddata
from annotate import Store, add_capture, frames, handler
from dataset import build, classes, materialize

BOX = [0.5, 0.5, 0.25, 0.5]


def video(path, seconds, fps=10, size=(64, 48)):
    """An MP4 with a constant frame rate; frame i is filled with grey level i so frames differ."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    for i in range(int(seconds * fps)):
        out.write(np.full((size[1], size[0], 3), i % 256, np.uint8))
    out.release()
    return path


@pytest.fixture(params=["local", "s3"])
def store(request, tmp_path, monkeypatch):
    monkeypatch.setattr(annotate, "yoloe_box", lambda jpg: BOX)
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


def test_samples_first_frame_at_or_after_each_third_of_a_second(tmp_path):
    # 10 fps: frames every 100 ms; the 1/3 s marks are 0, 333, 667, 1000, 1333, 1667 ms
    ms = [round(t) for t, _ in frames(video(tmp_path / "v.mp4", 2))]
    assert ms == [0, 400, 700, 1000, 1400, 1700]


def test_unreadable_video_fails_without_a_manifest(store, tmp_path):
    bad = tmp_path / "source.webm"
    bad.write_bytes(b"not a video")
    cid = add_capture(store, bad, "COKE-330", "train")
    with pytest.raises(ValueError, match="No frames"):
        annotate.annotate(store, cid)
    assert not store.exists(f"captures/{cid}/manifest.json")


def test_train_capture_gets_frames_labels_and_manifest(store, tmp_path):
    portrait = video(tmp_path / "turn.mp4", 2, size=(48, 64))
    cid = add_capture(store, portrait, "COKE-330", "train")
    jpgs = []

    def detect(jpg):  # no box on the third sampled frame
        jpgs.append(jpg)
        return None if len(jpgs) == 3 else BOX

    m = annotate.annotate(store, cid, detect=detect)

    assert m["frames"] == {"sampled": 6, "labelled": 5}  # the frame with no box is skipped
    assert (m["capture_id"], m["sku"], m["kind"]) == (cid, "COKE-330", "train")
    images = store.keys(f"captures/{cid}/images/")
    assert [k.rsplit("/", 1)[1] for k in images] == ["0000.jpg", "0001.jpg", "0003.jpg", "0004.jpg", "0005.jpg"]
    assert len(store.keys(f"captures/{cid}/labels/")) == 5
    assert store.get(f"captures/{cid}/labels/0000.txt") == b"0 0.500000 0.500000 0.250000 0.500000\n"
    local = tmp_path / "frame.jpg"
    store.download(images[0], local)
    assert Image.open(local).size == (1280, 720)  # portrait turned landscape
    assert json.loads(store.get(f"captures/{cid}/manifest.json")) == m


def test_swipe_capture_gets_only_a_manifest(store, tmp_path):
    cid = add_capture(store, video(tmp_path / "swipe.mp4", 1), "NUT-750", "swipe")
    m = annotate.annotate(store, cid)
    assert m["frames"] == {"sampled": 3, "labelled": 0}
    assert store.keys(f"captures/{cid}/") == [f"captures/{cid}/capture.json", f"captures/{cid}/manifest.json"]


def test_lambda_handler_annotates_the_uploaded_capture(store, tmp_path):
    if not store.bucket:
        pytest.skip("the handler reads S3 events")
    cid = add_capture(store, video(tmp_path / "turn.mp4", 1), "HEINZ-570", "val")
    event = {"Records": [{"s3": {"bucket": {"name": "captures"}, "object": {"key": f"raw/{cid}/source.mp4"}}}]}
    [m] = handler(event)
    assert m["frames"] == {"sampled": 3, "labelled": 3}
    assert store.exists(f"captures/{cid}/manifest.json")


def test_build_and_materialize_use_catalog_class_ids(store, tmp_path):
    assert classes() == {"0": "COKE-330", "1": "HEINZ-570", "2": "BJ-473", "3": "NUT-750"}
    train = add_capture(store, video(tmp_path / "a.mp4", 1), "HEINZ-570", "train")
    val = add_capture(store, video(tmp_path / "b.mp4", 1), "NUT-750", "val")
    swipe = add_capture(store, video(tmp_path / "c.mp4", 1), "COKE-330", "swipe")
    pending = add_capture(store, video(tmp_path / "d.mp4", 1), "BJ-473", "train")  # no manifest yet
    for cid in (train, val, swipe):
        annotate.annotate(store, cid)

    m = build(store, "20261118T120000Z")
    assert m["captures"] == {"train": [train], "val": [val], "swipe": [swipe]}
    assert pending not in json.dumps(m)
    assert m["counts"] == {"train": {"HEINZ-570": 3}, "val": {"NUT-750": 3}, "swipe": {"COKE-330": 1}}
    assert json.loads(store.get("datasets/20261118T120000Z/manifest.json")) == m

    out = tmp_path / "yolo"
    materialize(store, "20261118T120000Z", out)
    assert (out / "data.yaml").read_text().endswith(
        "train: images/train\nval: images/val\nnames:\n  0: COKE-330\n  1: HEINZ-570\n  2: BJ-473\n  3: NUT-750\n"
    )
    labels = sorted((out / "labels" / "train").glob("*.txt"))
    assert [p.read_text().split()[0] for p in labels] == ["1", "1", "1"]
    assert {p.read_text().split()[0] for p in (out / "labels" / "val").glob("*.txt")} == {"3"}
    assert sorted(p.stem for p in (out / "images" / "train").glob("*.jpg")) == [p.stem for p in labels]
    assert (out / "swipes" / "COKE-330" / f"{swipe}.mp4").is_file()
    with pytest.raises(FileExistsError):
        materialize(store, "20261118T120000Z", out)


def test_build_rejects_a_sku_outside_the_catalog(store, tmp_path):
    annotate.annotate(store, add_capture(store, video(tmp_path / "a.mp4", 1), "PEPSI-330", "train"))
    with pytest.raises(ValueError, match="PEPSI-330"):
        build(store)


def test_import_turns_fooddata_into_captures(store, tmp_path):
    src = tmp_path / "fooddata"
    video(src / "coca cola" / "IMG_1.MOV", 21, fps=2)
    video(src / "coca cola" / "IMG_2.MOV", 15, fps=2)
    video(src / "coca cola" / "IMG_3.MOV", 2)
    video(src / "nutella" / "IMG_4.MOV", 1.5)
    shutil.copy(src / "coca cola" / "IMG_3.MOV", src / "nutella" / "IMG_9.MOV")

    import_fooddata.main(src, f"s3://{store.bucket}" if store.bucket else str(store.dir))
    captures = [json.loads(store.get(k)) for k in store.keys("captures/") if k.endswith("/capture.json")]
    assert sorted((c["sku"], c["kind"]) for c in captures) == [
        ("COKE-330", "swipe"),
        ("COKE-330", "train"),
        ("COKE-330", "val"),
        ("NUT-750", "swipe"),  # the copy of IMG_3 in nutella/ is skipped
    ]
    manifests = [k for k in store.keys("captures/") if k.endswith("/manifest.json")]
    assert len(manifests) == (0 if store.bucket else 4)  # on S3 the upload triggers the annotator

    import_fooddata.main(src, f"s3://{store.bucket}" if store.bucket else str(store.dir))
    assert len([k for k in store.keys("captures/") if k.endswith("/capture.json")]) == 4


def test_classes_reads_store_catalog_including_retired(store):
    catalog = {
        "version": "1.0.0",
        "products": [
            {"class_id": 0, "sku": "COKE-330", "retired": False},
            {"class_id": 1, "sku": "PRD-001", "retired": True},
        ],
    }
    store.put("catalog.json", json.dumps(catalog).encode())
    assert classes(store) == {"0": "COKE-330", "1": "PRD-001"}  # a retired product keeps its ID


def test_classes_falls_back_to_repo_without_store_catalog(store):
    assert classes(store) == {"0": "COKE-330", "1": "HEINZ-570", "2": "BJ-473", "3": "NUT-750"}
