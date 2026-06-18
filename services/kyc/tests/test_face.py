"""Face-match tests: model load + graceful no-face handling.

Real-face accuracy is validated in the demo with actual selfie/Aadhaar images;
unit tests here cover the pipeline and failure modes without storing any face data.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from bobai_kyc.config import get_settings


def _jpeg(color) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (200, 200), color).save(b, "JPEG")
    return b.getvalue()


@pytest.fixture(scope="module")
def matcher():
    s = get_settings()
    if not (Path(s.yunet_path).exists() and Path(s.sface_path).exists()):
        pytest.skip("face-match ONNX models not present in data/models/")
    from bobai_kyc.face import FaceMatcher

    return FaceMatcher(s.yunet_path, s.sface_path)


def test_decode_invalid_bytes_returns_none(matcher):
    assert matcher.decode(b"not-an-image") is None


def test_no_face_is_handled_gracefully(matcher):
    a = matcher.decode(_jpeg((120, 120, 120)))
    b = matcher.decode(_jpeg((30, 30, 30)))
    res = matcher.match(a, b)
    assert res["match"] is False
    assert res["faces_detected"] == {"selfie": False, "document": False}
    assert res["cosine"] is None


def test_api_face_match_no_face(matcher):
    from fastapi.testclient import TestClient

    from bobai_kyc.main import app

    with TestClient(app) as c:
        r = c.post(
            "/v1/kyc/face/match",
            files={
                "selfie": ("s.jpg", _jpeg((120, 120, 120)), "image/jpeg"),
                "document": ("d.jpg", _jpeg((30, 30, 30)), "image/jpeg"),
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["match"] is False
        assert body["threshold"] > 0
