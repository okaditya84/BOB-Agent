# Bank of Baroda — Account, Deposit & Loan Documentation Reference
### Compiled for Hackathon Use (Document-Simplification Tool)

> **Sources:** Bank of Baroda's official website (bankofbaroda.bank.in — personal banking, business banking, NRI banking, "Banking Mantra" articles) and BOB's official KYC/OVD document list circular.
>
> **Why this matters for your project:** The single biggest "documentation problem" customers face is not knowing (a) which OVD + address proof combination is acceptable, and (b) which *extra* documents apply to their specific profile (salaried/self-employed/NRI/senior citizen/minor/business type). This guide is structured so your app can show: **Core KYC (always required) + Product-specific extras (conditional on user profile)**.
>
> **Disclaimer:** Document/eligibility rules are revised periodically via RBI/BOB circulars. Build a "Last verified: [date]" tag into your app and link out to the relevant official BOB page; advise users to confirm at their home branch before final submission.

---

## PART 0 — The Foundation: KYC / OVD Documents
*(Required for almost every product below — your app's "core checklist")*

### A. Officially Valid Documents (OVD) for Identity AND Address — pick ANY ONE
1. Passport
2. Driving Licence (with photo)
3. Aadhaar Card (proof of possession of Aadhaar number)
4. Voter's ID Card (Election Commission of India)
5. NREGA Job Card (signed by a State Government officer)
6. Letter issued by the National Population Register (NPR), containing Name & Address

### B. Mandatory Tax-ID Document
- PAN Card **OR** Form 60 (declaration form, with reason for not having PAN) — mandatory for every account/deposit/loan as per RBI norms

### C. "Deemed OVD" — needed only if the chosen OVD above does NOT show the customer's current address (pick ANY ONE)
- Utility bill — electricity / telephone / postpaid mobile / piped gas (not older than 2 months)
- Property or Municipal Tax receipt (latest)
- Pension Payment Order (PPO) issued by Govt departments/PSUs (if it carries the address)
- Allotment letter / registered leave-and-licence agreement from an employer (Govt/PSU/listed company)
- For foreign nationals: document from a foreign Govt department, or a letter from a Foreign Embassy/Mission in India

### D. Universal Extras
- 2 recent passport-size colour photographs
- Duly filled & signed Account/Application Opening Form (AOF)
- Specimen signature

### E. Special case — Minors
- Birth Certificate (issued by Gram Panchayat / NAC / Municipal Corporation)
- Guardian's full KYC (Parts A–D above)
- Proof of relationship/guardianship
- Recent photo of the minor (if old enough)

---

## PART 1 — SAVINGS ACCOUNTS

**Common documents for every sub-type:** AOF + Part 0 (A–D) KYC + initial deposit (cash/cheque/DD, unless zero-balance variant)

| Sub-type | Purpose / Who it's for | Documents ADDITIONAL to Part 0 |
|---|---|---|
| **bob Super Savings Account** | Premium account — auto-sweep, locker discounts, free DD | None — standard KYC only |
| **Basic Savings Bank Deposit Account (BSBDA)** | Zero-balance, financial-inclusion account | None — standard KYC (RBI allows relaxed/small-account KYC) |
| **bob Advantage Savings Account** | Low minimum-balance account with added benefits | None — standard KYC only |
| **bob Lite Savings Account** | Entry-level account with RuPay Platinum debit card | None — standard KYC only |
| **Salary / Salary Advantage Account** | Opened via employer salary tie-up | Salary certificate/letter from employer, Employee ID card, employer's payroll/authorization letter |
| **Senior Citizen Savings Account** | 60+ benefits (higher FD rates, priority service) | Age proof showing DOB — Passport/PAN/Driving Licence/Voter ID/Birth Certificate |
| **Minor's Savings Account** | For individuals under 18 | See Part 0-E (Birth Certificate + Guardian's KYC + relationship proof) |
| **Savings Account for Central/State Govt Employees** | Tailored for government staff | Government Employee ID card / appointment letter |
| **NRE Savings Account** (NRI) | Holds foreign income in INR; fully repatriable | Passport + valid visa/residence permit, Overseas address proof (utility bill/bank statement/driving licence of resident country), PIO/OCI card (if applicable), recent photo, employment contract/work permit/student ID, PAN or Form 60 |
| **NRO Savings Account** (NRI) | Manages India-sourced income (rent, dividend, pension) | Same as NRE above + FEMA declaration of source of funds |

