# Dataset and Code License Audit

**Checked:** 2026-11-11. This is a discovery audit, not legal advice or permission to use data. A repository code license does not automatically license embedded financial filings, third-party provider output, or benchmark annotations.

| Resource | Code/repository license evidence | Dataset/source-data status | Research reuse decision |
|---|---|---|---|
| FinFIRST V1 | Hugging Face card declares Apache-2.0 for the dataset release | Card says tasks use publicly accessible sources and reports expert-authored/verified tasks; terms for each linked web source are not individually audited | Card license is not source-level permission; review underlying source and attribution conditions before redistribution or reuse outside the card terms |
| HC-RAG / Multi-Doc-2025 | Paper is on arXiv; dataset card declares CC BY 4.0 | Card identifies SEC EDGAR filings; source filings/derived annotations have separate provenance and conditions | `PARTIAL`; verify exact release revision and derivative/source terms before redistribution |
| FinAgent Benchmark v1.1.1 | Dataset card declares MIT; paper is marked under review | Card claims SEC filings are public domain; card also records author anonymity and row-level gold repairs | `PARTIAL`; verify pinned release revision, source rights, and eventual paper/data terms |
| EvidenceLens | arXiv paper metadata states CC0; IEEE VIS 2026 program lists the short paper | No benchmark dataset license assessed | Paper license does not license any future/source evidence corpus; no data reuse inferred |
| FinBalance | Official GitHub README separates Apache-2.0 code from data license | Generated benchmark records, artifacts, labels, manifests and human verification are declared CC BY 4.0; provider outputs have separate terms | Potentially reusable with attribution after reviewing exact `DATA_LICENSE.md` and every included source/provider condition |
| FinDVer | Official repository identifies MIT license | Author README describes three subsets and says test labels were released in July 2026, but no separate dataset license was verified. Underlying SEC filings and the annotation/data bundle have rights distinct from code | Do not infer full dataset reuse rights from MIT code label; inspect exact data files/source notices and obtain clarification before redistribution |
| FinED-Bench | Checked official repository page showed no root `LICENSE` entry | Data and source-document redistribution terms not verified; ACL article license is not a dataset license | `NOT_CLEARED` pending author/repository clarification and source rights review |
| FinAuditing | Official repository states code is MIT | README directs users to individual Hugging Face dataset cards, each with its own license; filings/XBRL inputs have additional provenance/terms | Review each exact card/version and underlying filing terms before redistribution |
| FinVerBench | Paper says code/benchmark are public; exact repository license was not verified in checked primary page | SEC source filings plus derived perturbations/labels; reuse terms not established here | `NOT_CLEARED` pending repository/data-card and source-rights inspection |
| FinDoc-RAG | ACL paper available | Source documents are from UBS entities; a public paper/PDF is not evidence that the underlying document collection is redistributable | Treat as paper-only; request rights/terms before data reuse |
| When FEVER Meets Finance | ACL paper available | Official code/data license was not verified in this run; 10-K source and annotation rights are separate | `NOT_CLEARED` pending repository and source review |
| FinQA / TAT-QA | Official papers available; repository data/code terms were not audited in this pass | Public availability is not equivalent to unrestricted redistribution; derived financial-report content may carry conditions | Verify exact repository and dataset version before reuse |
| FinanceBench | Official GitHub repository was identified in prior project records; no license file verified in this run | Dataset-card terms and filing rights not verified against an authoritative current card | `NOT_CLEARED`; do not rely on secondary license aggregators |
| FinED/FIND and general papers | ACL paper text uses ACL publication terms | Article license covers article text, not automatically the released dataset or source documents | Separate dataset permission check required |

## Rules for a future COBI dataset

Record source document, source URL or custodian, acquisition date, applicable license/contract, derivative status, consent/legal basis, permitted processing, retention and deletion requirements, publication/redistribution permissions, and hashes. Keep data rights at document and annotation level. Do not copy third-party PDFs into the COBI release solely because the paper is open access. Real borrower data requires institutional/privacy/security approval and data minimization before intake.

## Additional primary references

- FinFIRST V1 dataset card: https://huggingface.co/datasets/inclusionAI/FinFIRST
- HC-RAG / Multi-Doc-2025 paper and card: https://arxiv.org/html/2608.12335 and https://huggingface.co/datasets/Anonymous-Team-HC-RAG/Multi-doc-2025
- FinAgent Benchmark v1.1.1 dataset card: https://huggingface.co/datasets/finagent-benchmark/finagent-benchmark
- EvidenceLens paper: https://arxiv.org/html/2606.23724

## Primary references

- FinBalance repository license statement: [official repository](https://github.com/Devansh1105/finbalance)
- FinDVer repository: [official repository](https://github.com/yilunzhao/FinDVer)
- FinED-Bench repository: [official repository](https://github.com/hedyHe/FinED-Bench)
- FinAuditing repository: [official repository](https://github.com/The-FinAI/FinAuditing)
- FinDoc-RAG paper: [ACL Anthology](https://aclanthology.org/2025.finnlp-2.9/)
