# COBI V4.2 — Final Research Readiness Gate

**Final Phase 1 status:** `PHASE1_COMPLETE_PHASE2_BLOCKED`  
**Phase 2 experiment status:** `BLOCKED`  
**Product status:** research-only/read-only; `EVIDENCE_AI_VALIDATION_BLOCKED`  
**Date:** 2026-11-11

## Final decision basis

Phase 1's documentation, audit, scoped tests and artifact manifest are complete for evidence available in the repository and primary sources. The review has not manufactured missing data, approval, labels, reviewer identity, license permission or model results. Phase 2 is blocked until every mandatory gate below is resolved and the release checksum guard passes on an authorized package.

| Gate | Phase 1 disposition | Phase 2 state | Evidence and exact blocker | Owner and next action |
|---|---|---|---|---|
| **G1 — Release integrity** | Documented; unresolved | **BLOCKED** | V4 `final_manifest.json` is 95/96; V4.1 current modified `RELEASE_MANIFEST.json` is 14/14 sources and 51/52 artifacts; current V4.1 `FINAL_MANIFEST.json` is 100/101. Current TONG differs from the two records' 19,107-byte expected version. The V4 UI digest already disagrees with its same-commit V4 manifest. The committed V4.1 manifest also has two same-tree source digest mismatches. | Release/repository owner: complete `RELEASE_OWNER_APPROVAL_REQUEST.md`; identify approved bytes or authorize an explicitly versioned package retaining historical manifests; rerun guards. |
| **G2 — Gold and annotation quality** | **PASS for audit packet; labels pending** | **BLOCKED** | D1.1 audit found 100 candidate omissions across 200 stale-as-current records. No independent adjudication is present; every decision is blank and pending. | Domain/policy owner + two qualified independent reviewers: adjudicate from source/as-of policy, retain raw ratings, and either exclude D1.1 or issue an immutable approved label version. |
| **G3 — Independent data and target population** | Requirements documented | **BLOCKED** | No independently constructed, permitted borrower/case benchmark or approved population is available. Generator C is synthetic, already unblinded and not a substitute. | Research/data owner + legal/security: approve workflow, sampling frame, source/data rights, privacy, retention and access; build a source-independent dataset and hashed group/time/template splits. |
| **G4 — Risk policy and sample-size inputs** | Approval packet drafted | **BLOCKED** | Criticality definition, epsilon, action costs, primary practical effect size, prevalence and cluster variance remain unknown/unapproved. Numerical N cannot be estimated responsibly. | Domain risk owner + statistician: complete/sign `RISK_POLICY_APPROVAL_PACKET.md`; use permitted blinded pilot inputs to finalize the sample-size plan and upper-bound procedure. |
| **G5 — Prior art and novelty** | Scoped search and first-pass screen complete; novelty unestablished | **BLOCKED** | Screening log has 28 entries: 26 unique studies/resources plus two explicit version/duplicate views; it captures close work including FinBalance, FinAuditing, FinED-Bench, FinDVer, FinVerBench, RFC-Bench, TempFinRAG, HC-RAG/Multi-Doc-2025, FinFIRST, EvidenceLens and FinAgent. Search result totals are not exportable and there is no independent second screener; some licenses and overlap dimensions remain open. FinDVer counts conflict across official versions. | Research lead + independent screener: repeat the frozen search/screen, verify full-text task/gold/rights overlaps, document retrieved/excluded counts where exportable, and retain a bounded claim. |
| **G6 — Evaluation protocol and registration** | Draft complete; not sealed | **BLOCKED** | RQs, schemas, endpoints, denominators and analysis approach are written, but population, primary effect, candidate family, threshold/policy inputs, final sample size and independent timestamp are not frozen. No locked test exists. | PI/research lead + statistician + risk owner: after G2–G5, freeze code/config/splits/endpoints, exclusions, multiplicity and stopping rules; independently timestamp before test-label access. |
| **G7 — Technical reproducibility and safe execution** | **PARTIAL** | **BLOCKED** | 15 V4.2 research tests and 7 semantic tests pass; frontend production build passes; C digest matches. Backend is 35/37 and targeted API tests 0/2 because the V4.1 guard detects TONG mismatch. E2E was not run: no disposable URL/database, and the available flow writes synthetic review/consent data. | Release owner + QA/research engineer: resolve or formally preserve the release baseline; rerun checks after an authorized decision; supply an isolated disposable environment before E2E. |

## Mandatory stop conditions

Until G1–G7 are satisfied for a versioned, approved research package:

- Do not construct Generator D, train/rescore models, select thresholds, conduct confirmatory evaluation or access locked test labels.
- Do not treat pending D1.1 proposals as approved gold.
- Do not infer real-bank validation, permission to use datasets from code licenses, novelty, or a risk guarantee from synthetic results.
- Keep all research outputs separate from checkout approval/routing logic.

## Human approval checklist

- [ ] Release owner signed the two-artifact integrity disposition and versioning decision.
- [ ] Qualified independent reviewers and policy owner recorded all D1.1 decisions, or D1.1 was excluded.
- [ ] Research/data owner and legal/security approved population, data rights and controls.
- [ ] Risk owner and statistician approved criticality, epsilon, endpoint, effect size and sample plan.
- [ ] Independent screener completed a second review and broader dataset/license overlap disposition.
- [ ] PI/statistician froze and independently timestamped the preregistration before sealed-test access.
- [ ] QA/release owner supplied a disposable E2E environment if E2E is required.

The complete report and executable check records are in `FINAL_PHASE1_REPORT.md`, `FINAL_VERIFICATION_REPORT.md`, `RUN_LOG.md` and `FINAL_ARTIFACT_MANIFEST.json`.
