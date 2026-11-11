# Statistical Analysis Plan — Draft 1.0

**Status:** prospective draft, not sealed. Do not describe it as preregistered until it is independently timestamped/frozen before any confirmatory test labels are accessible.

## Analysis freeze and estimands

The confirmatory estimand, if future data and approvals become available, is the difference in each predeclared endpoint between a frozen candidate and a frozen control on the target case population and policy window, averaged over independent economic/customer groups. A separate estimand describes the finite synthetic challenge under each named generator. Neither estimand is a real-bank claim without permitted representative data and independent labels.

Freeze before label access: hypotheses; primary/secondary endpoints; eligible population; annotation/policy versions; candidate family; source/generator configurations; features; transformations; train/validation/calibration/locked-test group lists; threshold rule; missingness handling; confidence procedure; multiplicity family; and stopping rule. Keep all group-linked documents and counterfactual variants inside one split.

## Splits, pairing and intervals

- Split by customer/economic group and template family where possible. No group, document version, paired counterfactual or duplicate customer record crosses train, calibration, validation and test.
- Use paired cluster bootstrap over economic/customer groups for model contrasts and primary intervals, with at least **2,000 resamples** in future evaluation. Freeze bootstrap seed and implementation before unblinding. Resample the same groups for both systems.
- Use group-level or cluster-robust intervals for rates; report group count and cluster-size distribution. Independent-group exact binomial intervals are appropriate only when the independent sampling unit and event definition support that assumption.
- For rare/zero observed events, show exact one-sided upper bounds when independence is defensible, otherwise cluster-based bounds/sensitivity. A zero observed error is not zero risk. If no events occur in a small sample, state the interval and low power explicitly.
- Report absolute risk differences, workload differences and confidence intervals, not only p-values. Keep scores and thresholded actions separate.

## Hypothesis tests and multiplicity

- Primary confirmatory comparisons use two-sided paired group-level contrasts unless a directional alternative is explicitly justified and frozen before data access. Family-wise error rate is 0.05 across the declared primary endpoints; apply Holm correction. Secondary and subgroup analyses are descriptive/exploratory unless separately powered and registered.
- Report effect sizes, paired estimates, 95% confidence intervals, adjusted p-values where used, and all tested comparisons. No post-hoc cherry-picking or unreported ablation selection.
- Distinguish confirmatory independent-test analyses from exploratory synthetic and Generator C analyses. C remains `POST_UNBLINDING_EXPLORATORY` regardless of later analysis.

## Power and sample-size plan

Before confirmatory collection, obtain from the domain risk owner (a) a minimum practically meaningful change in critical-miss risk/workload, (b) approved epsilon and acceptable confidence level, (c) anticipated group-level variance/prevalence and (d) feasible review volume. Use a separate blinded pilot or historical permitted data to estimate cluster variance and event prevalence. As a **provisional planning convention only**, target at least 80% power at two-sided alpha 0.05 for the smallest prespecified meaningful paired effect; confirm or replace these values before registration, and inflate for cluster design, unresolved labels and multiplicity. Publish assumptions/code before opening the final test. The numerical sample size is **not estimable from current evidence** and remains pending; do not invent a convenient N.

## Threshold and risk-control analysis

Select probability calibration and any action threshold only on the dedicated calibration partition, under the preapproved policy. Do not select on locked test or Generator C. Optimize action workload subject to a one-sided 95% upper confidence bound on the predeclared case-level critical-miss risk. Record `RISK_THRESHOLD_PENDING_DOMAIN_APPROVAL` until the domain owner sets epsilon. If no candidate satisfies the bound, report `NO_CERTIFIED_OPERATING_POINT`.

Conformal/selective-risk guarantees require explicit sampling/exchangeability or a valid shift-aware procedure. Their assumptions are not presumed under generator, policy, temporal or institutional shift. Report calibration and evaluation distributions, shift, group dependence, and guarantee scope. Do not extend synthetic guarantees to bank deployments.

## Missingness, unresolved labels and subgroup analyses

- Do not impute unknown currency, identity, source validity, period or annotation labels as negative.
- Primary endpoint denominators include only items with adjudicated targets appropriate for that endpoint; report eligibility coverage and excluded/unknown counts next to results.
- Predeclare source, template, time, policy, extraction, provenance, entity and prevalence strata. Report worst-group estimates and uncertainty; treat post-hoc cells as exploratory.
- Report reviewer agreement, unresolved frequency, trace failure and policy-specific exclusions. Sensitivity analysis may bracket unresolved cases as all positive/all negative only when the interpretation is clearly labeled as bounds, not accepted truth.

## Reporting checklist

Publish the frozen protocol/hash, manifests, command and environment log, all exclusions and denominators, model/config hashes, thresholds, paired contrasts, intervals, negative results, multiplicity adjustments, and deviations. Do not mark a registration sealed unless a timestamped independent freeze precedes test-label access.
## Sample design and multiplicity

No target-population prevalence, approved epsilon, minimum useful effect, cluster size, expected miss rate, or paired discordance rate is currently available. Do not state a definitive sample size. Use the parameterized calculations and zero-event caveat in `SAMPLE_SIZE_AND_POWER_PLAN.md`. For future confirmatory work use customer/economic-group resampling (>=2,000 paired bootstrap replicates as a starting proposal), exact independent-group intervals when units/assumptions permit, and Holm adjustment across the pre-registered primary family. Show raw support and event counts. A zero observed miss does not prove zero risk.
