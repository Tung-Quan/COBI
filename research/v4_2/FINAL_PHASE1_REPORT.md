# COBI V4.2 — Final Phase 1 Report

**Final status:** `PHASE1_COMPLETE_PHASE2_BLOCKED`  
**Validation status:** `EVIDENCE_AI_VALIDATION_BLOCKED`  
**Project:** `C:\disk D\COBI` — `main` at `7f5eff1e46a8f0c03a36a11d6892231bf4927182`  
**Date:** 2026-11-11

## Decision

The Phase 1 documentation and reproducibility package is complete for work supportable from the existing repository and public primary sources. Phase 2 is **not ready**. Release-owner provenance is unresolved for the two requested checksum mismatches; the committed V4.1 manifest also contains two stale same-snapshot source digests. The independent benchmark, D1.1 adjudication, risk policy and independent second literature screener are not available. These blockers are explicitly recorded rather than treated as passed.

No model was trained, Generator C was not rescored, thresholds were not changed, pending gold labels were not approved, and checkout decision logic was not changed.

## Phase 1 research record

- **Repository and release baseline:** source map, baseline audit and separate release-integrity reconciliation document the V4, V4.1 and current worktree snapshots. The checksum guard remains intact.
- **D1.1:** 200 stale-as-current observations; 100 candidate omissions (60/15/15/10). A reviewer packet and 100-row decision sheet are prepared. All decisions remain pending; original gold is unchanged.
- **Literature and novelty:** the scoped search protocol and first-pass screening log record 28 entries (26 unique studies/resources plus two explicit version/duplicate views). Close overlaps include FinBalance, FinAuditing, FinED-Bench, FinDVer, FinVerBench, RFC-Bench, When FEVER Meets Finance, TempFinRAG, HC-RAG/Multi-Doc-2025, FinFIRST, EvidenceLens and FinAgent. Broad claims are rejected; the bounded candidate distinction remains `NOVELTY_UNESTABLISHED`. The search is single-reviewer and not exhaustive; this limitation is explicit.
- **Ontology and annotation:** five versioned JSON Schemas, eleven illustrative bundles and annotation guidance separate pair comparability/relation, evidence-backed document attribution and case action. Unknown and unresolved states are not coerced into negatives.
- **Metrics and statistics:** denominators, endpoint definitions, clustered analyses, multiplicity and parameterized power/sample-size requirements are documented. No definitive N is fabricated from unavailable prevalence/effect-size inputs.
- **Risk and registration:** the risk approval packet is ready for the designated owner but unsigned. The Phase 2 protocol remains `DRAFT_NOT_SEALED` and is not a preregistration.
- **Leakage and readiness:** leakage threat model, Phase 2 data requirements/design/acceptance criteria, checklist and gate record are complete as drafts; DATA, GOLD, RISK and novelty dependencies remain blocking.

## Verification summary

| Check | Result |
|---|---:|
| V4.2 research tests | 13 passed |
| Existing semantic tests | 7 passed |
| Backend regression tests | 35 passed, 2 failed at the V4.1 checksum guard |
| V4.1 API tests | 0 passed, 2 failed at the same guard |
| Frontend production build | Passed; 1,637 modules transformed |
| E2E | Not run; no disposable database/URL, and the available flow writes synthetic review state |
| Frozen C predictions SHA-256 | `03d1a2a6aa3d52eae483cca2d538e8cf71777eea17aa32215160bc5be3dc7523` — match |
| V4 final manifest | 95/96 |
| V4 separate artifact inventory | 109/109 |
| Current V4.1 release manifest | 14/14 source; 51/52 artifact |
| Current separate V4.1 final manifest | 100/101 |
| V4.2 scoped artifact manifest | 62/62 |

Commands, exact digest values, historical manifest identities and qualifications are in `FINAL_VERIFICATION_REPORT.md` and `RUN_LOG.md`.

## Human actions still required

1. Release owner: disposition the V4 UI and V4.1 TONG bytes without replacing frozen manifests; also decide how future versioning should account for two stale source digests in the committed V4.1 manifest.
2. Domain/policy owner and qualified independent reviewers: adjudicate the 100 D1.1 proposals or keep them excluded.
3. Data owner, legal and security: approve target population, independent source data, permitted use, privacy, retention and access controls.
4. Domain risk owner and statistician: set criticality, epsilon, useful effect sizes, confidence procedure, costs and sample-size inputs.
5. Research lead with an independent screener: complete the second-pass/full-text/data-rights comparison and retain `NOVELTY_UNESTABLISHED` unless evidence changes it.
6. PI/research lead and statistician: freeze candidates, endpoints, analysis and sealed-test controls; independently timestamp registration before test-label access.
7. QA/release owner: provide a disposable E2E database if E2E execution is required after the integrity decision.

See `RESEARCH_READINESS_GATE.md` for individual G1–G7 decisions and `RELEASE_OWNER_APPROVAL_REQUEST.md` for the actionable release decision form.
