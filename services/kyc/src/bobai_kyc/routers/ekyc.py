"""eKYC, liveness, face-match, and vision document-classification routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

from bobai_kyc.schemas import (
    DocumentClassification,
    EkycVerifyResult,
    FaceMatchResult,
    LivenessResult,
)

router = APIRouter(tags=["ekyc"])


@router.post("/v1/kyc/face/match", response_model=FaceMatchResult)
async def face_match(
    request: Request,
    selfie: UploadFile = File(...),
    document: UploadFile = File(...),
) -> FaceMatchResult:
    matcher = request.app.state.face
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


@router.post("/v1/kyc/liveness", response_model=LivenessResult)
async def liveness_check(request: Request, selfie: UploadFile = File(...)) -> LivenessResult:
    matcher = request.app.state.face
    if matcher is None:
        raise HTTPException(status_code=503, detail="Face models not available.")
    img = matcher.decode(await selfie.read())
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image.")
    r = matcher.liveness(img)
    return LivenessResult(live=r["live"], score=r["score"], reason=r["reason"],
                          metrics=r.get("metrics", {}))


@router.post("/v1/kyc/ekyc/verify", response_model=EkycVerifyResult)
async def ekyc_verify(
    request: Request,
    selfie: UploadFile = File(...),
    document: UploadFile = File(...),
    expected_type: str = Form("aadhaar"),
) -> EkycVerifyResult:
    """Full eKYC with vision document verification, passive liveness, and face match."""
    matcher = request.app.state.face
    if matcher is None:
        raise HTTPException(status_code=503, detail="Face models not available.")
    selfie_bytes = await selfie.read()
    doc_bytes = await document.read()
    selfie_img = matcher.decode(selfie_bytes)
    doc_img = matcher.decode(doc_bytes)
    if selfie_img is None or doc_img is None:
        raise HTTPException(status_code=400, detail="Could not decode one or both images.")

    vc = request.app.state.vision.classify(doc_bytes, mime=document.content_type or "image/jpeg")
    doc_res = DocumentClassification(
        available=vc.get("available", False),
        is_identity_document=vc.get("is_identity_document"),
        document_type=vc.get("document_type"),
        confidence=vc.get("confidence"),
        extracted=vc.get("extracted", {}) or {},
        reason=vc.get("reason", ""),
    )

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


@router.post("/v1/kyc/document/classify", response_model=DocumentClassification)
async def classify_document(request: Request, document: UploadFile = File(...)) -> DocumentClassification:
    """Vision-LLM document-type classification (is this a genuine ID, and which type)."""
    data = await document.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload.")
    vc = request.app.state.vision.classify(data, mime=document.content_type or "image/jpeg")
    return DocumentClassification(
        available=vc.get("available", False),
        is_identity_document=vc.get("is_identity_document"),
        document_type=vc.get("document_type"),
        confidence=vc.get("confidence"),
        extracted=vc.get("extracted", {}) or {},
        reason=vc.get("reason", ""),
    )


@router.get("/ekyc", response_class=HTMLResponse)
def ekyc_page() -> str:
    return (Path(__file__).resolve().parent.parent / "ekyc.html").read_text(encoding="utf-8")
