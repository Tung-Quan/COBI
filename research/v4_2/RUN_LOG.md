# V4.2 Phase 1 Run Log

**Date:** 2026-11-11 (Asia/Saigon)  
**Repository:** `C:\disk D\COBI`  
**Branch / starting commit:** `main` / `7f5eff1e46a8f0c03a36a11d6892231bf4927182`  
**Starting worktree:** 49 pre-existing status entries (42 tracked modifications, 7 untracked); preserved.

This log includes actual command outcomes for Phase 1 checks. The V4.1 verification log is historical repository evidence and is separately marked in `REPO_BASELINE_AUDIT.md`. No C scoring, replay, training, recalibration, label changes, deployment or push was run.

## Environment

| Command / inspection | Result |
|---|---|
| `python --version` | Python 3.13.13 |
| `python -m pip show pytest jsonschema` | pytest 8.3.4; jsonschema 4.25.1 in global Python |
| `backend/.venv/Scripts/python.exe --version` | Python 3.13.13 |
| `backend/.venv/Scripts/python.exe -c "import jsonschema"` | Exit 1: jsonschema is not installed in the backend environment; V4.2 schema tests used global Python. |
| `node --version` | v24.16.0 |
| `Get-FileHash reports/evidence-v4.1/data/generator-c-v1/C_PREDICTIONS_FROZEN.csv -Algorithm SHA256` | Exit 0; `03d1a2a6aa3d52eae483cca2d538e8cf71777eea17aa32215160bc5be3dc7523` (matches recorded digest). |

Test dependencies for the new schema suite are listed in `requirements-test.txt`.

## Phase 1 commands and results

| Command (working directory) | Exit | Result |
|---|---:|---|
| `python research/v4_2/tools/audit_d1_1.py` (repository root; first attempt) | 1 | Initial import failed because direct script execution did not include the repository root on `sys.path`; script was corrected inside `research/v4_2/`. |
| `python research/v4_2/tools/audit_d1_1.py` (repository root; rerun) | 0 | 200 stale-as-current records; 100 candidate omissions; split omissions 60/15/15/10; input hashes recorded; proposals pending; Generator C unchanged. |
| `python -m pytest -q research/v4_2/tests/test_contracts_and_audit.py` (root; initial authoring runs) | 1, 1 | First two runs exposed malformed JSON Schema / an incorrect fixture assertion; both corrected before final run. |
| `python -m pytest -q research/v4_2/tests/test_contracts_and_audit.py` (root; final) | 0 | 6 passed: schemas, all 7 fixtures, tri-state/attribution invariants, D1.1 counts and pending status. |
| `backend/.venv/Scripts/python.exe -m pytest -q evidence_ai/tests/test_v4_1_semantics.py` (root) | 0 | 7 passed. |
| `.venv/Scripts/python.exe -m pytest -q` (`backend/`) | 1 | 35 passed, 2 failed. Both failures are `tests/test_evidence_research_v41.py`; `_verified_metrics()` detects a V4.1 release artifact checksum mismatch. |
| `.venv/Scripts/python.exe -m pytest -q tests/test_evidence_research_v41.py` (`backend/`) | 1 | 2 failed for the same checksum guard; one Starlette/AnyIO deprecation warning. An initial wrong-relative-path attempt exited 1 before execution and was immediately rerun correctly. |
| `npm run build` (`frontend/`) | 0 | TypeScript/Vite build passed; 1,637 modules transformed. |
| Read-only check of `RELEASE_MANIFEST.json` source/artifact checksums | 0 | 14/14 source checksums match; 51/52 artifact checksums match. The only mismatch is pre-existing `TONG_HOP_COBI_V4_1.md`: recorded `be5b8776…d57c7`, current `f40b28f7…78a40`. It was already untracked at task start and was preserved. |
| Read-only protected-manifest check in `FINAL_MANIFEST.json` | 0 | V4 manifest remains 95/96. `frontend/src/EvidenceResearch.tsx` expected `b3f7b74e…eff0947`, actual `54da9de3…d18db9`; actual hash matches the `HEAD` blob. |

## Scientific and integrity controls

- Verified C SHA-256 before and after Phase 1; no scoring or replay was performed.
- D1.1 raw inputs, four split manifests and the existing semantic source hash were read and hashed. New audit outputs are only `D1_1_PROPOSED_CHANGELOG.csv` and `D1_1_AUDIT_SUMMARY.json` within this directory.
- Protected V2/V3/V4.1 and product paths were not edited by this task. Existing pre-task changes and mismatches were preserved.
- Literature checks used official publisher/proceedings pages. Full texts inspected: FinDVer, FinED-Bench, FinBalance, conformal risk control and the leakage/reproducibility paper. The FinDVer landing-page/paper count discrepancy is preserved; this remains a targeted, non-systematic search. See `PRIOR_ART_MATRIX.md`.

## Historical verification records (not rerun by this Phase 1 task)