---

## PART 2 — CURRENT ACCOUNTS

**Common documents for every sub-type:** Current Account AOF + Part 0 KYC of proprietor/all partners/all directors/authorised signatories + photographs of all signatories + FATCA/CRS self-certification

### Sub-types
| Sub-type | Best for |
|---|---|
| **Baroda Small Business Current Account (BSBCA)** | Small traders/merchants — "Pay as you use" model |
| **Baroda Advantage Current Account** | Small & medium businesses — low Quarterly Average Balance, free net banking |
| **bob Premium Current Account (BPCA)** | Medium-to-large businesses |
| **bob Premium Current Account – Privilege** | Large enterprises — unlimited transactions, absolute liquidity |

### Additional documents — by Business Constitution (entity type)
| Constitution | Documents required (in addition to the common list) |
|---|---|
| **Sole Proprietorship** | Proof of business name/existence — any 2 of: GST registration, Shop & Establishment certificate, Sales/Income-Tax returns in proprietor's name, CST/VAT certificate, IEC code, licence from a statutory professional body, utility bill in business name |
| **Partnership Firm** | Registered Partnership Deed (or certified copy), PAN of the firm, KYC of all partners, authorisation letter naming operating signatories, one business-proof document (as above) in firm's name |
| **Private/Public Limited Company** | Certificate of Incorporation, MOA & AOA, Board Resolution authorising account opening + signatories, PAN of company, KYC of all directors/signatories, list of directors |
| **LLP** | Certificate of Incorporation (LLP), LLP Agreement, PAN of LLP, KYC of designated partners, Partner/Board resolution |
| **HUF** | HUF declaration/deed, PAN of HUF, KYC of Karta + adult co-parceners |
| **Trust / Society / Association** | Trust Deed / Registration Certificate, PAN of entity, list of trustees/managing-committee with KYC, resolution authorising account opening |

---

## PART 3 — TERM DEPOSITS (FD, RD, TAX-SAVER & NRI DEPOSITS)

**Common documents:** Term/RD application form (or online request, if existing KYC-compliant customer) + Part 0 KYC (waived for existing customers opening via net/mobile banking) + PAN/Form 60 + 2 photographs (new customers) + nomination form

| Sub-type | Key facts | Documents ADDITIONAL to common list |
|---|---|---|
| **Regular Fixed Deposit** | Tenure 7 days–10 years; premature withdrawal & loan-against-FD allowed | None |
| **Baroda Tax Saving Fixed Deposit** (RIRD / MIP / QIP variants) | 5-year lock-in; Section 80C benefit up to ₹1.5 lakh; no premature withdrawal/loan | **PAN is mandatory** (Form 60 not accepted for this product) |
| **Recurring Deposit (RD)** | Tenure 6 months–10 years; monthly instalments from ₹100 | Standing-instruction/auto-debit mandate for the monthly instalment |
| **Senior Citizen FD** | ~0.50% additional interest | Age proof (60+) |
| **Capital Gain Account Scheme (CGAS)** | Tax exemption on capital gains; savings + term-deposit options | Copy of sale deed of the asset transferred, declaration as per IT Rule 1962, PAN |
| **NRE / NRO / FCNR Fixed Deposits** | For NRIs; FCNR held in foreign currency | Passport + visa copy, overseas address proof, PIO/OCI card (if applicable), FIRC/inward-remittance proof or source-of-funds declaration, FEMA declaration |

