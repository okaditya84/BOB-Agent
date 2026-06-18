# BOBAI — KYC Service

Document-requirements resolver over the BoB knowledge base (`data/bob_documents_data.json`),
plus (upcoming) onboarding-fraud and live eKYC face-match modules.

## Run

```bash
uv sync --extra dev
uv run uvicorn bobai_kyc.main:app --reload --port 8002
uv run pytest
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/kyc/products` | List every applyable BoB product (discovered dynamically from the KB) |
| GET | `/v1/kyc/requirements?product_id=&profile=&constitution=` | Full document checklist for a product + applicant profile |
| POST | `/v1/kyc/check` | Check a list of submitted documents → satisfied / missing / completeness |

The resolver is **schema-driven**: products, profiles, constitutions and document
lists all come from the JSON. Adding a product to the KB surfaces it with no code change.

Roadmap (same service): document tamper detection (ELA), OCR field cross-check, and
seamless live eKYC with age-invariant face matching against the Aadhaar photo.