`reports/evidence-v4.1/VERIFICATION_LOG.md` records 37 backend tests, 7 semantic tests, 2 API tests, frontend build, desktop/mobile E2E and 100/100 final package manifest files. These remain historical claims. The current backend suite no longer passes all V4.1 API assertions because the release artifact hash for the pre-existing untracked report differs; the protected V4 manifest's separate 95/96 finding also remains.

## Continuation addendum — 2026-11-11

The previous Phase 1 snapshot above is preserved. At the start of this continuation, `git status --short` showed 50 entries (42 tracked modifications and 8 untracked entries, including the already-existing `research/` directory). All authored reports, scripts, fixtures and tests for this continuation are under `research/v4_2/`. The requested frontend build refreshed ignored generated output under `frontend/dist/`; it changed no tracked frontend source. The same 50 top-level status entries remained at the final check. Existing non-research modifications were preserved. The project was on `main` at `7f5eff1e46a8f0c03a36a11d6892231bf4927182`.

| Command (working directory) | Exit | Result |
|---|---:|---|
| `python -m research.v4_2.tools.build_adjudication_fixtures` (root) | 0 | Wrote 100 blank reviewer rows, all pending; added 4 edge fixtures; no original labels changed. |
| `python research/v4_2/tools/audit_d1_1.py` (root) | 0 | Read-only replay: 200 stale-as-current; 100 candidate omissions; 60/15/15/10; all input hashes recorded; no C change. |
| `python -m pytest -q research/v4_2/tests/test_contracts_and_audit.py` (root) | 0 | 12 passed: five schemas, all 11 fixtures, referential/edge invariants, D1.1 status and metric denominator arithmetic. |
| `backend/.venv/Scripts/python.exe -m pytest -q evidence_ai/tests/test_v4_1_semantics.py` (root) | 0 | 7 passed. |
| `.venv/Scripts/python.exe -m pytest -q` (`backend/`) | 1 | 35 passed, 2 failed. Both failures stop at `ValueError: V4.1 research artifact checksum mismatch` from the read-only release guard. |
| `.venv/Scripts/python.exe -m pytest -q tests/test_evidence_research_v41.py` (`backend/`) | 1 | 0 passed, 2 failed at the same checksum guard; one Starlette/AnyIO deprecation warning. |
| `npm run build` (`frontend/`) | 0 | Production TypeScript/Vite build passed; 1,637 modules transformed. |
| `python -m research.v4_2.tools.audit_release_integrity` (root) | 0 | C predictions hash matches; V4 `FINAL_MANIFEST` 95/96; current V4.1 worktree release manifest 14/14 sources, 51/52 artifacts; committed HEAD manifest applied to current files 13/14 sources, 9/19 artifacts. Exact mismatch hashes are in `FINAL_VERIFICATION_REPORT.md`. |
| `python -m research.v4_2.tools.make_artifact_manifest` then `python -m research.v4_2.tools.make_artifact_manifest --check` (root) | 0 / 0 | Created 61-file V4.2 research-scoped manifest; final check `MATCH`, no hash differences. |
| Read-only environment inspection (root) | 0 | Python 3.13.13; pytest 8.3.4; jsonschema 4.25.1; Node v24.16.0. |
| E2E Research UI | `NOT_RUN` | `COBI_E2E_URL` is not configured. Available `frontend/tests/workbench.e2e.mjs` creates a synthetic case and records review/consent actions; no disposable test database was supplied, so this mutating workflow was not launched. |

### Interpretation and controls

- The current V4.1 API failures are classified as **historical release-integrity discrepancies**, not marked passing and not treated as proof of a new product regression.
- `reports/evidence-v4/final_manifest.json` is the 96-entry V4 release manifest (95/96); `reports/evidence-v4/ARTIFACT_MANIFEST.json` is a different 109-entry artifact inventory (109/109). They are not interchangeable.
- Current worktree V4.1 manifest: TONG expected `be5b8776…d57c7`, actual `f40b28f7…78a40`. Committed `HEAD` manifest is a distinct 19-artifact historical snapshot; applied to current files it has 13/14 sources and 9/19 artifacts matching.
- FinDVer count conflict was expanded to three primary-source statements: ACL abstract 4,000/four; arXiv abstract 2,400/three; ACL PDF body 2,100 initial examples/three. The current author README says three subsets and describes a July 2026 test-label release without stating a total. No reason resolving the conflict was found.
- Generator C was not rescored, retrained, recalibrated or used for selection. Original D1.1 gold and protected manifests were not edited. No product paths were changed.


## Final integrity reconciliation and Phase 1 closeout — 2026-11-11

The preceding entries preserve prior Phase 1 snapshots. This closeout made research-only changes: the release-audit helper now uses the committed lowercase V4 manifest path; a focused test covers that path; the first-pass literature ledger and bounded novelty documents were updated with five close-overlap resources; the release-owner decision form and final reports were completed. Neither protected release manifest, V4/V4.1 report/source artifact, label file, Generator C output, model, threshold, nor checkout decision path was changed.