---

## PART 4 — LOANS

### 4.1 Home Loan
**Common (all applicants):**
- Home Loan application form, duly filled & signed, with photographs
- Identity proof: PAN (mandatory if loan > ₹10 lakh) / Aadhaar / Voter ID / Driving Licence / Passport
- Address proof: Aadhaar / Driving Licence / Voter ID / Passport / Ration Card / Registered Rent Agreement
- Last 6 months' bank account statement
- Processing-fee cheque

**Salaried — additional:**
- Last 6 months' salary slips
- Form 16 / IT Returns for last 2 years
- Employment/appointment/confirmation/increment letter (proves employment duration)
- Bank statement showing salary credit
- Investment proofs (FDs, shares), if used to support income

**Self-employed — additional:**
- IT Returns for last 3 years (individual & business)
- Audited Balance Sheet & Profit-and-Loss statements (last 2–3 years), CA-certified
- Business proof: GST / Shop Act / Trade licence / registration certificate
- Business address proof
- Partnership deed / Certificate of Incorporation (as applicable)
- Business bank account statement

**Property documents (everyone):**
- Allotment letter / registered Sale Deed / Agreement to Sell (builder or seller)
- NOC from society/builder
- Approved/sanctioned building plan
- Chain-of-title documents / Encumbrance Certificate (typically last 13–30 years)
- Property tax receipts
- Possession letter / Share certificate (co-op society, if applicable)

**NRI applicants — additional:**
- Valid passport & visa copy
- Work permit / employment contract / appointment letter
- Overseas salary slips (last 6 months) + employer ID
- Overseas bank statements (last 6 months)
- IT Returns — India & overseas (last 2 years)
- Power of Attorney (POA) to a representative in India
- Continuous Discharge Certificate (CDC) — for seafarers, if applicable
- Overseas credit-bureau report, if available

**Pensioners — additional:**
- Pension Payment Order (PPO)
- Proof that pension will continue through the loan tenure
- 3 months' bank statement showing pension credit

---

### 4.2 Personal Loan
> ⚠️ Per BOB's official FAQ: **NRIs are not eligible** for BOB Personal Loans.

**Salaried applicants:**
- Identity proof: Aadhaar / PAN / Voter ID / Passport / Driving Licence
- Address proof: Driving Licence / Aadhaar / utility bills / bank statement
- Income proof: Form 16, last 3 months' salary slips/salary certificate, last 6 months' bank statement (salary account)
- Latest colour passport-size photograph
- Duly filled application form

**Self-employed applicants — additional/instead:**
- Proof of business existence: GST registration / trade licence / business registration certificate
- ITR with income computation
- Business bank statements (6 months)

**Pensioners:**
- Identity proof: Aadhaar / PAN / Voter ID / Passport / Driving Licence
- Address proof: PAN / Driving Licence / utility bills / bank statement
- Income proof: Pension document / PPO / bank account statements
- Photograph

---

### 4.3 Vehicle Loan (New/Used Car, Two-Wheeler)
**Eligibility note:** Applicant ≥ 21 yrs, co-applicant ≥ 18 yrs; (age + repayment tenure) ≤ 70 yrs

**Documents:**
- Duly filled application form
- Identity proof: PAN / Aadhaar / Driving Licence / Passport / Voter ID
- Age proof: Passport / Ration Card / Aadhaar / PAN / Birth Certificate
- Address proof (Part 0 list)
- Income proof:
  - *Salaried:* last 3 months' salary slips, Form 16, 6 months' bank statement
  - *Self-employed:* ITR for 2–3 years, business proof, bank statements
- Photographs
- Vehicle quotation / proforma invoice from dealer
- **Used vehicles only:** RC book, insurance copy, valuation/inspection report

---

### 4.4 Education Loan

