"""Document-requirements and document-fraud routes."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from bobai_kyc.fraud import analyze_document
from bobai_kyc.matcher import check
from bobai_kyc.schemas import (
    CheckRequest,
    CheckResult,
    ClaimedFields,
    DocumentFraudReport,
    DocumentType,
    Product,
    RequirementSet,
)

router = APIRouter(prefix="/v1/kyc", tags=["documents"])


@router.get("/products", response_model=list[Product])
def products(request: Request) -> list[Product]:
    return request.app.state.kb.list_products()


@router.get("/requirements", response_model=RequirementSet)
def requirements(
    request: Request, product_id: str, profile: str | None = None, constitution: str | None = None
) -> RequirementSet:
    try:
        return request.app.state.kb.requirements(product_id, profile=profile, constitution=constitution)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown product '{product_id}'.")


@router.post("/check", response_model=CheckResult)
def check_documents(body: CheckRequest, request: Request) -> CheckResult:
    try:
        req = request.app.state.kb.requirements(
            body.product_id, profile=body.profile, constitution=body.constitution
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown product '{body.product_id}'.")
    return check(req, body.submitted)


@router.post("/document/analyze", response_model=DocumentFraudReport)
async def analyze_doc(
    request: Request,
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
    engine = request.app.state.ocr if run_ocr else None
    return analyze_document(image_bytes, document_type, claimed, ocr_engine=engine)
