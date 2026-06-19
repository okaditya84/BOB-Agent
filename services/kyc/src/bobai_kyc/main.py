"""FastAPI app factory for the BOBAI KYC service."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .kb import KnowledgeBase
from .ocr import TesseractEngine
from .routers import documents, ekyc
from .vision import DocumentVisionClassifier


def _load_face_matcher(settings):
    """Load the face matcher lazily; return None if models are unavailable."""
    import os

    if not (os.path.exists(settings.yunet_path) and os.path.exists(settings.sface_path)):
        return None
    try:
        from .face import FaceMatcher

        return FaceMatcher(settings.yunet_path, settings.sface_path)
    except Exception:
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.kb = KnowledgeBase.from_file(settings.kb_path)
    app.state.ocr = TesseractEngine()
    app.state.face = _load_face_matcher(settings)
    app.state.vision = DocumentVisionClassifier(settings.vision_model, settings.groq_base_url)
    yield


app = FastAPI(
    title="BOBAI KYC Service",
    version="0.1.0",
    description="Document-requirements resolver over the BoB knowledge base.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(documents.router)
app.include_router(ekyc.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "kyc"}
