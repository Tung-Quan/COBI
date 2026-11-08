import json
from datetime import datetime, timezone

import numpy as np
import pytest
import torch
from pydantic import ValidationError

from evidence_ai.annotations import Annotation
from evidence_ai.features import NAMES, encode
from evidence_ai.model import DeepSets
from evidence_ai.synthetic import FIELDS, PROTOCOL, generate, split_cases


def review(key, verdict):
    return {"reviewer_key": key, "verdict": verdict, "reviewed_at": "2026-11-07T13:00:00Z",
            "verification_method": "blind comparison", "evidence_refs": ["restricted-ref"], "reason_code": "test"}


def test_annotation_requires_independent_reviews_and_masks_unverified():
    record = {
        "label_status": "DISPUTED", "target": "material_evidence_error",
        "provenance": {"document_key": "d1", "customer_group_key": "g", "case_key": "c",
                       "template_group_key": "t", "source_system": "restricted", "document_sha256": "a" * 64,
                       "observed_at": "2026-11-07T10:00:00Z", "decision_at": "2026-11-07T12:00:00Z",
                       "access_authorization_ref": "auth-test", "evidence_refs": ["restricted-ref"]},
        "reviews": [review("r1", "PRESENT"), review("r2", "ABSENT")],
    }
    cutoff = datetime(2026, 11, 8, tzinfo=timezone.utc)
    assert Annotation.model_validate(record).training_label(cutoff) is None
    with pytest.raises(ValidationError, match="independent"):
        Annotation.model_validate(record | {"reviews": [review("r1", "PRESENT"), review("r1", "ABSENT")]})
    with pytest.raises(ValidationError, match="separate reviewer"):
        Annotation.model_validate(record | {"label_status": "ADJUDICATED", "adjudication": review("r1", "PRESENT")})
    resolved = Annotation.model_validate(record | {"label_status": "ADJUDICATED", "adjudication": review("r3", "PRESENT")})
    assert resolved.training_label(cutoff) == 1
    assert resolved.training_label(datetime(2026, 11, 7, 12, tzinfo=timezone.utc)) is None


def test_group_time_split_and_observation_only_features():
    config = json.loads(PROTOCOL.read_text()) | {"customers": 40}
    cases, labels = generate(config)
    assert generate(config) == (cases, labels)
    split = split_cases(cases, config["split_fractions"])
    case_by_id = {row["case_key"]: row for row in cases}
    groups = [{case_by_id[key]["customer_group"] for key in keys} for keys in split.values()]
    assert sum(map(len, groups)) == len(set.union(*groups)) == 40
    spans = [(case_by_id[ids[0]]["observed_at"], case_by_id[ids[-1]]["observed_at"]) for ids in split.values()]
    assert all(before[1] < after[0] for before, after in zip(spans, spans[1:]))
    assert all("template" not in field and "customer" not in field for field in NAMES)
    vector, baseline = encode(cases[0])
    permuted, permuted_baseline = encode(cases[0] | {"documents": cases[0]["documents"][::-1]})
    n = len(cases[0]["documents"])
    np.testing.assert_array_equal(vector[:n][::-1], permuted[:n])
    assert baseline == pytest.approx(permuted_baseline)


def test_deep_sets_permutation_and_padding_invariants():
    torch.manual_seed(42)
    net = DeepSets(len(NAMES), 16, len(FIELDS)).eval()
    values = torch.rand(1, 4, len(NAMES))
    mask = torch.tensor([[True, True, True, False]])
    perm = [2, 0, 3, 1]
    with torch.inference_mode():
        document, field = net(values, mask)
        shuffled, shuffled_field = net(values[:, perm], mask[:, perm])
        torch.testing.assert_close(document[:, perm], shuffled)
        torch.testing.assert_close(field[:, perm], shuffled_field)
        values[:, -1] = 100
        changed, changed_field = net(values, mask)
        torch.testing.assert_close(document[mask], changed[mask])
        torch.testing.assert_close(field[mask], changed_field[mask])