**I. Student-applicant:**
- KYC (Part 0): age proof, photo ID, address proof
- Mark sheets — 10th, 12th, graduation (as applicable to course level)
- Entrance exam scorecard (CAT/CMAT/JEE/NEET/CET/GMAT/GRE/TOEFL/IELTS, etc.)
- Proof of admission: Offer/Admission letter (conditional letter accepted for study abroad)
- Passport + visa copy (mandatory for studies abroad)
- Fee structure/schedule of expenses from the institution
- Scholarship letter, if any

**II. Co-applicant/Guarantor** (normally parent/guardian; for married applicants — spouse or parent-in-law):
- Full KYC (Part 0) + photographs

**III. Income proof — salaried co-applicant/guarantor:**
- Last 3 months' salary slips or salary certificate
- Form 16 & IT Returns (acknowledged)
- Last 6 months' bank statement (salary account)

**IV. Income proof — self-employed co-applicant/guarantor:**
- Business proof/registration
- IT Returns (last 2–3 years) with income computation
- CA-certified Balance Sheet & P&L
- Last 6 months' bank statements

**V. Collateral/property documents** (typically required for loans above ~₹7.5 lakh):
- Title deed and ownership documents of the property offered

**VI. Other:**
- Net-worth statement of co-applicant/guarantor
- Vidya Lakshmi Portal application reference (BOB education loans are routed via this Govt portal)
- Margin-money proof, if applicable
- Signed Education Loan application form + bank's checklist

---

### 4.5 Gold Loan
**Documents:**
- Duly filled Gold Loan application form
- Identity proof: PAN / Passport / Voter ID / Driving Licence / Aadhaar
- Address proof: Aadhaar / Voter ID / Passport / recent utility bill / ration card
- 2 recent passport-size photographs
- Self-declaration of ownership of the gold ornaments/coins offered as security

**Agri Gold Loan — additional:**
- Land record/ownership documents (or tenancy proof) showing agricultural land holding

> 💡 Income proof is **generally NOT required** for standard retail gold loans — one of its key advantages.

---

### 4.6 Mortgage Loan / Loan Against Property (LAP)
**Documents:**
- Application form with photo & signature
- Identity proof: Aadhaar / PAN / Passport / Voter ID
- Address proof — residence AND office: Aadhaar / Voter ID / Driving Licence / utility bill
- Income proof:
  - *Salaried:* last 6 months' salary slips, Form 16
  - *Self-employed:* ITR (last 3 years), audited Balance Sheet & P&L
- Last 6 months' bank statements
- Property documents: original title deeds with complete chain of ownership, latest property-tax/maintenance receipts, NOC/permission for mortgage from society or development authority, approved building plan

