"""Live eKYC face match — selfie vs the photo on an ID document.

Per the R&D verdict: match directly with a strong age-robust embedding (SFace) — NO
GAN face-aging at inference (aging adds artifacts that hurt recognition). Pipeline:
YuNet detect+align (MIT) -> SFace 128-d embedding (Apache) -> cosine similarity.

Scope: adult re-verification. A childhood-photo-to-adult match is NOT bank-grade and
is explicitly out of scope.
"""

from __future__ import annotations

import cv2
import numpy as np

# SFace cosine: higher = more similar. OpenCV's reference same-identity threshold.
DEFAULT_COSINE_THRESHOLD = 0.363


class FaceMatcher:
    def __init__(
        self, yunet_path: str, sface_path: str,
        cosine_threshold: float = DEFAULT_COSINE_THRESHOLD,
    ) -> None:
        self.detector = cv2.FaceDetectorYN.create(yunet_path, "", (320, 320), 0.9, 0.3, 5000)
        self.recognizer = cv2.FaceRecognizerSF.create(sface_path, "")
        self.cosine_threshold = cosine_threshold

    @staticmethod
    def decode(image_bytes: bytes) -> np.ndarray | None:
        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img

    def _largest_face(self, img: np.ndarray):
        h, w = img.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(img)
        if faces is None or len(faces) == 0:
            return None
        return max(faces, key=lambda f: float(f[2]) * float(f[3]))  # largest by bbox area

    def embed(self, img: np.ndarray) -> np.ndarray | None:
        face = self._largest_face(img)
        if face is None:
            return None
        aligned = self.recognizer.alignCrop(img, face)
        return self.recognizer.feature(aligned)

    def match(self, selfie: np.ndarray, document: np.ndarray) -> dict:
        f_selfie = self.embed(selfie)
        f_doc = self.embed(document)
        faces = {"selfie": f_selfie is not None, "document": f_doc is not None}
        if f_selfie is None or f_doc is None:
            missing = [k for k, v in faces.items() if not v]
            return {
                "match": False, "cosine": None, "faces_detected": faces,
                "note": f"No face detected in: {', '.join(missing)}.",
            }
        cosine = float(self.recognizer.match(f_selfie, f_doc, cv2.FaceRecognizerSF_FR_COSINE))
        return {
            "match": bool(cosine >= self.cosine_threshold),
            "cosine": round(cosine, 4),
            "faces_detected": faces,
            "note": "Faces match." if cosine >= self.cosine_threshold else "Faces do not match.",
        }
