# COBI V3 evidence learning protocol

V3 is a separate document evidence study. The UCI 350 default model, its test partition, registry and published metrics remain the V2 credit-risk benchmark. Checkout CS remains the reproducible CS_V2 baseline. Evidence model outputs are advisory research values and cannot feed routing, approval, affordability or mandatory gate logic.

## Current implementation audit

| Surface | Owning implementation | V3 boundary |
|---|---|---|
| P1 consent, simulated identity, source access, funding, material failure and as-of validation | `backend/app/calculations.py::_mandatory_gates, _evidence_as_of` | All existing gates remain the source of truth. |
| P2 evidence schema and trace | `backend/app/schemas.py::Evidence, EvidenceSource` and `calculations.py::calculate_application` | V2 holds synthetic counts and provenance flags. They cannot stand in for labeled material defects. |
| P3–P5 statistics, CS and capacity | `calculations.py::financial_features, confidence_score, affordability, payment` | Keep 0.30/0.30/0.20/0.20 and exp(−age/40). Fit no policy weights against bank outcomes. |
| P6–P8 risk, EL and eligibility | `calculations.py::demo_risk_score, expected_loss, route_application` | Synthetic risk and eligibility stay on the V2 path. |
| P9–P10 action reasons, persistence and simulation | `backend/app/main.py::_record_review, stop_scoring, simulate, metrics` and `db.py::append_audit_event` | Shadow endpoint is read-only and independent from audit actions and decisions. |
| UI and regression coverage | `frontend/src/App.tsx`, `ResearchLab.tsx`, `backend/tests/test_v2_workbench.py`, `test_api.py` and `frontend/tests/workbench.e2e.mjs` | Evidence AI gets a distinct screen. Existing flows remain available. |

## Label definitions and independent verification

| Target | Unit and definition | Independent evidence and reviewer instructions |
|---|---|---|
| Field extraction error | Field on a document. Extracted normalized value/span differs from an independently transcribed source or a mandatory present value was omitted. | Two blind transcribers inspect the original, record page, region, unit and locale, and adjudicate disagreements. A clear source can itself contain a false value. |
| Cross-source inconsistency | Comparable field on a pair of documents at the same effective period and subject. Difference exceeds a predeclared unit/rounding tolerance. | Verify provenance and match applicant, period, denomination and business meaning first. Record both document keys and evidence references. Non-comparable values remain unknown. |
| Material evidence error | Document with a validated defect that would materially change the affordability input, eligible review or other prespecified decision-relevant fact under a frozen policy. | Two qualified reviewers apply a versioned materiality rubric to reconciled source facts, blinded to CS, model, route and each other. Independently verify consequences using policy, without substituting the policy's prior action as truth. |
| Verification required | Need for additional independent evidence under the frozen policy, conditional on what was available at decision time. | Reviewers independently document the missing check and allowed verification path. Existing mandatory verification remains binding. A label of unavailable stays masked. |

Each record stores stable de-identified customer, case, template and document keys, SHA-256, source, timestamp, controlled evidence references and authorization. Require distinct reviewers and an independent adjudicator for unresolved disagreement. Preserve review history and reasons. Compute agreement before adjudication, audit reviewer assignment and assess unknown-rate differences by source/template. Use local restricted data and approved retention. `evidence_ai/annotations.py` validates the contract and enforces label availability by cutoff. CORD and DocILE do not carry these four bank defect labels.

## Frozen technical experiment

`evidence_ai/protocol.json` fixes synthetic data seed 731, chronological customer-disjoint train/validation/calibration/test allocation, model seeds 13/29/43, model search, 90% critical recall target on calibration and 300 paired customer-cluster bootstrap draws. Each customer's cases stay together. A late-only membership tag identifies a test subgroup. It does not change the generation law. A separate challenge applies new observed text formatting and a confidence shift to independent synthetic groups. Dates and groups are generated. These controls test the protocol and do not establish bank drift.

The generator separates known canonical values, document content and observed extracted values. Controlled corruptions and independent programmatic truth determine technical labels. Model features can use only the observed evidence layer. Gold labels, internal corruption identifiers, customer IDs, templates and period timestamps are excluded from feature matrices. Historical CS components are observable scenario features and are excluded together in one ablation. Real reviewer/adjudication outcomes are unavailable.

M0 ranks by 1−CS_V2, M1 uses regularized Logistic Regression, M2 uses XGBoost and M3 uses masked Deep Sets with a material-document head plus field extraction heads. M0 maps its score to research probabilities on calibration rather than interpreting CS as a probability. Neural optimization uses AdamW and variable-length padded batches with masks. Hyperparameter selection uses mean validation document log loss. Record loss, gradient norm before updates, rate, selected checkpoint digest and stopping per epoch. Evaluate frozen ablations without retuning.

Fit sigmoid calibration separately, select the highest document threshold attaining ≥90% critical recall on the calibration set, and freeze before test scoring. Document metrics include critical recall and FNR, AP, Brier and log loss. Case workload is the fraction of cases with at least one document flagged at that threshold. Report document/field metrics, counts and grouped intervals, and stratify test results by seen versus late-only templates and early/late test dates. Bootstrap uses customers as units and conditions on fitted models, checkpoints and thresholds. Multiple seeds assess optimizer variation, not domain uncertainty.

For document features `xᵢ` and validity mask `mᵢ`, Deep Sets pools `h = Σᵢ mᵢφ(xᵢ)/Σᵢ mᵢ`. Each document's representation `ρ([φ(xᵢ), h])` feeds one material error logit and three field extraction logits. The objective is masked document BCE plus `0.35 ×` masked field BCE. Permuting document order preserves the context and permutes the outputs. A field without an eligible label contributes no loss. The calibrated probability map is `σ(a + b·logit(p_raw))`, fitted after selection. The operating threshold is a research setting that leaves mandatory workbench checks intact.

Status remains `EVIDENCE_AI_VALIDATION_BLOCKED` for material bank errors. Models in this run are `SYNTHETIC_TECHNICAL_ONLY`. No Set Transformer result is claimed. The controlled generator is insufficient evidence of real document diversity.
