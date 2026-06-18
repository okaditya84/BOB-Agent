"""ML anomaly detector — an independent, unsupervised perspective on the event.

Combines a batch model (scikit-learn IsolationForest, trained on synthetic "normal"
behaviour so it has signal from the first request) with an online streaming model
(River HalfSpaceTrees, which adapts to drift). This catches *combinations* of weak
signals that no single heuristic rule would flag.
"""

from __future__ import annotations

import numpy as np
from river import anomaly
from sklearn.ensemble import IsolationForest

from . import DetectorResult

# The feature space the model reasons over. Built by the engine from the heuristics.
# (Time-of-day is intentionally excluded — the context detector already handles it,
#  so including it here would double-count.)
FEATURES = ["amount_norm", "device_new", "geo_speed_norm", "behavioral_dev", "sensitivity"]


class RiskModel:
    """Holds the trained models. Instantiate once and reuse (it learns online)."""

    def __init__(self, seed: int = 42) -> None:
        rng = np.random.default_rng(seed)
        n = 800
        # Synthetic "normal" sessions: small/no amount, known device, no travel, low drift.
        # We deliberately include the "perfectly clean" corner (exact zeros) so a routine
        # known-device login sits in a dense, normal region rather than looking like a
        # rare outlier.
        clean_mask = rng.random(n) < 0.5  # half the sessions are perfectly clean
        amount = np.where(rng.random(n) < 0.8, 0.0, np.abs(rng.normal(0.0, 0.03, n))).clip(0, 1)
        geo = np.where(clean_mask, 0.0, np.abs(rng.normal(0.0, 0.04, n))).clip(0, 1)
        behavioral = np.where(clean_mask, 0.0, np.abs(rng.normal(0.0, 0.05, n))).clip(0, 1)
        x_train = np.column_stack(
            [
                amount,                                    # amount_norm (mostly zero)
                np.zeros(n),                                # device_new = 0 (trusted)
                geo,                                        # geo_speed_norm (~0)
                behavioral,                                 # behavioral_dev (low)
                rng.uniform(0.03, 0.30, n),                 # sensitivity (routine actions)
            ]
        )
        self._iforest = IsolationForest(
            n_estimators=150, contamination=0.05, random_state=seed
        ).fit(x_train)
        train_scores = self._iforest.score_samples(x_train)  # higher = more normal
        self._hi = float(np.percentile(train_scores, 50))
        self._lo = float(np.percentile(train_scores, 1))

        self._hst = anomaly.HalfSpaceTrees(seed=seed)
        for row in x_train:
            self._hst.learn_one(self._to_dict(row))

    @staticmethod
    def _to_dict(vec) -> dict[str, float]:
        return {f: float(v) for f, v in zip(FEATURES, vec)}

    def score(self, features: dict[str, float]) -> DetectorResult:
        vec = np.array([[float(features.get(f, 0.0)) for f in FEATURES]])

        s = float(self._iforest.score_samples(vec)[0])
        if self._hi == self._lo:
            raw_if = 0.0
        else:
            raw_if = min(1.0, max(0.0, (self._hi - s) / (self._hi - self._lo)))

        d = {f: float(features.get(f, 0.0)) for f in FEATURES}
        hst_score = float(self._hst.score_one(d))
        self._hst.learn_one(d)  # online adaptation to drift

        raw = min(1.0, 0.6 * raw_if + 0.4 * hst_score)
        detail = (
            f"ML anomaly model flagged unusual feature combination "
            f"(isolation-forest {raw_if:.2f}, streaming {hst_score:.2f})."
            if raw > 0.2
            else "ML anomaly model: event consistent with normal behaviour."
        )
        return DetectorResult(raw, detail, {"iforest": round(raw_if, 3), "streaming": round(hst_score, 3)})
