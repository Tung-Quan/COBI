# Checkout Credit Copilot MVP

A local, bank-owned review workflow prototype for synthetic checkout installment cases. It shows the evidence behind each calculation, enforces mandatory input gates, compares eligible review routes, and records simulated officer actions. It does not approve real loans.

## What is included

- React, TypeScript, Vite and Tailwind operations dashboard.
- FastAPI and Pydantic API with SQLite application and append-only audit tables.
- Deterministic Python calculation engine for evidence confidence, income features, affordability, an explicitly uncalibrated logistic risk demonstration, expected loss, and policy constrained route selection.
- Six synthetic cases, including the supplied DEMO-001 expected values and five guardrail scenarios.
- Case intake, assessment, routing, officer review, a temporary what-if simulator, synthetic monitoring and JSON export.
- REST endpoints documented by FastAPI at `/docs`.

## Reference inputs and fidelity

The checkout opened without tracked files or branches. The following required references were not present in the workspace or the provided attachment folder:

- `AI4Biz_Adudu_2026.pdf`
- `checkout_credit_pipeline_demo.py`
- `checkout_credit_demo_output.json`
- `Checkout_Credit_MVP_Agent_Prompt.md`

The DEMO-001 anchor values in the implementation brief are reproduced in the seed fixture. Since the reference code is missing, the demo risk slopes, route costs, maximum DTI and route thresholds are clearly labelled as illustrative and are not claimed to match a bank or the prototype. The risk score is labelled `DEMO_RISK_SCORE_NOT_CALIBRATED`; no model training or calibration is claimed. Replace those values from the reference prototype before using its baseline as a comparison.

## Run locally on Windows PowerShell

Open two terminals from the repository root.

Terminal 1, backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API seeds `backend/data/checkout_credit.sqlite` on first start. The source seed file is `backend/data/seed_applications.json`.

Terminal 2, frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. API documentation is at <http://localhost:8000/docs>.

## Run with Docker Compose

From the repository root:

```powershell
docker compose up --build
```

Open <http://localhost:5173>. Stop the services with `Ctrl+C`, then run `docker compose down`. The SQLite file persists in `backend/data/`.

## Verify the implementation

Backend acceptance and integration tests:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pytest
```

Frontend type check and production bundle:

```powershell
cd frontend
npm install
npm run build
```

The verification log and any environmental limits are recorded in `docs/validation.md`.

## Main API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Local API status |
| `GET` | `/api/applications` | Searchable synthetic queue |
| `POST` | `/api/applications` | Validate and receive a synthetic case |
| `GET` | `/api/applications/{id}` | Case, calculations, routing and audit history |
| `POST` | `/api/applications/{id}/simulate` | Recalculate temporary what-if inputs |
| `POST` | `/api/applications/{id}/review` | Append a human review action with a reason |
| `GET` | `/api/metrics` | Synthetic operational snapshot and baseline cost comparison |
| `GET` | `/api/evaluation` | Per case evaluation log; explicitly not measured performance |
| `GET` | `/api/export` | JSON export of cases, calculations and audit history |
| `GET` | `/api/assumptions` | Configurable formula and assumption values |

## Boundaries

- All applicants, merchants, financial history and operational metrics are synthetic.
- Consent, simulated identity, source permission and funding reconciliation are mandatory scoring gates. If one fails, assessment scores are not computed and only `HOLD_FOR_HUMAN_HANDLING` is eligible.
- A lower demo PD cannot make a failed affordability or evidence gate eligible for fast-track.
- Officer actions require a reason. A changed route must be eligible; it is audited. The API exposes no loan approval action.
- Route costs, eligibility thresholds, DTI cap, LGD, EAD and demo risk coefficients are explicit configurable assumptions, not validated bank values.
- The current demo score is an anchored logistic calculation using the expected DEMO-001 PD from the prompt. Its demonstration slopes are not the missing prototype's coefficients.
- There are no external paid API requirements. Google Fonts are optional visual enhancements; local fallback fonts remain available.

## Documentation

- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data-dictionary.md)
- [Mathematical methodology and assumptions](docs/methodology.md)
- [Three minute demo script](docs/demo-script.md)
- [Validation record, limitations and next validation plan](docs/validation.md)
