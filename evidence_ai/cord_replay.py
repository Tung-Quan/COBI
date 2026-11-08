"""Verify the locked receipt release and compute a document-bootstrap interval."""
import json

import numpy as np
import torch
from safetensors.torch import load_file
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3TokenizerFast

from evidence_ai.cord import BASE, OUT, RAW, checksum, cohort, encode, evaluate
from ml.contracts import sha, write_json


def main():
    torch.set_num_threads(4)
    def read(name):
        return json.loads((OUT / name).read_text())

    report = read("report.json")
    manifest = read("model_manifest.json")
    provenance = read("provenance.json")
    assert read("release.json")["report_sha256"] == sha(OUT / "report.json")
    for name, digest in manifest["base_file_sha256"].items():
        assert checksum(BASE / name) == digest
    adapter = OUT / "adapter.safetensors"
    assert sha(adapter) == manifest["adapter_sha256"]
    config = manifest["config"]
    names = manifest["labels"]
    paths = sorted((RAW / "cord").glob("test-*.parquet"))
    assert all(checksum(path) == provenance["shard_sha256"][path.name] for path in paths)
    records = cohort(paths, read("split_lock.json")["official_split_row_indices"]["test"])
    tokenizer = LayoutLMv3TokenizerFast.from_pretrained(BASE, local_files_only=True)
    encoded, refs = encode(records, tokenizer, {name: i for i, name in enumerate(names)}, config["max_tokens"])
    model = LayoutLMv3ForTokenClassification.from_pretrained(BASE, local_files_only=True, use_safetensors=True,
                                                             num_labels=len(names))
    model.load_state_dict(load_file(adapter), strict=False)
    measured = evaluate(model, encoded, refs, names, config["batch_size"], include_document_counts=True)
    counts = np.asarray(measured.pop("document_counts"))
    assert measured["counts"] == report["test"]["counts"]
    assert measured["exact_field_micro_f1"] == report["test"]["exact_field_micro_f1"]
    draws = np.random.default_rng(73).integers(len(counts), size=(1000, len(counts)))
    tp, fp, fn = counts[draws].sum(axis=1).T
    result = {"documents": len(counts), "exact_field_micro_f1": measured["exact_field_micro_f1"],
              "ci95": np.quantile(2 * tp / (2 * tp + fp + fn), [.025, .975]).tolist(),
              "replicates": 1000, "seed": 73, "unit": "receipt",
              "scope": "Conditional on one seed, frozen adapter and sampled public receipts"}
    write_json(OUT / "replay_uncertainty.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
