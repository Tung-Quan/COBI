"""Validate restricted local annotation JSONL or export its schema."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path

from pydantic import ValidationError

from evidence_ai.annotations import Annotation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", action="store_true")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--cutoff")
    args = parser.parse_args()
    if args.schema:
        print(json.dumps(Annotation.model_json_schema(), indent=2))
        return
    if not args.input or not args.cutoff:
        parser.error("--input and timezone-aware --cutoff are required")
    cutoff = datetime.fromisoformat(args.cutoff)
    if cutoff.tzinfo is None:
        parser.error("--cutoff must include a timezone")
    statuses, eligible = Counter(), Counter()
    seen = set()
    with args.input.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = Annotation.model_validate_json(line)
            except ValidationError:
                parser.error(f"Invalid annotation contract at line {number}")
            key = (record.provenance.document_key, record.target, record.field_key, record.second_document_key)
            if key in seen:
                parser.error(f"Duplicate annotation target at line {number}")
            seen.add(key)
            statuses[record.label_status] += 1
            if record.training_label(cutoff) is not None:
                eligible[record.target] += 1
    print(json.dumps({"status_counts": statuses, "eligible_by_cutoff": eligible, "raw_labels_exported": False}, indent=2))


if __name__ == "__main__":
    main()
