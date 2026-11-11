# Claims and Limitations — COBI V4.2 Phase 1

## Supported statements

- The actual frozen Generator C prediction file exists at `reports/evidence-v4.1/data/generator-c-v1/C_PREDICTIONS_FROZEN.csv`; its current SHA-256 matches the recorded V4.1 digest.
- V4.1's stored metric artifacts report the counts and scores listed in `REPO_BASELINE_AUDIT.md`. This Phase 1 task did not re-score C; measurements are post-unblinding and synthetic.
- The D1.1 raw data, gold and split manifests support 200 records identified as stale-as-current by the registered temporal rule and 100 missing critical labels, split 60/15/15/10. A separate read-only script and output preserve a candidate changelog. All 100 remain pending independent adjudication and policy approval.
- Machine-validatable JSON Schema contracts and eleven illustrative synthetic bundles now encode separate claim, pair, document attribution and case-action labels. Scoped validation tests passed.
- The scoped systematic query and single-reviewer first-pass screen are recorded in the 28-entry screening ledger (26 unique studies/resources plus two explicit version/duplicate views). Full texts were inspected for the closest financial claim-verification, reconciliation, financial QA, temporal/provenance and benchmark-audit work; the newest data-card-only sources are labeled as such. The search is not exhaustive or independently screened, and data/source license overlap remains incomplete. FinDVer official versions report conflicting dataset counts, which remain unresolved.
- The Phase 1 test log records current semantic tests, V4.2 contract tests, frontend build, and the full backend suite outcomes. Two V4.1 API tests fail because the existing release manifest checksum does not match the untracked report file it names.

## Statements not supported

- Accuracy, calibration or risk guarantees on real bank documents or another institution/policy.
- A conclusion that any document is fraudulent or that a specific source is wrong from pair contradiction alone.
- Causal benefit from temporal/provenance learned features, or a complete all-candidate V4.1 comparison.
- A certified review threshold, bank-approved error tolerance, loss reduction, workload savings, regulatory readiness or loan-decision quality.
- A first-of-its-kind financial evidence benchmark or verifier.
- A sealed preregistration or confirmatory Generator C result.

## Material limits

1. D1.1 gold is synthetic/programmatic and omits critical temporal labels. Proposed corrections are not accepted gold.
2. Generator C labels were already opened. No new C score, threshold or model selection is produced here.
3. Prior-art review uses a scoped systematic query and single-reviewer first pass, including recent close overlaps. It is not exhaustive or independently screened; novelty remains unestablished, and some dataset/source rights need review.
4. Phase 2 needs an independent benchmark construction process, permitted source evidence, independent adjudication, approved policy and risk tolerance, split/power design, and sealed label controls.
5. Current pre-existing V4.1 integrity findings remain visible: protected V4 manifest 95/96, and the read-only V4.1 backend API checksum guard fails against `TONG_HOP_COBI_V4_1.md`. Neither file was changed by this work.

## Wording rules for future reports

Use `reported in the V4.1 synthetic release` or `observed on post-unblinding Generator C` for old measurements. Use `candidate` or `pending adjudication` for any D1.1 proposed label. Use `independently adjudicated` only when reviewer/source evidence and provenance support it. Keep `EVIDENCE_AI_VALIDATION_BLOCKED` until independent real-world evidence is authorized and evaluated.
