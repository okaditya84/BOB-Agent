"""Risk detectors. Each returns a DetectorResult (raw 0..1 + a plain-English reason)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DetectorResult:
    """One detector's verdict. `raw` is its own 0..1 risk; `detail` is the reason code."""

    raw: float
    detail: str
    data: dict = field(default_factory=dict)


__all__ = ["DetectorResult"]
