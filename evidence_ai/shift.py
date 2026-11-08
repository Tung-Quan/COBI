"""Separate synthetic domain challenge using frozen V3 models and thresholds."""
from hashlib import sha256

import torch

from evidence_ai.evaluation import scores
from evidence_ai.replay import predict_frozen, read
from evidence_ai.synthetic import DATA, PROTOCOL, generate
from evidence_ai.train import RELEASE
from ml.contracts import canonical, sha, write_json

CHALLENGE = {
    "experiment_id": "evidence-synthetic-v3.0-unseen-format",
    "generator_seed": 1732, "customers": 120, "cases_per_customer": 2,
    "template": "new machine-formatted locale and lower OCR confidence",
    "changes": ["Pipe-separated abbreviated keys and comma-separated amount strings",
                "Subtract 0.15 from observed OCR confidence with floor zero"],
    "evaluation": "Frozen v3.0 predictions, same calibrators and thresholds, no tuning",
}


def main():
    torch.set_num_threads(1)
    out = RELEASE / "synthetic-format-challenge"
    out.mkdir(parents=True, exist_ok=False)
    config = read(PROTOCOL) | CHALLENGE
    cases, gold = generate(config)
    for case, labels in zip(cases, gold, strict=True):
        case["case_key"] = "external-" + case["case_key"]
        case["customer_group"] = "external-" + case["customer_group"]
        labels["case_key"] = case["case_key"]
        for doc, label in zip(case["documents"], labels["documents"], strict=True):
            doc["document_key"] = "external-" + doc["document_key"]
            doc["template"] = "format-challenge"
            doc["ocr_quality"] = max(0., doc["ocr_quality"] - .15)
            doc["text"] = "|".join(f"{key[:2].upper()}:{value:,}" if value is not None else f"{key[:2].upper()}:N/A"
                                   for key, value in doc["values"].items())
            label["document_key"] = doc["document_key"]
            label["observed_payload_sha256"] = sha256(canonical(doc)).hexdigest()
    private = DATA / "format-challenge"
    write_json(private / "observed.json", cases)
    write_json(private / "labels.json", gold)
    write_json(out / "manifest.json", CHALLENGE | {"scope": "SYNTHETIC_TECHNICAL_ONLY",
                                                   "observed_sha256": sha(private / "observed.json"),
                                                   "labels_sha256": sha(private / "labels.json")})
    data, probabilities, _, lock = predict_frozen(cases, gold, RELEASE / "synthetic")
    results = {name: scores(p, data, lock["all_thresholds"][name]) for name, p in probabilities.items()}
    write_json(out / "report.json", {"status": "SYNTHETIC_TECHNICAL_ONLY", "results": results})
    print("Scored independent controlled formatting challenge with frozen models and thresholds.")


if __name__ == "__main__":
    main()
