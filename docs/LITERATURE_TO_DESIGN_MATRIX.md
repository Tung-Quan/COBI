# Literature to design matrix

The links point to the papers or owning organizations. The COBI decisions and experiments are project design choices derived from these references.

| Source | Relevant finding | COBI design and experiment | Limitation |
|---|---|---|---|
| [Yeh, UCI 350](https://doi.org/10.24432/C55S3H) | Published Taiwan card history and binary next-month outcome | Preserve UCI lineage and run E1–E3 in a distinct domain | No checkout outcome or application-time index |
| [Lessmann et al. (2015)](https://doi.org/10.1016/j.ejor.2015.05.030) | Comparative credit scoring requires testing across candidate methods and metrics | E1/E2 compare a constant baseline, linear, tree and neural models | One dataset and one outcome horizon |
| [Probability calibration, scikit-learn](https://scikit-learn.org/stable/modules/calibration.html) | Good ranking and calibrated probabilities are separate properties | E3 uses independent calibration and reliability diagrams | No assurance that calibration improves a particular test |
| [Kull et al. (2017)](https://proceedings.mlr.press/v54/kull17a.html) | Calibration family can matter with skewed score distributions | Compare prespecified sigmoid with raw output. Beta calibration reserved for a new study. | No comparative beta result |
| [Wang and Strong (1996)](https://www.jmis-web.org/articles/1002) | Data quality spans multiple dimensions | P4 defines COBI-specific subscores. E4 requires defect labels. | The COBI formula is an operational proposal |
| [CORD](https://github.com/clovaai/cord) | Receipts can benchmark post-OCR extraction | Keep extraction confidence apart from verification and PD | Bank-document verification needs domain-specific labels |
| [Verbraken et al. (2014)](https://doi.org/10.1016/j.ejor.2014.04.001) | Credit classification thresholds have economic tradeoffs | P7/P8 expose economic assumptions and sensitivity | No empirical bank costs, recoveries or margins |
| [Mozannar and Sontag (2020)](https://proceedings.mlr.press/v119/mozannar20b.html) | Deferral can be studied with expert outcomes | P8/P9 support transparent human review and abstention. E5 uses deterministic routing. | No expert-labeled learning-to-defer study |
| [Lakkaraju et al. (2017)](https://www.cs.cornell.edu/home/kleinber/kdd17-selective.pdf) | Selective labels bias evaluation when prior decisions control observability | E6 requires recording selection, censoring and actual action | No reject-inference or causal uplift claim |
| [Kapoor and Narayanan (2023)](https://doi.org/10.1016/j.patter.2023.100804) | Leakage undermines reproducibility and generalization | Lock cohorts, train-fit preprocessing and enforce as-of checks | UCI lacks grouped and chronological evidence |
| [BCBS credit risk principles](https://www.bis.org/publications/202504-guidelines-principles-management-credit-risk) and [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) | Credit and AI risk management depend on controls and documented governance | Versioned policy, artifact scope, human audit and external validation gate | No certification or bank approval implied |
