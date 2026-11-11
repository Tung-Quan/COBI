# Release Owner Approval Request — V4/V4.1 Integrity

**Request status:** `AWAITING_RELEASE_OWNER_DECISION`  
**Purpose:** authorize a provenance-preserving disposition for two open artifact mismatches and note two stale source digests embedded in the committed V4.1 manifest. This request does not alter manifests or checksum guards.

## Evidence reviewed

See `RELEASE_INTEGRITY_RECONCILIATION.md` for commit IDs, baseline paths, expected/current SHA-256 values, file sizes, timestamps, Git state and limits of the provenance evidence.

## Decision A — V4 research UI

- Path: `frontend/src/EvidenceResearch.tsx`
- V4 baseline: `reports/evidence-v4/final_manifest.json` (96 artifacts)
- Baseline expected SHA-256: `b3f7b74ec8ab8d1c773c970f5f31d3f2181c1f539fb968d37ab0fb4d7eff0947`
- Current committed/current-file SHA-256: `54da9de3afae412a20a58e47578fd9ca89276f0f85c87c72bf02d9f21dd18db9`
- Current file equals the Git blob present when the V4 manifest was committed. The expected bytes were not recovered.

Select one:

- [ ] **Preserve the V4 historical baseline and leave the mismatch open.** Acknowledge that the V4 protected manifest does not validate the committed UI file.
- [ ] **Supply the approved 19,652-byte baseline file** matching the expected digest. Authorize a separate, versioned restoration/release action; do not overwrite or edit the frozen manifest.
- [ ] **Authorize a new V4 release version** for the current UI bytes. Preserve the historical V4 manifest unchanged and publish an explicit superseding manifest/release record.
- [ ] **Other written disposition:** ____________________________________________

## Decision B — V4.1 Vietnamese summary report

- Path: `reports/evidence-v4.1/TONG_HOP_COBI_V4_1.md`
- Current expanded worktree `RELEASE_MANIFEST.json` and separate `FINAL_MANIFEST.json` expect SHA-256 `be5b8776c9b0e1186d78e4c331ba22c10a3edd808278e5836b4df18d2f2d57c7` and 19,107 bytes.
- Current file is 19,297 bytes with SHA-256 `f40b28f712dba9e7bc061f9a9f0434ef4d883aa1cbabc42cc66a955739278a40`.
- Filesystem timestamps support, but do not prove, a report edit after those records were written. Git has no TONG history.

Select one:

- [ ] **Preserve the release-manifest baseline and leave the mismatch open.** Keep the API checksum guard failing closed until an authoritative file is supplied.
- [ ] **Supply/identify the approved 19,107-byte report** matching the expected digest. Authorize a separate versioned release action; do not replace historical manifests.
- [ ] **Approve the current 19,297-byte report** and authorize a new versioned package manifest. Preserve previous manifest bytes and record the supersession.
- [ ] **Exclude the report from a future release scope** through an explicitly versioned manifest/schema decision; do not remove it from an existing frozen manifest.
- [ ] **Other written disposition:** ____________________________________________

## Historical V4.1 manifest note

The committed 14-source/19-artifact V4.1 `RELEASE_MANIFEST.json` has two source digests that do not match the same commit tree: `EXPERIMENT_PROTOCOL_C.md` and `experiment_protocol_c.json`. The committed artifacts do match 19/19. If authorizing a new release package, specify whether the new package should use current source bytes and explicitly supersede those two historical source digests. The separate expanded worktree manifest currently records 14/14 sources and 51/52 artifacts.

## Approval record

Release owner name and role: ________________________________________________  
Decision date and timezone: _________________________________________________  
Approved release/version identifier (if applicable): __________________________  
Decision A selection / rationale: ____________________________________________  
Decision B selection / rationale: ____________________________________________  
Historical V4.1 source-manifest note disposition: _____________________________  
Signature or approved ticket/reference: ______________________________________

No implementation action is authorized by this blank request. After the signed record identifies exact approved bytes or a new versioned package, the release owner should authorize that concrete change and require the existing checksum guards and applicable tests to pass.
