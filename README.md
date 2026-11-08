# COBI V2 · Checkout Credit Copilot

COBI has two local workspaces. **Credit Review Workbench** preserves intake, evidence review, assessment, routing, officer actions, what-if scenarios, monitoring and JSON export for synthetic checkout cases. **Research Lab** publishes the UCI Taiwan credit-card default benchmark, including licensing, split, training curves, calibration, locked-test results and a checksummed model registry.

Checkout PD and actual expected loss require bank validation. The workbench uses versioned scenario assumptions and leaves every decision with a human reviewer. UCI probabilities are restricted to the UCI feature contract and next-payment-month outcome.

## Evidence AI Research · V3

The Evidence AI Research page compares CS V2, Logistic Regression, XGBoost and Deep Sets on controlled synthetic defects. It also presents a separate LayoutLMv3 receipt extraction pilot on CORD v2. The checkout shadow endpoint reports `EVIDENCE_AI_VALIDATION_BLOCKED` and returns null learned scores for existing checkout cases. Workbench decisions and the UCI 350 registry use the existing V2 path.

[V3 research protocol](docs/EVIDENCE_LEARNING_PROTOCOL_V3.md) · [Results and reproduction](reports/evidence-v3/RESULTS.md) · [Slide evidence](reports/evidence-v3/SLIDE_EVIDENCE.md).

## Run locally

From the repository root on Windows, use Python 3.13 and Node.js. In the API terminal:

```powershell
python -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -r backend/requirements.txt
& $python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In a separate terminal:

```powershell
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run dev
```

Open [the workbench](http://localhost:5173) or [the API documentation](http://localhost:8000/docs). The API seeds `backend/data/checkout_credit.sqlite` only if empty. To see the new DEMO-001 without changing your existing cases, set `COBI_DB_PATH` to a fresh SQLite path before startup, for example `data/processed/cobi-v2-demo.sqlite`. Existing inputs and audit events stay in the original database and new reads calculate V2 outputs. For rollback, back up the SQLite database before running a historical revision. The historical formula implementation and original regression cases are included.

`docker compose up --build` uses the existing local workbench services and mounts published research metadata/artifacts read-only. The ML training and prediction runtime uses the native Python environment below.

## Reproduce the experiment

In the repository root, after installing the backend dependencies:

```powershell
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -r ml/requirements.txt
& $python -m scripts.fetch_uci
& $python -m ml.split
& $python -m ml.train_pd --reproduce-locked --out data/processed/reproduction-v2
& $python -m scripts.make_figures
& $python -m scripts.route_sensitivity
& $python -m scripts.check_restart
```

The explicit replay writes a separate output directory and uses the same holdout. If working from a source-only snapshot without the canonical run directory, `python -m ml.train_pd` produces the canonical run. A pending request in Research Lab queues only the registered UCI protocol. The local operator starts it with that command after acquisition and split lock. UCI raw files and row-level outputs remain local. The [data manifest](data/manifest/uci350.yaml) records source and hashes. [Training details and reproduction](docs/TRAINING_AND_EVALUATION.md).

## Verify

```powershell
$python = ".\.venv\Scripts\python.exe"
$env:PYTHONPATH = Join-Path (Get-Location) "backend"
& $python -m pytest -q backend/tests ml/tests
npm.cmd --prefix frontend run build
```

The ML verification tests require acquired UCI data and the local split lock. The handoff pack's offline normalization test can also run when the pack is present. For browser E2E, start the API against a fresh, disposable `COBI_DB_PATH` and point Vite at it using `VITE_API_PROXY_TARGET` if the API uses a custom port.

```powershell
$env:COBI_E2E_URL = "http://localhost:5173"
node --test frontend/tests/workbench.e2e.mjs
```

Chrome is used by default. Set `COBI_E2E_CHROME` to a Chromium executable if needed. The browser test creates a synthetic case and records audit events in the test database.

## API surfaces

| Workspace | Endpoint |
|---|---|
| Workbench | `GET/POST /api/applications`, `GET /api/applications/{id}` |
| Assumptions and trace | `GET /api/assumptions`, `GET /api/assessments/{id}/explanation` |
| What-if | `POST /api/assessments/simulate` and the existing `POST /api/applications/{id}/simulate` |
| Human review | `POST /api/applications/{id}/review` and `POST /api/applications/{id}/revoke-consent` |
| Synthetic monitoring | `GET /api/metrics`, `GET /api/evaluation` and `GET /api/export` |
| Research | `GET /api/research/datasets`, `POST /api/research/experiments`, `GET /api/research/experiments/{id}` and artifact downloads |
| Model registry | `GET /api/research/models`, `GET /api/research/models/{id}` and `POST /api/research/models/{id}/predict` for a compatible UCI request with the local ML dependencies |

## Three-minute walkthrough

1. In **Applications**, open DEMO-001. A fresh V2 database shows VND 6m purchase, VND 5m principal, VND 1m own funds and VND 1.25m monthly payment over four months.
2. In **AI Assessment**, inspect evidence subscores, linear P25, both affordability constraints and the illustrative loss grid. **Decision Routing** compares feasible paths using assumed process costs. Record a reason in **Officer Review**.
3. In **What-if Simulator**, change income or debt and rerun. Check benchmark compatibility to see why checkout PD is unavailable. Switch to **Research Lab** to see the trained XGBoost benchmark, raw and calibrated results, intervals and artifact provenance.

[Scientific report](reports/final/RESULTS.md) · [Baseline audit](reports/baseline/AUDIT.md) · [Formula changelog](docs/FORMULA_CHANGELOG_V1_TO_V2.md) · [Data contracts](docs/DATA_CONTRACTS.md) · [Literature matrix](docs/LITERATURE_TO_DESIGN_MATRIX.md) · [Model card](docs/MODEL_CARD.md) · [Limitations](docs/LIMITATIONS.md).
