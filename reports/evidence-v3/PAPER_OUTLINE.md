# Scientific paper outline

**Provisional title** · Evidence-aware document error detection for human review of checkout credit

1. **Abstract.** Describe the separate bank evidence label problem, synthetic engineering trial and public receipt extraction pilot. Report denominators, thresholds and uncertainty. State `EVIDENCE_AI_VALIDATION_BLOCKED`.
2. **Motivation.** Distinguish successful extraction, cross-source disagreement, independently verified error and additional verification required. Explain why a composite evidence quality score cannot provide training truth.
3. **Related work.** Deep Sets supplies the permutation-invariant set operator. Set Transformer offers learned interactions for a sufficiently diverse future sample. LayoutLMv3 provides pretrained document representations. CORD and DocILE supply task-specific extraction labels. None supplies bank material-defect labels.
4. **Data and labeling.** Explain blinded double review, source and as-of verification, adjudication, unknown-label masking, document and template identities, and authorization. Document the generated corruption process and keep its model-observable inputs apart from gold.
5. **Methods.** Define CS_V2, sigmoid calibration, LR, XGBoost and Deep Sets with masked document/field heads. Prespecify chronological customer splits, three optimizer seeds, metric definitions, threshold lock and customer bootstrap.
6. **Results.** Present fixed holdout comparisons and paired intervals. Report negative findings such as XGBoost's advantage over Deep Sets on controlled defects. Present ablations and external synthetic format challenge as descriptive. Keep the CORD exact field F1 on its own task.
7. **Limitations and model risk.** Discuss synthetic generator artifacts, reviewer error, unknowns, drift, dependent documents, label maturity, lack of actual template/customer transfer evidence, confidence conditioning and noncommercial LayoutLMv3 restrictions.
8. **Deployment and governance.** Report how the shadow endpoint refuses unsupported workbench predictions. Review routing/approval remains under deterministic policy and human authority. Define the independent external validation and sign-off required for a future change.
9. **Reproducibility appendix.** Include protocol/code hashes, manifest, group split, training curves, frozen calibrators and exact replay checks. No raw documents are distributed by COBI.

## Primary references

- Zaheer et al. (2017), *Deep Sets*, NeurIPS 30. [Proceedings](https://papers.neurips.cc/paper_files/paper/2017/hash/f22e4747da1aa27e363d86d40ff442fe-Abstract.html)
- Lee et al. (2019), *Set Transformer*, ICML, PMLR 97:3744–3753. [Proceedings](https://proceedings.mlr.press/v97/lee19d.html)
- Huang et al. (2022), *LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking*, ACM Multimedia. [Paper](https://arxiv.org/abs/2204.08387)
- Park et al. (2019), *CORD: A Consolidated Receipt Dataset for Post-OCR Parsing*, NeurIPS Document Intelligence Workshop. [Dataset and author citation](https://github.com/clovaai/cord)
- Šimsa et al. (2023), *DocILE Benchmark for Document Information Localization and Extraction*, ICDAR. [Paper](https://arxiv.org/abs/2302.05658)
- Niculescu-Mizil and Caruana (2005), *Predicting Good Probabilities with Supervised Learning*, ICML. [DOI](https://doi.org/10.1145/1102351.1102430)
