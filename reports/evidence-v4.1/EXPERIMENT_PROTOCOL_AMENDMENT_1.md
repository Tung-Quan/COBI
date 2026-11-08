# V4.1 Protocol Amendment 1 — Development Generator Correction

**Registered:** before any V4.1 model training, calibration, selection, Generator C generation, or Generator C label evaluation.  
**Original protocol canonical JSON SHA-256:** `b5fb342f0607ef14cfc6f0683a87585e6998e1cd176f0c48500b26ca8caf8711`  
**Amended protocol file SHA-256:** see `experiment_protocol_c.json` and `protocol_registration.json`.

## Reason

A semantic sanity check found that valid historical D4 cases changed the requested period to a historical month but a neutral third record retained the original current month. That unintended side record could be labeled valid while receiving a stale-as-current rule explanation. No training or model selection had taken place.

## Correction

- Set the side record's period to the same requested historical period in valid-history D4 cases.
- Bump the development generator from `semantic-ledger-dev-v1.0` to `semantic-ledger-dev-v1.1` and write the corrected frozen dataset to a new directory.
- Preserve the initial D1 pilot dataset under `data/development-d1/` and label it invalidated before training; it is excluded from every model fit, calibration, test, and result.
- Keep Generator C implementation, seed, sample size, scenarios, metrics, bootstrap, threshold rules, acceptance criteria, and ablation plan unchanged.

The correction was made before opening any development-test metrics for model selection, before fitting any V4.1 model, and before generating Generator C. Generator C remains a separately implemented challenge with its own held-out source pair.
