# Sample-Size and Power Plan

**Status:** parameterized design only; no sample size is approved.  
**Missing inputs:** target prevalence, independent customer/economic-group count, within-group correlation, expected paired discordance, baseline rates, minimum practically important effect, alpha/power, missing/unknown-label fraction, approved epsilon and shift-stratum sizes.

## Critical-miss risk with zero observed events

For `n` independent critical evaluation units with zero observed misses, a one-sided exact 95% binomial upper bound is `1 - 0.05^(1/n)`. To make that upper bound no greater than an externally chosen `epsilon`, the minimum independent positive units is `ceil(log(0.05)/log(1-epsilon))`. Illustrative arithmetic only:

| Illustrative epsilon (not approved) | Critical independent units with zero observed misses |
|---:|---:|
| 5% | 59 |
| 2.5% | 119 |
| 1% | 299 |

These counts assume independent Bernoulli units and no multiplicity/shift adjustment. If cases cluster within customers, the effective independent unit is the group or a justified cluster model; these figures must not be used as the final bank sample requirement. Any observed miss increases the required support and bound.

## Paired model comparison

For a paired primary metric, estimate the two discordant probabilities `p10` and `p01` on an independent pilot, with target absolute difference `delta = |p10-p01|`. A rough paired-proportion normal approximation is:

`n_pairs ≈ (z_(1-alpha*/2) + z_(1-beta))^2 * (p10 + p01 - (p10-p01)^2) / delta^2`.

This approximation is a planning aid only. `alpha*` reflects the pre-registered multiplicity family; `1-beta` is approved power. Final planning should simulate the actual group-clustered paired bootstrap or exact design, expected unknown-label exclusions and group sizes. Use a development/pilot sample separate from the locked test, and do not use Generator C to estimate confirmatory effects.

## Required plan before enrollment

1. Domain owner sets the permissible epsilon and acceptable failure behavior.
2. Research lead specifies primary endpoint, minimum useful difference, alpha, desired power and multiplicity family.
3. Statistician obtains pilot prevalence, cluster-size distribution, intraclass correlation, missingness and paired discordance from data not used for final evaluation.
4. Simulate power and risk-bound coverage under ID and planned shift strata, including group bootstrap and unresolved-label rates.
5. Freeze the resulting sample/split plan before test-label access and report sensitivity analysis over plausible inputs.
