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
    Product,
    RequirementSet,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.kb = KnowledgeBase.from_file(settings.kb_path)
    app.state.ocr = TesseractEngine()
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
