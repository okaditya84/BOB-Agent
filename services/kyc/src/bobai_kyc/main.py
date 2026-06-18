"""FastAPI app for the BOBAI KYC document-requirements service."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .fraud import analyze_document
from .kb import KnowledgeBase
from .matcher import check
from .ocr import TesseractEngine
from .schemas import (
    CheckRequest,
    CheckResult,
    ClaimedFields,
    DocumentFraudReport,
    DocumentType,
    FaceMatchResult,
    Product,
    RequirementSet,
)


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


def _kb() -> KnowledgeBase:
    return app.state.kb


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "kyc"}


@app.get("/v1/kyc/products", response_model=list[Product])
def products() -> list[Product]:
    return _kb().list_products()


@app.get("/v1/kyc/requirements", response_model=RequirementSet)
def requirements(
    product_id: str, profile: str | None = None, constitution: str | None = None
) -> RequirementSet:
    try:
        return _kb().requirements(product_id, profile=profile, constitution=constitution)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown product '{product_id}'.")


@app.post("/v1/kyc/check", response_model=CheckResult)
def check_documents(body: CheckRequest) -> CheckResult:
    try:
        req = _kb().requirements(
            body.product_id, profile=body.profile, constitution=body.constitution
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown product '{body.product_id}'.")
    return check(req, body.submitted)


@app.post("/v1/kyc/document/analyze", response_model=DocumentFraudReport)
async def analyze_doc(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(DocumentType.OTHER),
    name: str | None = Form(None),
    dob: str | None = Form(None),
    document_number: str | None = Form(None),
    run_ocr: bool = Form(True),
) -> DocumentFraudReport:
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file upload.")
    claimed = ClaimedFields(name=name, dob=dob, document_number=document_number)
    engine = app.state.ocr if run_ocr else None
    return analyze_document(image_bytes, document_type, claimed, ocr_engine=engine)


@app.post("/v1/kyc/face/match", response_model=FaceMatchResult)
async def face_match(
    selfie: UploadFile = File(...),
    document: UploadFile = File(...),
) -> FaceMatchResult:
    matcher = app.state.face
    if matcher is None:
        raise HTTPException(
            status_code=503,
            detail="Face-match models not available. Place YuNet + SFace ONNX in data/models/.",
        )
    selfie_bytes, doc_bytes = await selfie.read(), await document.read()
    selfie_img = matcher.decode(selfie_bytes)
    doc_img = matcher.decode(doc_bytes)
    if selfie_img is None or doc_img is None:
        raise HTTPException(status_code=400, detail="Could not decode one or both images.")
    result = matcher.match(selfie_img, doc_img)
    return FaceMatchResult(
        match=result["match"], cosine=result["cosine"],
        faces_detected=result["faces_detected"], threshold=matcher.cosine_threshold,
        note=result["note"],
        disclaimer="Adult re-verification only; not bank-grade for child-to-adult age gaps. "
        "Liveness/anti-spoofing and provenance (DigiLocker/Aadhaar Secure-QR) recommended for production.",
    )
