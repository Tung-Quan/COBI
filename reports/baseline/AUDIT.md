# Phase A · Current repository audit

Baseline commit `11352a6` on `main`. The V2 handoff pack was an existing untracked directory. The repository had no model registry, trained checkpoint, migration runner, or bank dataset.

```text
backend/app/         FastAPI routes, SQLite access, Pydantic requests, calculation engine
backend/data/        six synthetic seeds; local SQLite excluded from Git
backend/tests/       9 calculation tests and 8 API tests
frontend/src/        React workspace, case inbox, assessment, routing, review, simulator, monitoring
docs/                methodology, architecture, data dictionary, validation and demo script
COBI_V2_Agent_Upgrade_Pack/   handoff spec, acquisition/protocol/audit, manifest and loader tests
```

## Verified baseline

- Backend `python -m pytest -q` from `backend` · [17 passed](backend.log).
- Frontend `npm.cmd run build` · [TypeScript and Vite build passed](frontend.log). The baseline had no browser test suite.
- [Exact DEMO-001 calculation and routes](demo-001.json), obtained from the running V1 calculation code and seed.
- Dependencies were FastAPI/Pydantic/Uvicorn with SQLite and React/TypeScript/Vite/Tailwind. Startup created tables and append-only audit triggers directly. Case reads persisted the latest calculation and what-if calculations were temporary.
- Existing API surfaces included health, intake/list/detail, case simulation, human review, assumptions, metrics/evaluation and JSON export.

## Reference reconciliation

| Item | Status | Observed |
|---|---|---|
| V2 master, acquisition playbook, V2 research protocol, handoff audit and template | FOUND | Read alongside the existing methodology and demo script. |
| Original business presentation | FOUND | `Downloads/AI4Biz_Adudu_2026.pdf`, 11 pages. Slide 8 shows a 6m VND purchase, 5m loan, 1m own funds, eight months of history and an illustrative 1.1m installment. Slide 9 labels KPI figures as original targets. |
| Research Training Bundle, V1 protocol, extraction/routing studies and original Python demo/output | NOT_FOUND | Searched the workspace, visible artifact root, Downloads and names in the user's home and project drive. The V2 pack contains an audit describing the starter, but its training code and results were unavailable. |
| Mathematical methodology | DIFFERENT_VERSION | Tracked `docs/methodology.md` matches most V1 code. The slide and handoff examples have different transaction values and eight months of history. |
| P1 and P2 | FOUND | Four boolean-style flags, synthetic sources and reconciliation counts. No field timestamp validation or separate extraction confidence. |
| P3 and P4 | FOUND | Mean 12m, population SD 1,477,097.89 VND, CV 0.12309149, DTI 0.1078125, P25 11m by lower order statistic. History coverage 11/12 and CS 0.820938. |
| P5 | DIFFERENT_VERSION | Code used only a 35% DTI capacity. V1 principal 9.6m / 4 = 2.4m matched V1 seed. It differed from the original slide and from the V2 5m case. |
| P6 and P7 | FOUND | Anchored PD 0.039675 with CS in the score, LGD 0.45, EAD 6,666,600 VND, illustrative loss 119,023.81 VND. |
| P8 | FOUND | Fast track selected at assumed 42,000 VND; eligibility used synthetic PD cutoffs, evidence and affordability. |
| P9 and P10 | FOUND | Human actions with reasons, append-only audit triggers and hypothetical route cost comparison. No model/policy/fixture version or input digest in events. |

The business case states 1.8–4.6 working days and VND 380,000 per application. These are source case figures. This repository contains no independent measurements supporting them.
