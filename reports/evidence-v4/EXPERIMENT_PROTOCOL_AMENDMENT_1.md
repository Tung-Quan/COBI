# Generator B Protocol Amendment 1

**Registered:** 2026-11-08, before the confirmatory Generator B replay  
**Applies to:** `cobi-evidence-v4.0`  
**Original protocol SHA-256:** `f1eb2df747451e18a511d18c9679eb6685d2640056d3eb9054566468789d9a65`  
**Status:** implementation correction; initial B pilot invalidated

## Reason

A pre-confirmatory feature-leakage audit of the first Generator B implementation found event-dependent explanatory phrases in the model-visible document text. In B2/B4/B5, wording such as an explicit duplicate-status phrase, a stale-as-current phrase, or a statement that a difference was valid could reveal generator event semantics to the model. The first evaluation used that implementation and is therefore invalid as confirmatory evidence.

## Corrective action

- Preserve the first generated dataset and its outputs in `experiments/invalidated-generator-b-leakage-pilot/` with status `INVALIDATED_PRE_CONFIRMATORY_FEATURE_LEAKAGE`.
- Generate the confirmatory corpus in a new directory, using the same registered seed, sample size, scenario proportions, label rules, model artifacts, preprocessing, calibration, thresholds, evaluation units, metrics, bootstrap draws, and cost assumptions.
- Remove event-dependent evaluative wording from model-visible text. Keep canonical facts and event labels physically separate from observed document text.
- Keep the actual synthetic evidence contents (including duplicate amounts, parse errors, and ages) visible where they would form part of the document. Do not add a text cue that directly names whether the evidence is erroneous or legitimate.
- Do not use the invalidated run's metric values to alter the hypotheses, sample size, model set, thresholds, event rates, or economic assumptions.

This amendment changes only the feature-leakage defect in the implementation. It does not change the research question, registered hypotheses, metrics, or decision rules. If the corrected implementation fails feature-leakage checks, E2 remains blocked rather than being tuned against its outcomes.
