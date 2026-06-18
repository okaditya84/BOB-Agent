"""Image tamper triage via Error Level Analysis (ELA).

ELA re-compresses the image at a known JPEG quality and measures the residual.
Uniformly-compressed (untouched) regions settle to a low, even error; edited or
spliced regions retain a different error level and stand out. This is a *triage*
signal that raises review — not forensic proof of forgery.
"""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image, ImageChops

from .schemas import ELAResult

# ELA tuning (algorithm parameters, not data): how mean/spread of residual map to risk.
_MEAN_SCALE = 12.0
_P95_SCALE = 60.0
_SUSPICIOUS_AT = 0.5


def ela_analyze(image_bytes: bytes, quality: int = 90) -> ELAResult:
    original = Image.open(BytesIO(image_bytes)).convert("RGB")

    buffer = BytesIO()
    original.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    resaved = Image.open(buffer).convert("RGB")

    diff = np.asarray(ImageChops.difference(original, resaved), dtype=np.float32)
    mean_error = float(diff.mean())
    max_error = float(diff.max())
    p95_error = float(np.percentile(diff, 95))

    score = min(1.0, 0.5 * (mean_error / _MEAN_SCALE) + 0.5 * (p95_error / _P95_SCALE))
    suspicious = score >= _SUSPICIOUS_AT
    note = (
        "Uneven recompression residual — region(s) may have been edited; recommend review."
        if suspicious
        else "Recompression residual is even/low — no tampering indicated by ELA."
    )
    return ELAResult(
        score=round(score, 3), mean_error=round(mean_error, 2), max_error=round(max_error, 2),
        p95_error=round(p95_error, 2), suspicious=suspicious, note=note,
    )
