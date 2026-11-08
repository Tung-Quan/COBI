# Judge Q&A

### What exactly does the score predict?
Whether a document contains a material evidence or extraction defect under the defined synthetic/annotation task. It is not default probability, creditworthiness, eligibility, or approval.

### Why use synthetic data?
It allows controlled, reproducible stress scenarios and explicit gold rules. It cannot establish external validity or replace real, adjudicated documents. That limitation is central to the result.

### Why is E1 retrospective?
The V3 test had already been inspected and discussed before V4. We label it retrospective and do not treat its threshold sweep as model selection.

### What is independent about Generator B?
It is implemented as a new event-ledger process and does not call the V3 generator or its format-shift function. Its observed documents, canonical facts, and labels are separate. A first pilot was invalidated after a leakage audit; the corrected generator and amendment are preserved, and only the amended run is reported as confirmatory within the synthetic protocol.

### Why not tune thresholds on B?
That would turn the challenge set into selection data and undermine the portability test. The aim was to evaluate the registered V3 operating point. A future tuning study needs a separate development set and untouched test set.

### Why use customer-group bootstrap?
Two cases from one generated customer share profile-level information. Resampling groups keeps those dependent cases together. The resulting intervals remain conditional on the designed synthetic sample and are not population guarantees.

### Does 90% recall target mean 90% guaranteed recall?
No. It was part of threshold selection on V3 calibration data. It is not a population guarantee and did not hold consistently on Generator B.

### Is the E3 cost saving real?
No. It is an assumption-based simulation using retrospective E1 synthetic rates. Unit costs and volume are configurable assumptions, not bank quotations or measured savings.

### Can the interface change loan outcomes?
No. The V4 research page is read-only. Both routing and approval authorization are false; the production workbench and mandatory gates are not changed by these research artifacts.

### What is the strongest conclusion?
The independent synthetic test exposes serious transfer failures, especially on stale evidence and legitimate discrepancies. The evidence supports a need for a human-reviewed external benchmark, not deployment.

### What is not yet done?
No human review, bank validation, external validation, or V4 model training/tuning. There are no V4 epochs, gradients, or training-loss claims. The status remains `EVIDENCE_AI_VALIDATION_BLOCKED`.
