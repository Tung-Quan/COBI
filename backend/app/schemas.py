from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

Route = Literal["HOLD_FOR_HUMAN_HANDLING", "FAST_TRACK_CANDIDATE", "STANDARD_REVIEW", "ENHANCED_REVIEW"]
ReviewAction = Literal["confirm_route", "request_evidence", "escalate", "override_route"]
RiskSource = Literal["SYNTHETIC_HEURISTIC", "PUBLIC_BENCHMARK_ONLY", "APPLICATION_COMPATIBLE_VALIDATED", "UNAVAILABLE"]
Money = Annotated[float, Field(ge=0, le=1e12, allow_inf_nan=False)]
PositiveMoney = Annotated[float, Field(ge=0.01, le=1e12, allow_inf_nan=False)]


class EvidenceSource(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    type: str
    months: int = Field(ge=0, le=120)
    verified: StrictBool
    permission: str
    feature_event_at: str | None = None
    feature_snapshot_at: str | None = None


class Evidence(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    reconciliation_fields_total: int = Field(default=0, ge=0)
    reconciliation_fields_consistent: int = Field(default=0, ge=0)
    available_sources: int = Field(default=0, ge=0)
    verified_sources: int = Field(default=0, ge=0)
    age_days: float = Field(default=3650, ge=0, le=3650)
    sources: list[EvidenceSource] = Field(default_factory=list, max_length=100)
    reconciliation_notes: list[str] = Field(default_factory=list, max_length=100)
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    critical_failure: StrictBool = False
    feature_event_at: str | None = None
    feature_snapshot_at: str | None = None

    @model_validator(mode="after")
    def check_counts(self):
        if self.reconciliation_fields_consistent > self.reconciliation_fields_total or self.verified_sources > self.available_sources:
            raise ValueError("Verified and reconciled counts cannot exceed their respective totals.")
        return self


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    application_id: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9-]+$")
    borrower_label: str = Field(min_length=1, max_length=100)
    product: str = "Checkout installment"
    merchant: str = Field(min_length=1, max_length=120)
    purchase_description: str = Field(min_length=1, max_length=200)
    purchase_amount_vnd: PositiveMoney
    loan_amount_vnd: PositiveMoney
    own_funds_vnd: Money | None = None
    proposed_installment_vnd: PositiveMoney
    term_months: int | None = Field(default=None, gt=0, le=120)
    annual_interest_rate: float | None = Field(default=None, ge=0, le=1)
    submitted_at: str
    consent: StrictBool
    identity_verified: StrictBool
    source_permission: StrictBool
    funding_reconciled: StrictBool
    existing_monthly_debt_vnd: Money
    essential_monthly_expenses_vnd: Money
    monthly_income_vnd: list[PositiveMoney] = Field(min_length=1, max_length=24)
    evidence: Evidence


class ReviewReason(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=12, max_length=1000)

    @field_validator("reason")
    @classmethod
    def reason_must_be_meaningful(cls, value: str) -> str:
        if len(value.strip()) < 12:
            raise ValueError("Please provide at least 12 non-space characters for the review reason.")
        return value.strip()


class ReviewActionIn(ReviewReason):
    action: ReviewAction
    route: Route | None = None


class SimulationIn(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    monthly_income_vnd: list[PositiveMoney] | None = Field(default=None, min_length=1, max_length=24)
    existing_monthly_debt_vnd: Money | None = None
    essential_monthly_expenses_vnd: Money | None = None
    proposed_installment_vnd: PositiveMoney | None = None
    consent: StrictBool | None = None
    identity_verified: StrictBool | None = None
    source_permission: StrictBool | None = None
    funding_reconciled: StrictBool | None = None
    evidence_quality: float | None = Field(default=None, ge=0, le=1)
    evidence_age_days: float | None = Field(default=None, ge=0, le=3650)
    max_dti: float = Field(default=0.35, ge=0.05, le=0.8)
    residual_buffer: float = Field(default=0.25, ge=0, le=0.75)
    route_costs_vnd: dict[Route, Money] | None = None
    benchmark_model_id: str | None = Field(default=None, max_length=100)


class AssessmentSimulationIn(SimulationIn):
    application_id: str = Field(min_length=3, max_length=40)