**NRI applicants — additional:**
- Passport & visa copy
- Overseas salary certificate/income statement (attested by BOB's foreign office or competent local authority)
- Biodata — education, job history, profession
- Employment contract

---

### 4.7 MSME / Business Loans (incl. Mudra Loan)
**Schemes covered:** PM Mudra Yojana — Shishu (≤₹50,000), Kishore (₹50,000–5 lakh), Tarun (₹5–10 lakh), Tarun Plus (₹10–20 lakh); Digital Mudra Loan; general MSME Term Loan/Working Capital; CGTMSE-backed loans; Stand-Up India; sector schemes (textiles, healthcare, solar, etc.)

**Common documents:**
- Duly filled application form with photographs
- Identity proof: Aadhaar / PAN / Driving Licence / Passport / Voter ID — of all applicants/partners/directors
- Residence proof: latest utility bills / Aadhaar / Voter ID / Passport / bank statement — of all applicants
- Business proof: Udyam/Udyog Aadhaar registration, GST registration, trade licence, shop & establishment certificate (as applicable)
- Last 2–3 years' ITR with income computation, audited Balance Sheet & P&L
- Last 6 months' business bank statements
- Proof of business continuity (ITR/trade licence/sales-tax certificate)
- Entity-specific docs: Partnership deed, OR Certificate of Incorporation + MOA/AOA + Board resolution + list of directors (companies)
- Collateral/property documents (lease/title deed), where security is offered
- Projected financials (next 1–2 years) for working-capital/term-loan assessment

**Digital Mudra Loan (≤ ₹50,000) — specific:**
- Last 6 months' bank statement (downloaded digitally via net/mobile banking/email)
- Business registration details (if applicable)
- KYC of business and proprietor
- Details of associate concerns and existing loans

---

### 4.8 Agriculture Loan / Kisan Credit Card (Baroda Kisan Credit Card – BKCC)
**Documents:**
- Duly filled KCC application form
- Identity proof: Aadhaar / Voter ID / Driving Licence / Passport
- Address proof (Part 0 list)
- Land-holding document: Revenue-authority-certified land record or Online Land Record extract (ownership proof, OR lease/tenancy agreement for tenant farmers/share-croppers)
- Passport-size photographs
- Existing loan/no-dues details, if any

**Animal Husbandry & Fisheries KCC — additional:**
- Same KYC as above + proof/details of the activity (dairy unit, poultry shed, fishery, etc.)
- Collateral documents (land mortgage/charge) — mandatory if loan amount exceeds ₹1.6 lakh

---

## PART 5 — OTHER PRODUCTS

### Public Provident Fund (PPF) Account
- AOF for PPF
- Aadhaar Card **AND** PAN/Form 60 — both mandatory (per Govt Savings Promotion Rules, 2023)
- Identity/address proof — Part 0 OVD list
- Photographs
- Nomination form
- **Not eligible:** NRIs and HUFs cannot open a PPF account; joint accounts not allowed

### NRI Banking — Quick Overview
| Account type | Purpose |
|---|---|
| **NRE (Non-Resident External)** | Park foreign income in INR; fully repatriable |
| **NRO (Non-Resident Ordinary)** | Manage India-sourced income (rent, dividends, pension); repatriation capped (~USD 1 million/year) |
| **FCNR (Foreign Currency Non-Resident)** | Hold deposits in foreign currency (USD, GBP, EUR, AUD, CAD, etc.) |

All three are available as savings/current/term-deposit variants and use the documents listed under "NRE/NRO Savings Account" (Part 1) plus product-specific FEMA declarations.

---

## Source Pages (Bank of Baroda official site)
- `bankofbaroda.bank.in/personal-banking/accounts/saving-accounts` (+ sub-pages for each variant)
- `bankofbaroda.bank.in/personal-banking/accounts/current-accounts` (+ Premium/Advantage sub-pages)
- `bankofbaroda.bank.in/personal-banking/accounts/term-deposit/fixed-deposit/tax-saving-fixed-deposit`
- `bankofbaroda.bank.in/loans/vehicle-loan`, `/loans/education-loan`, `/loans/gold-loan`
- `bankofbaroda.bank.in/business-banking/msme-banking` (+ Digital Mudra Loan, PMMY pages)
- `bankofbaroda.bank.in/business-banking/rural-and-agri/loans-and-advances/baroda-kisan-credit-card`
- `bankofbaroda.bank.in/banking-mantra/loans-borrowings/articles/` — *documents-required-for-home-loan*, *documents-required-for-personal-loan*, *documents-required-for-education-loan*, *documents-required-to-get-a-car-loan*, *documents-required-for-loan-against-property-a-complete-checklist*, *what-are-the-gold-loan-eligibility-criteria*
- `bankofbaroda.bank.in/writereaddata/images/pdf/List-Of-Valid-KYC-Documents-For-Account-Opening-01-07-2019.pdf` (official KYC/OVD circular)
- `bankofbaroda.bank.in/nri-banking/products-services/accounts/` (NRE/NRO pages)
- `bankofbaroda.bank.in/accounts/baroda-public-provident-fund`
- `bankofbaroda.bank.in/banking-mantra/savings/articles/nri-account-opening-documents-guide`
