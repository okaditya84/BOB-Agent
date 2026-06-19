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

    def liveness(self, img: np.ndarray) -> dict:
        """Passive single-frame liveness heuristic (commercially-clean, OpenCV only).

        Combines: a face is present and adequately sized; the face region is in
        sharp focus (Laplacian variance — printed/again-photographed IDs are softer);
        and colour variety (greyscale photocopies / heavy moire score low). This is a
        screen/print *triage* signal, NOT a certified presentation-attack detector;
        production should use a certified PAD (see docs/PITCH.md).
        """
        face = self._largest_face(img)
        if face is None:
            return {"live": False, "score": 0.0, "reason": "No face detected."}

        x, y, w, h = (int(v) for v in face[:4])
        H, W = img.shape[:2]
        x, y = max(0, x), max(0, y)
        crop = img[y:y + h, x:x + w]
        if crop.size == 0:
            return {"live": False, "score": 0.0, "reason": "Face region empty."}

        face_ratio = (w * h) / float(W * H)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        colour_std = float(crop.reshape(-1, 3).std(axis=0).mean())

        size_ok = face_ratio >= 0.04
        sharp_ok = sharpness >= 40.0
        colour_ok = colour_std >= 12.0
        passed = sum([size_ok, sharp_ok, colour_ok])
        score = round(passed / 3.0, 3)
        reasons = []
        if not size_ok:
            reasons.append("face too small/far")
        if not sharp_ok:
            reasons.append("image too soft (possible re-photographed ID/screen)")
        if not colour_ok:
            reasons.append("low colour variety (possible photocopy)")
        return {
            "live": passed >= 2,
            "score": score,
            "reason": "Passive checks passed." if passed >= 2 else "; ".join(reasons),
            "metrics": {"face_ratio": round(face_ratio, 4), "sharpness": round(sharpness, 1),
                        "colour_std": round(colour_std, 1)},
        }

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
