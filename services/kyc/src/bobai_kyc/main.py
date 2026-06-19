"""FastAPI app for the BOBAI KYC document-requirements service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .config import get_settings
from .fraud import analyze_document
from .kb import KnowledgeBase
from .matcher import check
from .ocr import TesseractEngine
from .schemas import (
    CheckRequest,
    CheckResult,
    ClaimedFields,
    DocumentClassification,
    DocumentFraudReport,
    DocumentType,
    EkycVerifyResult,
    FaceMatchResult,
    LivenessResult,
    Product,
    RequirementSet,
)
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


def _face_disclaimer() -> str:
    return (
        "Adult re-verification only. Passive liveness is a screen/print triage signal, "
        "not a certified PAD; production should add certified liveness + provenance "
        "(DigiLocker / Aadhaar Secure-QR)."
    )


@app.post("/v1/kyc/liveness", response_model=LivenessResult)
async def liveness_check(selfie: UploadFile = File(...)) -> LivenessResult:
    matcher = app.state.face
    if matcher is None:
        raise HTTPException(status_code=503, detail="Face models not available.")
    img = matcher.decode(await selfie.read())
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image.")
    r = matcher.liveness(img)
    return LivenessResult(live=r["live"], score=r["score"], reason=r["reason"],
                          metrics=r.get("metrics", {}))


@app.post("/v1/kyc/ekyc/verify", response_model=EkycVerifyResult)
async def ekyc_verify(
    selfie: UploadFile = File(...),
    document: UploadFile = File(...),
    expected_type: str = Form("aadhaar"),
) -> EkycVerifyResult:
    """Full eKYC: (1) vision-LLM verifies the document IS a genuine ID of the expected
    type, (2) passive liveness on the live selfie, (3) face match vs the ID photo."""
    matcher = app.state.face
    if matcher is None:
        raise HTTPException(status_code=503, detail="Face models not available.")
    selfie_bytes = await selfie.read()
    doc_bytes = await document.read()
    selfie_img = matcher.decode(selfie_bytes)
    doc_img = matcher.decode(doc_bytes)
    if selfie_img is None or doc_img is None:
        raise HTTPException(status_code=400, detail="Could not decode one or both images.")

    # 1) Document-type verification (Groq vision LLM).
    vc = app.state.vision.classify(doc_bytes, mime=document.content_type or "image/jpeg")
    doc_res = DocumentClassification(
        available=vc.get("available", False),
        is_identity_document=vc.get("is_identity_document"),
        document_type=vc.get("document_type"),
        confidence=vc.get("confidence"),
        extracted=vc.get("extracted", {}) or {},
        reason=vc.get("reason", ""),
    )
    # Document gate: only enforced when the classifier is available and succeeded.
    doc_ok = True
    doc_problem = None
    if doc_res.available and vc.get("ok"):
        if not doc_res.is_identity_document:
            doc_ok, doc_problem = False, "Uploaded file is not a valid identity document."
        elif expected_type and expected_type != "any" and doc_res.document_type != expected_type:
            doc_ok, doc_problem = False, (
                f"Expected a {expected_type} but the document looks like a "
                f"{doc_res.document_type or 'different document'}."
            )

    # 2) Liveness + 3) face match.
    live = matcher.liveness(selfie_img)
    m = matcher.match(selfie_img, doc_img)
    live_res = LivenessResult(live=live["live"], score=live["score"], reason=live["reason"],
                              metrics=live.get("metrics", {}))
    match_res = FaceMatchResult(
        match=m["match"], cosine=m["cosine"], faces_detected=m["faces_detected"],
        threshold=matcher.cosine_threshold, note=m["note"], disclaimer=_face_disclaimer(),
    )

    verified = bool(doc_ok and live_res.live and match_res.match)
    if not doc_ok:
        summary = doc_problem
    elif not live_res.live:
        summary = f"Liveness failed: {live_res.reason}"
    elif not match_res.match:
        summary = "Face does not match the document photo."
    else:
        dt = doc_res.document_type or "ID"
        summary = f"eKYC verified: genuine {dt} and live selfie matches the document photo."
    return EkycVerifyResult(
        verified=verified, document=doc_res, liveness=live_res, face_match=match_res,
        summary=summary, disclaimer=_face_disclaimer(),
    )


@app.post("/v1/kyc/document/classify", response_model=DocumentClassification)
async def classify_document(document: UploadFile = File(...)) -> DocumentClassification:
    """Vision-LLM document-type classification (is this a genuine ID, and which type)."""
    data = await document.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload.")
    vc = app.state.vision.classify(data, mime=document.content_type or "image/jpeg")
    return DocumentClassification(
        available=vc.get("available", False),
        is_identity_document=vc.get("is_identity_document"),
        document_type=vc.get("document_type"),
        confidence=vc.get("confidence"),
        extracted=vc.get("extracted", {}) or {},
        reason=vc.get("reason", ""),
    )


@app.get("/ekyc", response_class=HTMLResponse)
def ekyc_page() -> str:
    return (Path(__file__).parent / "ekyc.html").read_text(encoding="utf-8")
