# Risk Policy Approval Packet

**Decision status:** `RISK_THRESHOLD_PENDING_DOMAIN_APPROVAL`  
**Requested approver:** designated domain/risk policy owner; no identity or approval is presumed.

## Decision requested

Approve or reject a future research tolerance for critical missed cases and the conditions under which a case may receive `NO_FLAG`, `HUMAN_REVIEW` or `REQUEST_MORE_EVIDENCE`. This packet does not authorize lending decisions or product integration.

## Required policy choices

| Decision | Proposed field for approval | Current state |
|---|---|---|
| Target population/workflow and critical case definition | `TBD_BY_DOMAIN_OWNER` | Not specified |
| Critical-miss risk event | Critical case receives `NO_FLAG` | Proposed endpoint; not approved |
| Risk denominator | Critical cases among cleared cases, plus misses/all critical cases | Specified as separate measures; policy meaning needs approval |
| Tolerance `epsilon` | `____` | `RISK_THRESHOLD_PENDING_DOMAIN_APPROVAL` |
| Confidence level and bound | Proposed one-sided 95% UCB | Requires statistical and domain approval |
| Action costs | Review, request-more-evidence, missed critical case, model | Unknown; no savings claim |
| Shift/fallback behavior | No certified point if UCB fails or exchangeability is unsupported | Proposed fail-closed research reporting |
| Unknown/abstention behavior | Preserve UNKNOWN and route to evidence request or review by approved policy | Requires approval |

## Decision record

Reviewer name/role: ______  
Date and policy version: ______  
Decision: `APPROVE_FOR_RESEARCH / REVISE / REJECT / DEFER`  
Approved epsilon and rationale: ______  
Population, exclusions and shift scope: ______  
Failure and escalation behavior: ______

Until completed and signed through the institution's approved process, no operating point may be described as satisfying a risk constraint. A point estimate alone is insufficient; the future test must report an upper confidence bound using a justified group-aware procedure. OOD results do not inherit exchangeability-based conformal guarantees automatically.