### Final commands and actual outcomes

| Command (working directory) | Exit | Result |
|---|---:|---|
| `python -m pytest -q research/v4_2/tests/test_contracts_and_audit.py` (root) | 0 | **13 passed**. Includes the case-correct V4 manifest-path regression check. |
| `backend/.venv/Scripts/python.exe -m pytest -q evidence_ai/tests/test_v4_1_semantics.py` (root) | 0 | **7 passed**. |
| `.venv/Scripts/python.exe -m pytest -q` (`backend/`) | 1 | **35 passed, 2 failed**. Both failures stop at `_verified_metrics()` on `V4.1 research artifact checksum mismatch` for the read-only V4.1 guard. |
| `.venv/Scripts/python.exe -m pytest -q tests/test_evidence_research_v41.py` (`backend/`) | 1 | **0 passed, 2 failed** at the same guard; no bypass or test change. One Starlette/AnyIO deprecation warning. |
| `npm run build` (`frontend/`) | 0 | Production build passed; **1,637 modules transformed**. |
| `python -m research.v4_2.tools.audit_release_integrity` (root) | 0 | Frozen C digest matches. V4 `final_manifest.json` is 95/96; current worktree V4.1 manifest is 14/14 sources and 51/52 artifacts; committed V4.1 manifest against current files is 13/14 sources and 9/19 artifacts. |
| `python research/v4_2/tools/audit_d1_1.py` (root) | 0 | 200 stale-as-current; 100 candidate omissions; 60/15/15/10; all proposals pending; no C/gold modification. |
| `python -m research.v4_2.tools.make_artifact_manifest` then `python -m research.v4_2.tools.make_artifact_manifest --check` (root) | 0 / 0 | Final closeout manifest written and verified **62/62** V4.2-scoped files; self-hash excluded. |
| E2E | `NOT_RUN` | No `COBI_E2E_URL` or disposable database. The available flow writes synthetic case/review/consent data. |

### Reconciled history and current release counts

- V4 `reports/evidence-v4/final_manifest.json`: 96 entries, 95/96 current matches; the only mismatch is `frontend/src/EvidenceResearch.tsx` (expected `b3f7b74ec8ab8d1c773c970f5f31d3f2181c1f539fb968d37ab0fb4d7eff0947`, actual `54da9de3afae412a20a58e47578fd9ca89276f0f85c87c72bf02d9f21dd18db9`). The same actual Git blob was present when the manifest was committed in `683b110e8f735ba838fbb8b268ce8d4c3dfe3aa0`; the component's only path-history commit is `93f17b07ebd3356b04dc1df0041fc3656a6e3888`.
- Separate V4 `ARTIFACT_MANIFEST.json`: 109/109 current entries.
- V4.1 committed `RELEASE_MANIFEST.json` from `e9102a7e9fb5b79edef1449eb869c7637f2e781f`: 14 source and 19 artifact entries. At the commit tree, Git-filtered bytes yield 12/14 source and 19/19 artifact matches. Its same-snapshot source digests for `EXPERIMENT_PROTOCOL_C.md` and `experiment_protocol_c.json` do not match that tree. Applied to current modified files it yields 13/14 source and 9/19 artifact matches.
- Current modified V4.1 worktree `RELEASE_MANIFEST.json`: 14/14 sources, 51/52 artifacts; TONG expected `be5b8776c9b0e1186d78e4c331ba22c10a3edd808278e5836b4df18d2f2d57c7` vs actual `f40b28f712dba9e7bc061f9a9f0434ef4d883aa1cbabc42cc66a955739278a40`.
- Separate untracked V4.1 `FINAL_MANIFEST.json`: 101 entries, 100/101 current matches; same TONG mismatch, expected size 19,107 vs current 19,297 bytes. `VERIFICATION_LOG.md`'s 100/100 result is from an earlier snapshot.
- Current C predictions SHA-256: `03d1a2a6aa3d52eae483cca2d538e8cf71777eea17aa32215160bc5be3dc7523`, unchanged.

Historical file metadata (Asia/Saigon) shows TONG last written at 16:17:36, after the current release manifest at 16:15:51 and final manifest at 16:15:52. This is consistent with a post-manifest report edit; it does not prove the editor or recover the old content. Both requested mismatches remain open in `RELEASE_INTEGRITY_RECONCILIATION.md`; `RELEASE_OWNER_APPROVAL_REQUEST.md` is prepared and unsigned.

### Final readiness record

Final disposition: **`PHASE1_COMPLETE_PHASE2_BLOCKED`**. Phase 1 documentation and checks are complete to the available evidence. Phase 2 remains blocked by the release-owner decision, independent D1.1 adjudication, permitted independent data, policy-approved risk parameters, independent literature screening, sealed preregistration and required safe test environment. No Generator D/training/threshold/locked-test action occurred.
