# Claims and Limitations

| Claim | Evidence | Safe wording | Limitation |
|---|---|---|---|
| Frozen systems were replayed on V3 | E1 output and V3 release replay | “Retrospective synthetic replay” | Previously inspected test; not confirmatory |
| Generator B differs in implementation | New event-ledger code, hashes, separate data layers | “Independently implemented synthetic challenge” | Independent code does not imply realistic or independent human labels |
| Performance changed between A and B | E1/E2 results and group bootstrap | “Synthetic cross-generator performance changed” | Different prevalence and designed scenarios; no bank inference |
| B4 and B5 expose important failure modes | Scenario metrics and B5 legitimate-document denominator | “Models failed these predeclared synthetic stress tests” | Scenario assumptions may not match real documents |
| E3 explores cost sensitivity | YAML assumptions, cost equation, scenario table | “Illustrative assumption-based simulation” | Not measured cost, quote, savings, or feasibility |
| Research page is non-authoritative | API response, route tests, read-only UI | “No routing or approval authority” | Does not itself prove the upstream bank workflow is safe |

## Disallowed claims

- Bank validated, production ready, safe, fair, compliant, or guaranteed recall.
- Real-world workload reduction or VND savings.
- A model is selected as the best operating policy based on Generator B.
- Human-validated labels or real customer outcomes.

**Disposition:** `EVIDENCE_AI_VALIDATION_BLOCKED` until a separately governed and representative evaluation supports a new decision.
