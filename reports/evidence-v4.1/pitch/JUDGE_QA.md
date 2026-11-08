# Likely questions and precise answers

### Is this validated on actual bank documents?

No. Generator C is programmatic synthetic evidence with supplied structured metadata. It does not measure real-document parsing or bank performance.

### What does 100% recall mean here?

The frozen hybrid flagged all 520 records labeled critical in this Generator C release. It flagged all 120 critical stale-as-current records in scenario C4. The estimates are conditional on this generator and label policy.

### Why was the overall false-positive rate not zero?

The hybrid flagged 400 valid peer records in same-period conflict scenarios: 160 in C2, 120 in C6 and 120 in C7. The pair-level rule can detect a comparable conflict but cannot identify which peer is wrong, so both sides are sent for review.

### Did the semantic features cause the improvement?

That conclusion is not supported. The hybrid includes deterministic rules, and an audit found 100 missing critical labels among stale development records. The learned feature effects remain exploratory.

### Is Generator C independent of the deterministic rules?

It is independent in implementation path, seed, and templates, but not fully independent at the semantic-criterion level. C2/C6/C7 use the same field tolerances as the rules, and the C4 gold and time rule share a 180-day stale threshold. This is target-construct overlap, not direct leakage of hidden gold or corruption IDs into prediction inputs. The result does not establish generalization to independently adjudicated criteria.

### Did every registered acceptance criterion pass?

Four of five point-estimate criteria were met. The fifth requires comparison with the best complete frozen baseline, but the frozen XGBoost replay was blocked by the missing `xgboost==3.0.5` dependency. The registered criterion is therefore unassessable.

### Can it route or approve applications?

No. Validation status is `EVIDENCE_AI_VALIDATION_BLOCKED`; the checkout application does not consume Generator C outputs, and routing/approval are unauthorized.
