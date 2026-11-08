# UCI 350 dataset and preprocessing

**Presentation takeaway.** The model learned historical next-payment-month default in a Taiwanese credit-card cohort. The dataset supports an internal random-holdout benchmark for that task.

| Attribute | Verified value |
|---|---|
| Source | I-Cheng Yeh, *Default of Credit Card Clients*, UCI Machine Learning Repository, DOI 10.24432/C55S3H |
| License | Creative Commons Attribution 4.0 International |
| Population and feature window | Taiwan credit-card customers, April–September 2005 repayment, billing and payment history |
| Label | `default.payment.next.month`, 1 = default, 0 = no default |
| Raw shape | 30,000 rows × 25 columns, including 23 source features, ID and label |
| Class distribution | 23,364 non-defaults (77.88%), 6,636 defaults (22.12%) |
| Model design | 19 source predictors, 85 float32 model inputs |
| Leakage controls | Unique IDs, disjoint cohort memberships, fixed encoding and train-only numeric scaling |

[Official UCI card](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients) · [License](https://creativecommons.org/licenses/by/4.0/) · [Dataset manifest](../../data/manifest/uci350.yaml).

## Provenance

The original acquisition used the official UCI ZIP and CSV plus `ucimlrepo.fetch_ucirepo(id=350)`. The new audit independently rehashed the local ZIP, XLS, CSV, license-card snapshot and normalized CSV, verified the XLS bytes against the ZIP member, normalized the two raw representations and checked row-for-row equality with the local normalized data. No raw records were copied into this package. [Acquisition implementation](../../scripts/fetch_uci.py) · [Audit code](verify_evidence.py).

| Local original | SHA-256 |
|---|---|
| `data/raw/uci350.zip` | `56c885f84457f6680f8438f02bfcdac9579323d8a94465ee5f26e32baa727602` |
| `data/raw/default of credit card clients.xls` | `30c6be3abd8dcfd3e6096c828bad8c2f011238620f5369220bd60cfc82700933` |
| `data/raw/uci350-official.csv` | `45bcf4df62ff2e237a74eb155cabfb4bbbc171219a0637daef44fdad07503dd0` |
| `data/processed/uci350.csv` | `957a8f0c61a409fca9831da6dc9eb38a710503f0a09a19d5725a574f48db5809` |

## Inputs and transformation

- **13 numeric predictors**. `LIMIT_BAL` (credit limit including supplementary credit), `BILL_AMT1` through `BILL_AMT6` (monthly statement amounts, latest first), and `PAY_AMT1` through `PAY_AMT6` (prior payments, latest first). Values are in NTD. `StandardScaler` computes means and population standard deviations on the 18,000 training rows, then applies `(x−μ_train)/σ_train` to all other cohorts and inference. Numeric inputs occupy the first 13 columns.
- **Six categorical predictors**. `PAY_0, PAY_2, PAY_3, PAY_4, PAY_5, PAY_6` correspond to September through April 2005. Each has a fixed one-hot block for the 12 integer codes −2 through 9. The blocks follow the numeric inputs. Total width is `13 + 6 × 12 = 85`. All 11 candidates share this transformation.
- **Excluded**. `SEX, EDUCATION, MARRIAGE, AGE` are excluded from predictive inputs. `ID` is used only for integrity and split membership. The label is stored separately. This choice leaves possible proxies and differences in subgroup error unmeasured.
- **Missing or invalid**. Ingestion requires a 30,000 × 25 frame of finite integer values, unique expected sample IDs, labels {0,1} and engineering bounds for the allowlist. This snapshot has zero missing cells. No imputation, outlier winsorization, feature selection or rare-category merging occurs. Research inference requires exact compatible keys, types, bounds, domain, horizon and feature signature.
- **Unusual codes and values**. UCI documents −1 as paid duly and positive delay categories. The repository preserves observed −2 and 0 as distinct undocumented categories and assigns them no business meaning. In `PAY_0` these occur 2,759 and 14,737 times respectively. Code 9 is in the contract and absent from this snapshot. Some allowed categories are rare or absent by month. Negative bill balances are retained within the signed amount bounds. The transformer encodes allowed unseen categories using the same fixed column order. Their predictive contribution lacks independent evidence.

[Feature contract](../../ml/contracts.py) · [Transformation code](../../ml/preprocessing.py) · [Input guards](../../ml/predict.py).

## Cohort lock

| Cohort | Role | N | Default | No default | Rate |
|---|---|---:|---:|---:|---:|
| Train | Fit scaler and candidate weights | 18,000 | 3,982 | 14,018 | 22.122% |
| Validation | Compare configurations and select stops | 4,500 | 995 | 3,505 | 22.111% |
| Calibration | Fit selected model’s sigmoid | 3,000 | 664 | 2,336 | 22.133% |
| Locked test | Evaluate frozen predictions | 4,500 | 995 | 3,505 | 22.111% |

Random stratification allocates 60/15/10/15 using seed 42. The audit regenerated membership, checked complete and non-overlapping IDs, verified the lock hash and confirmed scaler values against train-only moments. The artifact replay reproduces validation and test scores without retraining. No fresh training run is claimed. Absolute chronology and customer-disjoint validation are unavailable. [Split implementation](../../ml/split.py) · [Lock summary](../final/split-lock.json) · [Duplicate sensitivity](06_DUPLICATE_AND_VALIDITY_AUDIT.md).

**Slide visuals** · [Class distribution](figures/class_distribution.svg) · [Data processing and cohorts](figures/dataset_processing.svg).
