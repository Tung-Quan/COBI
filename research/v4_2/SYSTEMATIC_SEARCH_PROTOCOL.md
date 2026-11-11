# Systematic Search Protocol and Screening Record

**Search/screen date:** 2026-11-11 (Asia/Saigon)  
**Status:** `SCOPED_SYSTEMATIC_SEARCH_AND_FIRST_SCREEN_COMPLETE; INDEPENDENT_SCREEN_AND_EXHAUSTIVE_NOVELTY_REVIEW_PENDING`  
**Purpose:** map prior art relevant to semantic financial evidence verification, reconciliation, time/provenance, document attribution, uncertainty, annotation quality and review-risk evaluation.

## Scope and sources

The scoped search covers English-language peer-reviewed papers, preprints with inspectable methods, benchmark/data papers and primary dataset cards posted by 2026-11-11. It includes financial claim/document verification, cross-document reconciliation, evidence-grounded financial QA, temporal validity, provenance, attribution, selective review, benchmark construction, annotation and leakage/reproducibility. General methods are retained only when they inform evaluation or risk-control design.

Sources searched and opened: web-indexed search results; ACL Anthology proceedings and PDFs; arXiv abstracts and HTML; publisher full texts; IEEE VIS program/preprint pages; and author/maintainer dataset cards or repositories on Hugging Face/GitHub. Search-result snippets were only leads. Claims in the matrix cite primary records or maintained dataset cards.

## Exact query record

The original search pass used:

- `"financial evidence" LLM benchmark contradiction document attribution`
- `"multi-document" financial reconciliation benchmark evidence source documents LLM`
- `financial documents contradiction detection temporal validity provenance benchmark`
- `finance evidence verification human review selective risk workload benchmark`
- `site:aclanthology.org/2026 "On Finding Inconsistencies in Documents" FIND`
- `site:aclanthology.org/2026.acl-long.492 RFC-BENCH financial misinformation`
- `site:arxiv.org/html/2605.29586 FinVerBench`
- `site:aclanthology.org/2025.finnlp FinDoc-RAG financial documents`
- `site:github.com "FinVerBench" "LICENSE"`
- `site:huggingface.co/datasets "FinDVer" financial`
- `site:huggingface.co/datasets "FinED-Bench"`
- `site:github.com/The-FinAI/FinAuditing "LICENSE"`

A close-overlap follow-up pass added:

- `site:aclanthology.org/2026.finnlp-1.42 financial claim evidence benchmark`
- `"financial claim evidence" benchmark authoritative timely source verification`
- `site:arxiv.org financial financial-document claim-evidence matrix provenance 2026`
- `site:huggingface.co/datasets financial benchmark source evidence rubric verification 2026`
- `"multi-document" financial filings evidence graph benchmark 2026`

The screening ledger has 28 entries: 26 unique studies/resources plus two explicit version/duplicate views. It records included studies, a duplicate dataset-card view, screening basis, full-text/data-card access, license status and scope notes. FinDVer is deliberately represented by separate publication-version rows because the authoritative pages disagree on counts.

## Eligibility and screening

Include a source if its task or evaluation materially concerns at least one of: financial claim/document verification; multi-document reconciliation; numerical consistency; temporal validity; source provenance/attribution; financial evidence QA; selective review/abstention; benchmark construction/annotation; or evaluation leakage/reproducibility. Record task unit, target, gold source and data/code license separately. Abstract-only and dataset-card-only records can bound scope but cannot support uninspected methods claims.

Exclude general financial prediction with no evidence semantics, demonstrations without a defined task or evaluation, secondary summaries where primary sources are available, lexical-only matches and duplicate versions. Deduplicate by DOI, ACL Anthology ID, arXiv ID and normalized title/authors; retain canonical study rows and explicit version comparisons. License review is separate from scientific inclusion.

## Screening outcome and reproducibility limits

The 28 ledger entries are the retained relevant set from the executed query batches plus directly followed primary-source links. Search interfaces returned ranked results but did not provide a stable export with complete result counts; therefore the retrieval denominator, total number screened out, and a PRISMA-style flow count cannot be reconstructed. No second independent screener participated. The screening decisions are a first-pass single-reviewer record, not an independently adjudicated systematic review.

Coverage now includes close 2026 overlaps: FinBalance, FinAuditing, FinED-Bench, FinDVer, FinVerBench, RFC-Bench, When FEVER Meets Finance, TempFinRAG, HC-RAG/Multi-Doc-2025, FinFIRST, FinAgent and EvidenceLens. The first-pass review is sufficient to reject broad novelty claims and bound the current gap assessment; it is not sufficient to establish novelty. The status remains `NOVELTY_UNESTABLISHED` until an independent screener repeats screening, data/task/license overlap is resolved, and a permitted independent borrower-case benchmark exists.

## Outputs

- `LITERATURE_SCREENING_LOG.csv`: record-level inclusion and evidence status.
- `PRIOR_ART_MATRIX.md`: task-unit comparison and bounded implications.
- `DATASET_LICENSE_AUDIT.md`: code/data/source-rights distinctions; not legal clearance.
- `RESEARCH_GAP_AND_NOVELTY.md` and `NOVELTY_CLAIM_REGISTER.md`: falsifiable, unestablished candidate distinctions.
