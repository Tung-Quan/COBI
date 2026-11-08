# Updated Dataset and Split Manifest Index

This index documents existing manifests and their integrity; it does not rewrite their data.

| Artifact | Role | SHA-256 |
|---|---|---|
| `experiment_protocol_c.json` | Registered Generator C mechanism, scenarios, seeds, metrics and acceptance rules | `9ea7842de9004b7349ea0d403d6ffa44dabbe8ae3c7352f1626a03348c9178da` |
| `data/development-d1.1/dataset_manifest.json` | Permitted D1.1 training/validation/calibration/locked-test source | `2bf617a463cb0a2e046abe49feaed070acb4135c2b537cd7f652c465b9f6ae1e` |
| `data/generator-c-v1/dataset_manifest.json` | C group/case/document and scenario manifest | `7a15e685acafbbf0ff537021cad7d17d269876d129c7674d793146df7c634502` |
| `data/generator-c-v1/C_PREDICTION_MANIFEST.json` | Prediction hashes frozen before label access | `506b279597b251243674cb5b61a99d898c94161615c8de92862c1228bf361e70` |
| `data/generator-c-v1/C_EVALUATION_MANIFEST.json` | Label-opening and evaluation artifact hashes | `8d58f1768cc044a4dd5e3ac048b3149953cf809eaa17f5b252bfcf166969da23` |
| `models/frozen-v1/frozen_model_manifest.json` | Frozen model identities, features, thresholds and artifact references | `9e960f45b0b4607f243de7429cd329e8317dea0a2020cf0ebe859e4641a78c1a` |

Generator C partitions 840 groups equally across seven registered scenarios (120 groups each), with two cases per group. The two cases and all documents remain clustered by customer group for uncertainty resampling. The payroll+merchant source pair is excluded from D1.1 and used in C7. C labels are open; the existing split remains valid as a frozen split, but C is not a newly blind test.

**Split-quality qualification:** D1.1's four disjoint partitions are documented in the source split manifests. Post-evaluation semantic audit found 100 critical-label omissions in stale records across every partition. Split disjointness does not cure label inconsistency. No relabeling, retraining, recalibration, or retuning is done here.
