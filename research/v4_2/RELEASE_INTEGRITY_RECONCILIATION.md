# Release Integrity Reconciliation

**Review date:** 2026-11-11 (Asia/Saigon)  
**Repository:** `C:\disk D\COBI`, branch `main`, HEAD `7f5eff1e46a8f0c03a36a11d6892231bf4927182`  
**Disposition:** `OPEN_PENDING_RELEASE_OWNER_APPROVAL`  
**Scope:** the two requested mismatches, plus a historical source-manifest inconsistency found while establishing the V4.1 baseline.

This is a read-only release review. Protected manifests, product files and report bytes were not changed to make checksum guards pass. Canonical V4 Git path case is `reports/evidence-v4/final_manifest.json` (lowercase); Windows path lookup is case-insensitive, but the audit helper now preserves repository case.

## A. Requested mismatches

| Artifact | Expected release digest | Current digest | Historical provenance and applicable baseline | Finding and disposition |
|---|---|---|---|---|
| `frontend/src/EvidenceResearch.tsx` | `b3f7b74ec8ab8d1c773c970f5f31d3f2181c1f539fb968d37ab0fb4d7eff0947` | `54da9de3afae412a20a58e47578fd9ca89276f0f85c87c72bf02d9f21dd18db9` | The 96-entry V4 baseline is `reports/evidence-v4/final_manifest.json`, committed in `683b110e8f735ba838fbb8b268ce8d4c3dfe3aa0` on 2026-11-08 22:53:09 +07:00. The UI file entered Git in `93f17b07ebd3356b04dc1df0041fc3656a6e3888` at 22:51:55 +07:00. At the V4 manifest commit, the file had Git blob `8828fba0c345c9862f64e749f472ed75a61f972c`, the same blob as current HEAD; it did not change in the subsequent V4 documentation commit. Its only path-history commit is the UI commit. The 109-entry `ARTIFACT_MANIFEST.json` is a distinct inventory. | The mismatch already existed in the committed V4 release snapshot: that same tree contains the current UI blob while `final_manifest.json` expects another digest. Evidence supports a stale/different-source-state manifest entry, but cannot distinguish a stale generation input from an earlier unrecorded UI version. The expected bytes were not recovered from the file's Git history or the 34 unreachable Git blobs inspected. **Open; 95/96 remains.** |
| `reports/evidence-v4.1/TONG_HOP_COBI_V4_1.md` | `be5b8776c9b0e1186d78e4c331ba22c10a3edd808278e5836b4df18d2f2d57c7` (19,107 bytes) | `f40b28f712dba9e7bc061f9a9f0434ef4d883aa1cbabc42cc66a955739278a40` (19,297 bytes) | The current modified worktree `RELEASE_MANIFEST.json` records the expected digest. The separate untracked `FINAL_MANIFEST.json` records the same digest and 19,107-byte size. The 2026-11-11 filesystem metadata gives TONG creation 16:15:31 and last write 16:17:36; the current `RELEASE_MANIFEST.json` last write is 16:15:51 and `FINAL_MANIFEST.json` 16:15:52 (+07:00). TONG has no Git history and was untracked before this closeout. | The 190-byte size increase and later file-write time are consistent with a report edit after the two manifest records captured the 19,107-byte version. Timestamps do not identify the editor, prove exact content, or show approval; the earlier bytes were not recovered. The committed V4.1 manifest predates TONG and is a separate 14-source/19-artifact snapshot. The checked-in `scripts/finalize_v4_1_reporting.py` public-artifact list does not generate/include this TONG report. **Open; current expanded worktree manifest remains 14/14 source and 51/52 artifact matches, and the API guard must continue to fail closed.** |

## B. Release-manifest snapshots and additional historical note

These records are separate and must not be silently substituted for one another:

| Snapshot | Scope | Observed result |
|---|---:|---|
| V4 `reports/evidence-v4/final_manifest.json` | 96 artifacts | 95/96 current files match; the only current mismatch is `EvidenceResearch.tsx`. |
| V4 `reports/evidence-v4/ARTIFACT_MANIFEST.json` | 109 inventory entries | 109/109 current files match; this inventory does not override the V4 final-manifest mismatch. |
| V4.1 committed `RELEASE_MANIFEST.json` at `e9102a7e9fb5b79edef1449eb869c7637f2e781f` | 14 sources + 19 artifacts | On the commit's own tree with Git checkout filters applied, 12/14 source digests and 19/19 artifact digests match. The two same-snapshot source mismatches are `EXPERIMENT_PROTOCOL_C.md` and `experiment_protocol_c.json`; those expected digests do not appear in either path's recorded Git history. This is an additional pre-existing manifest inconsistency. |
| V4.1 committed manifest applied to current modified worktree | 14 sources + 19 artifacts | 13/14 sources and 9/19 artifacts match current worktree files. This does not describe the original commit tree. |
| V4.1 current modified worktree `RELEASE_MANIFEST.json` | 14 sources + 52 artifacts | 14/14 sources and 51/52 artifacts match current files; TONG is the single artifact mismatch. |
| V4.1 separate untracked `FINAL_MANIFEST.json` | 101 artifacts | Current check is 100/101; TONG is the single mismatch. The earlier verification log claims 100/100 at a prior snapshot and is stale for the current 101-row manifest. |

The committed V4.1 manifest and current expanded worktree manifest have different contents and scopes. The expanded worktree manifest is itself a pre-existing modification; this closeout did not regenerate or replace it.

## C. Current file/content checks

- `EvidenceResearch.tsx` is tracked and clean at the start and end of this work. It passes the frontend production build. A build is not runtime behavior verification.
- TONG is present and readable, but its authoring provenance and the exact earlier 19,107-byte content are not established. Its scientific claims were not independently re-audited as a release artifact.
- The available E2E script writes synthetic case/review/consent data. No disposable database or `COBI_E2E_URL` was configured, so it was not run.
- The backend API checksum guard rejects the current TONG mismatch. It was not bypassed or weakened.

## D. Reconciliation decision

There is no repository evidence that the release owner authorized replacing either protected baseline, and neither expected historical byte sequence was recovered. Therefore no versioned release reconciliation was authorized or implemented. The exact decision form and selectable actions are in `RELEASE_OWNER_APPROVAL_REQUEST.md`. After a signed decision, an authorized owner can supply/recover the baseline bytes or issue a new versioned package while retaining all previous manifest files; then rerun the existing checksum guards and tests.

## Evidence commands

Historical provenance was checked with `git log --follow`, `git show`, `git rev-parse`, `git ls-tree`, `git cat-file --filters`, manifest JSON inspection, SHA-256/size checks, `git status --short`, and filesystem timestamps. Current counts and exact commands are in `FINAL_VERIFICATION_REPORT.md` and `RUN_LOG.md`.
