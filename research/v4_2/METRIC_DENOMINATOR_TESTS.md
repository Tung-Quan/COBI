# Metric Denominator Tests

The deterministic implementation is `tools/metric_contracts.py`; its tests are in `tests/test_contracts_and_audit.py`.

| Endpoint | Numerator | Denominator | Exclusions / guard |
|---|---|---|---|
| Pair comparability confusion | Count for each adjudicated true/predicted state | All pairs with adjudicated comparability | Three classes are retained; UNKNOWN is not mapped to NOT_COMPARABLE |
| Document attribution precision/recall | Predictions against verified incorrect/correct document labels | Independently adjudicated attribution-eligible documents (positive denominator is verified incorrect documents) | `UNRESOLVED` and unverified targets are excluded and counted separately |
| Critical misses among cleared cases | Critical cases predicted `NO_FLAG` | All eligible cases predicted `NO_FLAG` | Reports `NA` if no case is cleared |
| Critical case miss rate | Critical cases predicted `NO_FLAG` | All eligible critical cases | Reports `NA` if no eligible critical case exists |
| Action workload | `HUMAN_REVIEW` + `REQUEST_MORE_EVIDENCE` cases | All eligible adjudicated cases | Each action count and cost remains separate |

The unit suite uses hand-computable fixtures to verify empty denominators, unknown states, unresolved attribution and both case miss definitions. Passing these tests validates arithmetic contracts only; it does not validate labels or business policy.
