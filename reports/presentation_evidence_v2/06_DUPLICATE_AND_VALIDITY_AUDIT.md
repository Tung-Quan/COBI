# Duplicate vectors and model validity

Exact equality over the 19 source predictors gives **29,183 distinct vectors** among 30,000 records, or **817 rows beyond the first occurrence**. All 30,000 sample IDs are distinct. The test contains **127/4,500 (2.8222%)** vectors observed in train. There are 97 test rows matching validation and 101 matching calibration. These categories overlap. The union is **133 test rows** matching at least one development cohort, and 65 test rows repeat a vector within test beyond the first occurrence. The audit used exact tuple equality rather than treating row hash matches as proof of equality. [Audit fields](audit_summary.json) · [Original data diagnostics](../final/uci350-v2.0/report.json).

## Post-hoc sensitivity using frozen predictions

| Existing test subset | N | Defaults | Default rate | Raw AUC | Raw log loss | Sigmoid log loss | Paired sigmoid − raw log loss [descriptive 95% CI] |
|---|---:|---:|---:|---:|---:|---:|---|
| Full test | 4,500 | 995 | 22.11% | 0.78529 | 0.424263 | 0.424694 | +0.000431 [+0.000024, +0.000837] |
| No train vector | 4,373 | 938 | 21.45% | 0.78390 | 0.416030 | 0.416400 | +0.000370 [−0.000062, +0.000811] |
| No train, validation or calibration vector | 4,367 | 934 | 21.39% | 0.78331 | 0.415875 | 0.416233 | +0.000358 [−0.000094, +0.000774] |
| Matches train vector | 127 | 57 | 44.88% | 0.58221 | 0.707743 | 0.710282 | +0.002539 [+0.001143, +0.003914] |

These are existing predictions evaluated on changed denominators. Removing overlap also changes the event prevalence and covariate mix. AUC stays close in the two larger subsets, while the calibration difference intervals include zero. The small overlap subset is comparatively difficult for this model. Its poorer scores do not prove that duplicates cause difficulty or that overlap helped or harmed the full result. An identical vector may be a repeated observation or a coincidental match in discrete financial inputs. A true customer ID is unavailable. No new group split or model was fit. [Sensitivity figure](figures/duplicate_sensitivity.svg).

| Validity dimension | What the evidence supports |
|---|---|
| Internal validity | Fixed stratified cohort membership, disjoint IDs, train-only preprocessing, validation-only selection and separate calibration. Exact vector overlap remains. |
| Statistical uncertainty | Paired percentile intervals preserve within-row model comparison. The row bootstrap conditions on fitted models, and can understate uncertainty when rows are dependent. The subset analysis is exploratory. |
| Temporal validity | The history window is in 2005 and the label is next payment month. Per-application dates and chronological drift evidence are unavailable. |
| Geographic validity | The data are from Taiwan. Local calibration, operating conditions and applicant selection in Vietnam remain unknown. |
| Product and domain transfer | Revolving card default differs from installment checkout loss, horizon and predictors. The app enforces the domain boundary. |

A future duplicate-group study should use a distinct experiment ID and a prespecified grouping rule before development/test selection. Prefer reliable customer IDs and a chronological, outcome-mature bank sample. Exact vector grouping can be a robustness design when IDs are unavailable. It cannot establish customer-disjoint validity.
