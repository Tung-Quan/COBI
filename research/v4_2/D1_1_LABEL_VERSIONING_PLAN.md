# D1.1 Label Versioning Plan

## Immutable inputs

Retain the current dataset manifest, `observed.json`, `gold_labels.json`, four split manifests and their recorded SHA-256 values exactly as they are. Do not patch original labels or regenerate them in place. Generator C predictions, labels, thresholds and metrics remain outside this process.

## Proposed version sequence

1. `semantic-evidence-development-d1.1` — immutable original labels; status `HISTORICAL_UNADJUDICATED` for the 100 candidate disagreements.
2. `semantic-evidence-development-d1.1-review-1` — append-only reviewer records, preserving each independent rating, evidence references, policy version, rater role, timestamps and adjudication outcome. Raw labels still separate.
3. `semantic-evidence-development-d1.2` — create only after policy owner and independent adjudication approval. Store final adjudicated labels in a new file, a new manifest, new hashes, and lineage back to original record IDs and review decisions. Unresolved cases stay `UNKNOWN/UNRESOLVED`; do not force binary labels.

## Release conditions

- A written policy defines target population, applicable period/as-of semantics, freshness by source/field, correction/supersession and what makes a stale record critical.
- At least two independent qualified ratings per candidate, followed by an identified adjudicator for disagreements; report agreement with appropriate class prevalence context.
- Reviewers do not use model scores or candidate correction as ground truth.
- Locked-test labels remain inaccessible to training/model selection. If already exposed, retire the split from confirmation and create a fresh group-held-out sealed test.
- Versioned dataset card records synthetic scope, generator and policy versions, allowed uses, lineage, exclusions, adjudication status and license.
- All dependent metrics are recomputed only under an explicitly versioned analysis; historical reports remain unaltered and clearly distinguish the old and new label versions.

Until every condition is met, the 100 rows stay `PENDING_ADJUDICATION`, are excluded from confirmatory training/evaluation, and the gold-correction gate remains blocked.
