# V4 Validation Report

## Passed

- Protected V2/V3 artifact audit: **109/109 hashes verified**; no baseline mismatch.
- V3 frozen replay and customer-group partition checks: **PASS**; the locked test report was reproduced and customer groups do not overlap across train, validation, calibration, and test partitions.
- Generator B deterministic regeneration, data-layer hashes, observed schema, and feature-contract checks: **PASS**; 1,920 cases, 960 groups, 7,744 documents, 0 incompatible documents.
- V4 and benchmark unit tests: **8 passed** (`evidence_ai/tests/test_v4.py` and `ml/tests`).
- Direct V4 route-contract invocation: **PASS**; verified summary integrity, four models, blocked validation status, false routing/approval authority, and a whitelisted SVG figure.
- Frontend production build: **PASS** (`tsc -b && vite build`; 1,635 modules transformed).
- Final artifact manifest: **95/95 files verified**, with no checksum errors.

## Backend HTTP integration limitation

The FastAPI `TestClient` suite could not initialize its Windows asyncio event loop in this sandbox. The captured stack trace stops in Python's Windows Proactor loop while creating the socket pair (`socket.py` `accept` / `asyncio.windows_events`). The default pytest temporary directory was also outside the writable sandbox; rerunning with a workspace-local `--basetemp` resolved that filesystem issue, but not the event-loop socket issue. The affected HTTP integration tests were interrupted rather than reported as passing.

The route handler itself was invoked directly and passed its integrity and authorization assertions. That direct invocation does **not** replace an HTTP-level integration test. Browser E2E was not run because this environment could not start the local HTTP test client needed for the isolated frontend/backend workflow.

## Disposition

Research outputs remain read-only and **`EVIDENCE_AI_VALIDATION_BLOCKED`**. Routing and approval authorization remain false. No V4 training, recalibration, threshold tuning, bank validation, or human-reviewed labeling was performed.
