"""Bank annotation intake contract and independent adjudication checks."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Target = Literal["field_extraction_error", "cross_source_inconsistency", "material_evidence_error",
                 "verification_required"]
Verdict = Literal["PRESENT", "ABSENT", "UNVERIFIABLE"]
Key = Annotated[str, Field(min_length=1, max_length=128)]


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_key: Key
    customer_group_key: Key
    case_key: Key
    template_group_key: Key
    source_system: Key
    document_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: AwareDatetime
    decision_at: AwareDatetime
    access_authorization_ref: Key
    # Store only references to restricted evidence, never raw values in annotation JSONL.
    evidence_refs: list[Key] = Field(min_length=1)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer_key: Key
    verdict: Verdict
    reviewed_at: AwareDatetime
    verification_method: Key
    evidence_refs: list[Key] = Field(min_length=1)
    reason_code: Key


class Annotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label_status: Literal["PENDING", "DISPUTED", "CONSENSUS", "ADJUDICATED"]
    provenance: Provenance
    target: Target
    field_key: Key | None = None
    second_document_key: Key | None = None
    reviews: list[Review] = Field(default_factory=list, max_length=2)
    adjudication: Review | None = None

    @model_validator(mode="after")
    def validate_protocol(self):
        if self.target == "field_extraction_error" and not self.field_key:
            raise ValueError("Field extraction requires a field key")
        if self.target == "cross_source_inconsistency" and (
            not self.field_key or not self.second_document_key
            or self.second_document_key == self.provenance.document_key
        ):
            raise ValueError("Cross-source review requires a field and two distinct documents")
        if self.provenance.observed_at > self.provenance.decision_at:
            raise ValueError("Post-decision document is ineligible as a model input")
        reviewer_keys = {review.reviewer_key for review in self.reviews}
        if len(reviewer_keys) != len(self.reviews):
            raise ValueError("Reviews must be independent")
        if any(review.reviewed_at < self.provenance.observed_at for review in self.reviews):
            raise ValueError("Review cannot precede evidence observation")
        if self.adjudication and (self.adjudication.reviewer_key in reviewer_keys
                                  or any(self.adjudication.reviewed_at < r.reviewed_at for r in self.reviews)):
            raise ValueError("A separate reviewer must adjudicate after both reviews")
        if len(self.reviews) < 2:
            expected = "PENDING"
        elif self.reviews[0].verdict == self.reviews[1].verdict:
            expected = "CONSENSUS"
        else:
            expected = "ADJUDICATED" if self.adjudication else "DISPUTED"
        if self.label_status != expected or bool(self.adjudication) != (expected == "ADJUDICATED"):
            raise ValueError(f"Invalid review history for label status {self.label_status}")
        return self

    def training_label(self, cutoff: datetime) -> int | None:
        """Unknown, disputed or unavailable-as-of labels stay masked."""
        if self.label_status not in {"CONSENSUS", "ADJUDICATED"}:
            return None
        final_review = self.adjudication or max(self.reviews, key=lambda review: review.reviewed_at)
        if final_review.reviewed_at > cutoff or final_review.verdict == "UNVERIFIABLE":
            return None
        return int(final_review.verdict == "PRESENT")
