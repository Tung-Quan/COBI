"""Research-only LayoutLMv3 receipt field extraction on pinned CORD v2 splits."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import file_digest, sha256
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import torch
from safetensors.torch import load_file, save_file
from torch.utils.data import DataLoader
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3TokenizerFast

from ml.contracts import ROOT, sha, write_json

RAW = ROOT / "data/raw/evidence-v3"
PROTOCOL = Path(__file__).with_name("cord_protocol.json")
BASE = RAW / "layoutlmv3"
OUT = ROOT / "reports/evidence-v3/cord-extraction"
CORD_URL = "https://huggingface.co/datasets/naver-clova-ix/cord-v2"
BASE_URL = "https://huggingface.co/microsoft/layoutlmv3-base"


def checksum(path):
    with path.open("rb") as file:
        return file_digest(file, "sha256").hexdigest()


def read_words(annotation):
    width = annotation["meta"]["image_size"]["width"]
    height = annotation["meta"]["image_size"]["height"]
    tokens, boxes, tags = [], [], []
    for line in annotation["valid_line"]:
        first = True
        for word in line["words"]:
            token = word["text"].strip()
            if not token:
                continue
            quad = word["quad"]
            x = [quad[f"x{i}"] for i in range(1, 5)]
            y = [quad[f"y{i}"] for i in range(1, 5)]
            box = [int(1000 * min(x) / width), int(1000 * min(y) / height),
                   int(1000 * max(x) / width), int(1000 * max(y) / height)]
            boxes.append([min(1000, max(0, value)) for value in box])
            tokens.append(token)
            if word.get("is_key", False) in (True, 1, "1"):
                tags.append("O")
                first = True
            else:
                tags.append(("B-" if first else "I-") + line["category"])
                first = False
    return tokens, boxes, tags


def cohort(paths, selected):
    rows = []
    offset = 0
    for path in paths:
        parquet = pq.ParquetFile(path)
        end = offset + parquet.metadata.num_rows
        indexes = {i - offset for i in selected if offset <= i < end}
        if indexes:
            batch_offset = 0
            for batch in parquet.iter_batches(batch_size=12, columns=["image", "ground_truth"]):
                for index in sorted(i - batch_offset for i in indexes if batch_offset <= i < batch_offset + batch.num_rows):
                    annotation = json.loads(batch.column(1)[index].as_py())
                    image_bytes = batch.column(0)[index].as_py()["bytes"]
                    rows.append((sha256(image_bytes).hexdigest(), read_words(annotation)))
                batch_offset += batch.num_rows
        offset = end
    return rows


def encode(rows, tokenizer, label_map, limit):
    result, references = [], []
    for image_id, (words, boxes, gold) in rows:
        encoded = tokenizer(words, boxes=boxes, truncation=True, max_length=limit,
                            padding="max_length", return_tensors="pt")
        aligned, word_positions, prev = [], [], None
        for token_index, word_index in enumerate(encoded.word_ids()):
            if word_index is not None and word_index != prev:
                word_positions.append((token_index, word_index))
                aligned.append(label_map.get(gold[word_index], -100))
            else:
                aligned.append(-100)
            prev = word_index
        result.append({key: value.squeeze(0) for key, value in encoded.items()} | {"labels": torch.tensor(aligned)})
        references.append((image_id, gold, word_positions))
    return result, references


def entities(tags):
    spans = set()
    kind, start = None, 0
    for i, tag in enumerate([*tags, "O"]):
        if kind and tag == "I-" + kind:
            continue
        if kind:
            spans.add((kind, start, i))
        kind, start = (None if tag == "O" else tag[2:]), i
    return spans


def f1(tp, fp, fn):
    return 2 * tp / max(1, 2 * tp + fp + fn)


def evaluate(model, encoded, reference, names, batch_size, *, include_document_counts=False):
    model.eval()
    counts = Counter()
    per_label = {}
    losses = []
    document_counts = []
    index = 0
    with torch.inference_mode():
        for batch in DataLoader(encoded, batch_size=batch_size):
            output = model(**batch)
            if torch.isfinite(output.loss):
                losses.append(float(output.loss))
            for ids in output.logits.argmax(dim=-1):
                _, gold, mapping = reference[index]
                index += 1
                predicted = ["O"] * len(gold)
                for token_index, word_index in mapping:
                    predicted[word_index] = names[int(ids[token_index])]
                counts.update(words=len(gold), visible_words=len(mapping), unknown_words=sum(tag not in names for tag in gold),
                              word_correct=sum(p == g for p, g in zip(predicted, gold)))
                truth, guess = entities(gold), entities(predicted)
                if include_document_counts:
                    document_counts.append([len(truth & guess), len(guess - truth), len(truth - guess)])
                for key, values in (("tp", truth & guess), ("fp", guess - truth), ("fn", truth - guess)):
                    counts[key] += len(values)
                    for label, _, _ in values:
                        per_label.setdefault(label, Counter())[key] += 1
    result = {
        "documents": len(encoded), "exact_field_micro_f1": f1(counts["tp"], counts["fp"], counts["fn"]),
        "exact_field_precision": counts["tp"] / max(1, counts["tp"] + counts["fp"]),
        "exact_field_recall": counts["tp"] / max(1, counts["tp"] + counts["fn"]),
        "word_tag_accuracy_including_truncation": counts["word_correct"] / counts["words"],
        "cross_entropy_labeled_tokens": float(np.mean(losses)),
        "counts": dict(counts),
        "field_metrics": {key: {"f1": f1(value["tp"], value["fp"], value["fn"]),
                                "gold": value["tp"] + value["fn"], "predicted": value["tp"] + value["fp"]}
                          for key, value in sorted(per_label.items())},
    }
    if include_document_counts:
        result["document_counts"] = document_counts
    return result


def run(out, threads):
    config = json.loads(PROTOCOL.read_text())
    torch.set_num_threads(threads)
    torch.manual_seed(config["seed"])
    rng = np.random.default_rng(config["seed"])
    shards = {split: sorted((RAW / "cord").glob(split + "-*.parquet")) for split in config["cohort_sizes"]}
    totals = {name: sum(pq.ParquetFile(path).metadata.num_rows for path in paths) for name, paths in shards.items()}
    if totals != {"train": 800, "validation": 100, "test": 100}:
        raise ValueError(f"Official CORD shard totals do not match: {totals}")
    selections = {name: sorted(rng.choice(totals[name], n, replace=False).tolist())
                  for name, n in config["cohort_sizes"].items()}
    hashes = {path.name: checksum(path) for paths in shards.values() for path in paths}
    base_files = ("config.json", "model.safetensors", "preprocessor_config.json", "tokenizer_config.json", "vocab.json", "merges.txt")
    base_hashes = {filename: checksum(BASE / filename) for filename in base_files}
    write_json(out / "provenance.json", {
        "dataset": CORD_URL, "license": "CC BY 4.0", "dataset_revision": config["receipt_revision"],
        "shard_sha256": hashes, "schema": ["image", "ground_truth"], "official_split_sizes": totals,
        "model_source": BASE_URL, "model_license": "CC BY-NC-SA 4.0", "model_revision": config["model_revision"],
        "base_file_sha256": base_hashes, "base_use": "non-commercial research only",
    })
    write_json(out / "split_lock.json", {"protocol_sha256": sha(PROTOCOL), "official_split_row_indices": selections,
                                       "split_sizes": config["cohort_sizes"], "seed": config["seed"]})
    train, valid = (cohort(shards[name], selections[name]) for name in ("train", "validation"))
    assert not ({key for key, _ in train} & {key for key, _ in valid})
    categories = sorted({tag[2:] for _, (_, _, tags) in train for tag in tags if tag != "O"})
    names = ["O", *(prefix + label for label in categories for prefix in ("B-", "I-"))]
    label_map = {label: index for index, label in enumerate(names)}
    tokenizer = LayoutLMv3TokenizerFast.from_pretrained(BASE, local_files_only=True)
    et, _ = encode(train, tokenizer, label_map, config["max_tokens"])
    ev, rv = encode(valid, tokenizer, label_map, config["max_tokens"])
    model = LayoutLMv3ForTokenClassification.from_pretrained(BASE, local_files_only=True, use_safetensors=True,
                                                             num_labels=len(names))
    model.requires_grad_(False)
    model.layoutlmv3.encoder.layer[-1].requires_grad_(True)
    model.classifier.requires_grad_(True)
    trainable = {key: value for key, value in model.named_parameters() if value.requires_grad}
    opt = torch.optim.AdamW(trainable.values(), lr=config["learning_rate"], weight_decay=config["weight_decay"])
    loader = DataLoader(et, batch_size=config["batch_size"], shuffle=True,
                        generator=torch.Generator().manual_seed(config["seed"]))
    checkpoint = out / "adapter.safetensors"
    best, best_epoch, history = -1.0, 0, []
    for epoch in range(1, config["epochs"] + 1):
        model.train()
        norms, train_loss = [], []
        for batch in loader:
            opt.zero_grad(set_to_none=True)
            loss = model(**batch).loss
            loss.backward()
            norms.append(float(torch.nn.utils.clip_grad_norm_(trainable.values(), 1.0, error_if_nonfinite=True)))
            opt.step()
            train_loss.append(float(loss.detach()))
        metrics = evaluate(model, ev, rv, names, config["batch_size"])
        improved = metrics["exact_field_micro_f1"] > best
        if improved:
            best, best_epoch = metrics["exact_field_micro_f1"], epoch
            save_file({key: value.detach().cpu().contiguous() for key, value in trainable.items()}, checkpoint)
        stop = epoch - best_epoch >= config["patience"]
        history.append({"epoch": epoch, "training_loss": float(np.mean(train_loss)), "validation": metrics,
                        "gradient_l2_preclip_mean": float(np.mean(norms)), "gradient_l2_preclip_max": max(norms),
                        "learning_rate": config["learning_rate"], "checkpoint_sha256": sha(checkpoint),
                        "best_epoch": best_epoch, "decision": "STOP_PATIENCE" if stop else "BEST" if improved else "CONTINUE"})
        write_json(out / "training_history.json", history)
        print(f"CORD epoch {epoch}: validation exact field F1={metrics['exact_field_micro_f1']:.5f}", flush=True)
        if stop:
            break
    adapter = load_file(checkpoint)
    assert set(adapter) == set(trainable)
    model.load_state_dict(adapter, strict=False)
    write_json(out / "model_manifest.json", {
        "model": BASE_URL, "license": "CC BY-NC-SA 4.0", "variant": config["trainable"], "base_revision": config["model_revision"],
        "base_file_sha256": base_hashes, "adapter_sha256": sha(checkpoint), "labels": names,
        "config": config, "best_epoch": best_epoch, "trainable_parameters": sum(p.numel() for p in trainable.values()),
    })
    with (out / "test_opened.txt").open("x", encoding="utf-8") as file:
        file.write(datetime.now(timezone.utc).isoformat() + "\n")
    test = cohort(shards["test"], selections["test"])
    assert not ({key for key, _ in test} & {key for key, _ in [*train, *valid]})
    ex, rx = encode(test, tokenizer, label_map, config["max_tokens"])
    result = evaluate(model, ex, rx, names, config["batch_size"])
    write_json(out / "report.json", {
        "status": "PUBLIC_RECEIPT_EXTRACTION_PILOT", "scope": config["scope"], "validation": history[best_epoch - 1]["validation"],
        "test": result, "cohorts": config["cohort_sizes"], "labels": names, "best_epoch": best_epoch,
        "model_inputs": "Dataset-supplied annotated words and bounding boxes. No images, OCR detector or unannotated background words.",
    })
    write_json(out / "release.json", {"report_sha256": sha(out / "report.json")})
    print(f"CORD locked receipt test exact field F1={result['exact_field_micro_f1']:.6f}, n={len(test)}.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    run(args.out, args.threads)


if __name__ == "__main__":
    main()
