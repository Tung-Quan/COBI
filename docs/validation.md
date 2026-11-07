# Validation record and limitations

## Verification status

This file is updated after the implementation commands are run. It records what was verified in this workspace, not a claim of bank acceptance.

| Check | Result |
|---|---|
| `python -m pytest -q` | Passed: 17 tests. One Starlette/AnyIO deprecation warning from the test client. |
| `npm run build` | Passed: TypeScript check and Vite production build. |
| `docker compose config` | Passed. |
| Docker Compose image build and startup | Not completed: build stalled at the container's `npm ci`; the Compose process was stopped and no Compose services were left running. |
| DEMO-001 numerical regression | Passed: mean 12,000,000 VND; CS 0.820938; PD demo 0.039675; capacity 2,906,250 VND/month; EL approximately 119,024 VND; fast-track candidate. |
| Browser walkthrough | Passed with local FastAPI/Vite: dashboard, application evidence/history, assessment, routing, changed-income simulator, consent-blocked simulator, and monitoring/evaluation log rendered. No console errors remained after adding the favicon. |
| Audit actions and JSON export | API integration tests passed for reason validation, eligible route override, append-only event history and JSON/evaluation output. |

## Known limitations

- The original PDF, prototype Python file, baseline JSON and detailed markdown specification were not available in the checkout, attachments, or configured remote branches. Exact prototype coefficients, cost assumptions and the business case have not been independently reconstructed.
- DEMO-001's expected values are anchored from the user supplied implementation prompt. The demo logistic slopes and all review policy values are explicitly illustrative. The synthetic PD is not trained, calibrated, validated, or a probability suitable for underwriting.
- The seed cases are fixtures, not applicants or repayment histories. No model performance metrics or real processing time/cost measurements exist.
- SQLite triggers prevent routine updates/deletes to audit rows, but this local single-file database is not tamper-proof storage against an administrator who can replace the file or drop triggers.
- No production identity checks, consent ledger, open banking, payroll verification, merchant integrations, encryption/key management, authentication/authorization, operational logging, or privacy retention controls are included.
- The confidence consistency and source verification counts are synthetic input fields. Live evidence normalization, duplicate handling, reconciliation tolerances and dispute workflows need source contracts and independent design review.
- “Fast-track candidate” is only a route label. Every case still requires a credit officer; the UI and API cannot approve a loan.
- Google Fonts are fetched from their public stylesheet URL when network access is available. The interface includes local fallback fonts.
- Docker Compose syntax was validated, but an end-to-end container build/startup remains unverified because `npm ci` inside the container stalled in this environment. Native local frontend/backend commands were verified.

## Future validation plan

1. Supply the referenced presentation, prototype, numerical output and detailed specification; compare every coefficient, intermediate result, route gate and route cost against those sources.
2. Obtain bank credit policy owners' approval for consent, identity, source, reconciliation and affordability rules before connecting any live data.
3. Define consented data schemas and provenance, missingness, transaction categorization, source recency, currency and reconciliation standards with data owners.
4. Build an independently governed training and validation dataset with outcomes, observation windows, bias/fairness review, leakage controls, out-of-time holdout, calibration analysis and documented monitoring thresholds.
5. Validate LGD/EAD definitions, expected-loss use, route costs and human capacity using bank-owned portfolio and operations data; label actual and hypothetical results separately.
6. Add authenticated roles, least privilege, encryption, secure audit retention, threat modeling, privacy review, observability, backups and incident procedures before any non-synthetic deployment.
7. Run a shadow pilot with officer feedback and no automated approval. Measure accuracy, calibration, affordability override rates, evidence requests, processing time, cost and adverse impact before a controlled product decision.
