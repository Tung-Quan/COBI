from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Route = Literal[
    "HOLD_FOR_HUMAN_HANDLING",
    "FAST_TRACK_CANDIDATE",
    "STANDARD_REVIEW",
    "ENHANCED_REVIEW",
]
ReviewAction = Literal["confirm_route", "request_evidence", "escalate", "override_route"]


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9-]+$")
    borrower_label: str = Field(min_length=1, max_length=100)
    product: str = "Checkout installment"
    merchant: str = Field(min_length=1, max_length=120)
    purchase_description: str = Field(min_length=1, max_length=200)
    purchase_amount_vnd: float = Field(gt=0)
    loan_amount_vnd: float = Field(gt=0)
    proposed_installment_vnd: float = Field(gt=0)
    term_months: int | None = Field(default=None, gt=0, le=120)
    annual_interest_rate: float | None = Field(default=None, ge=0, le=1)
    submitted_at: str
    consent: bool
    identity_verified: bool
    source_permission: bool
    funding_reconciled: bool
    existing_monthly_debt_vnd: float = Field(ge=0)
    essential_monthly_expenses_vnd: float = Field(ge=0)
    monthly_income_vnd: list[float] = Field(min_length=1, max_length=24)
    evidence: dict

    @field_validator("monthly_income_vnd")
    @classmethod
    def income_values_are_positive(cls, values: list[float]) -> list[float]:
        if any(value <= 0 for value in values):
            raise ValueError("Every monthly income value must be positive.")
        return values


class ReviewActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ReviewAction
    reason: str = Field(min_length=12, max_length=1000)
    route: Route | None = None

    @field_validator("reason")
    @classmethod
    def reason_must_be_meaningful(cls, value: str) -> str:
        if len(value.strip()) < 12:
            raise ValueError("Please provide at least 12 non-space characters for the review reason.")
        return value.strip()


class SimulationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly_income_vnd: list[float] | None = Field(default=None, min_length=1, max_length=24)
    existing_monthly_debt_vnd: float | None = Field(default=None, ge=0)
    essential_monthly_expenses_vnd: float | None = Field(default=None, ge=0)
    proposed_installment_vnd: float | None = Field(default=None, gt=0)
    consent: bool | None = None
    identity_verified: bool | None = None
    source_permission: bool | None = None
    funding_reconciled: bool | None = None
    evidence_quality: float | None = Field(default=None, ge=0, le=1)
    evidence_age_days: float | None = Field(default=None, ge=0, le=3650)
    max_dti: float = Field(default=0.35, ge=0.05, le=0.8)
    route_costs_vnd: dict[str, float] | None = None

    @field_validator("monthly_income_vnd")
    @classmethod
    def income_values_are_positive(cls, values: list[float] | None) -> list[float] | None:
        if values is not None and any(value <= 0 for value in values):
            raise ValueError("Every monthly income value must be positive.")
        return values
