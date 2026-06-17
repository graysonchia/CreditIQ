from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    customer_code: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=255)
    age: int = Field(..., ge=18, le=100)
    gender: str = Field(..., min_length=1, max_length=30)
    marital_status: str = Field(..., min_length=1, max_length=50)
    employment_status: str = Field(..., min_length=1, max_length=100)
    monthly_income_myr: float = Field(..., ge=0)
    monthly_expenses_myr: float = Field(..., ge=0)
    years_employed: float = Field(..., ge=0)
    num_dependents: int = Field(..., ge=0)
    education_level: str = Field(..., min_length=1, max_length=100)
    existing_loans_count: int = Field(..., ge=0)
    existing_loans_total_myr: float = Field(..., ge=0)
    bankruptcy_history: bool
    late_payment_count_12m: int = Field(..., ge=0)
    credit_utilization_pct: float = Field(..., ge=0, le=100)
    savings_balance_myr: float = Field(..., ge=0)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    customer_code: str | None = Field(default=None, min_length=1, max_length=50)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    age: int | None = Field(default=None, ge=18, le=100)
    gender: str | None = Field(default=None, min_length=1, max_length=30)
    marital_status: str | None = Field(default=None, min_length=1, max_length=50)
    employment_status: str | None = Field(default=None, min_length=1, max_length=100)
    monthly_income_myr: float | None = Field(default=None, ge=0)
    monthly_expenses_myr: float | None = Field(default=None, ge=0)
    years_employed: float | None = Field(default=None, ge=0)
    num_dependents: int | None = Field(default=None, ge=0)
    education_level: str | None = Field(default=None, min_length=1, max_length=100)
    existing_loans_count: int | None = Field(default=None, ge=0)
    existing_loans_total_myr: float | None = Field(default=None, ge=0)
    bankruptcy_history: bool | None = None
    late_payment_count_12m: int | None = Field(default=None, ge=0)
    credit_utilization_pct: float | None = Field(default=None, ge=0, le=100)
    savings_balance_myr: float | None = Field(default=None, ge=0)


class PredictionSummary(BaseModel):
    id: int
    prediction_type: str
    predicted_value: float
    predicted_label: str | None
    confidence_score: float
    model_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerRead(CustomerBase):
    id: int
    is_deleted: bool = False
    created_at: datetime
    prediction_history: list[PredictionSummary] = []

    model_config = ConfigDict(from_attributes=True)


class CustomerListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[CustomerRead]


class CreditScorePredictionRequest(BaseModel):
    customer_id: int
    overrides: dict[str, Any] = Field(default_factory=dict)


class LoanDefaultPredictionRequest(BaseModel):
    customer_id: int
    requested_amount_myr: float = Field(..., gt=0)
    tenure_months: int = Field(..., gt=0)
    loan_type: str = Field(..., min_length=1, max_length=100)
    purpose: str | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)


class FraudPredictionRequest(BaseModel):
    customer_id: int
    amount_myr: float = Field(..., gt=0)
    transaction_hour: int = Field(..., ge=0, le=23)
    is_international: bool
    merchant_category: str = Field(..., min_length=1, max_length=100)
    device_type: str = Field(..., min_length=1, max_length=50)
    transaction_type: str = Field(..., min_length=1, max_length=50)
    location: str | None = None
    transaction_date: date | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)


class PredictionResponse(BaseModel):
    id: int
    customer_id: int
    prediction_type: Literal["credit_score", "loan_default", "fraud"]
    predicted_value: float
    predicted_label: str | None
    confidence_score: float
    model_version: str
    shap_explanation: dict[str, Any] | None
    missing_features: list[str] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchPredictionResponse(BaseModel):
    predictions: list[PredictionResponse]


class ModelMetricRead(BaseModel):
    id: int
    model_name: str
    model_version: str
    accuracy: float | None
    precision_score: float | None
    recall: float | None
    f1_score: float | None
    roc_auc: float | None
    trained_at: datetime
    dataset_size: int
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PredictionDistributionItem(BaseModel):
    prediction_type: str
    month: str
    count: int
    avg_predicted_value: float | None


class TopRiskCustomer(BaseModel):
    customer_id: int
    customer_code: str
    full_name: str
    risk_type: str
    risk_score: float
    predicted_label: str | None
    created_at: datetime


class CustomerInsights(BaseModel):
    customer: CustomerRead
    prediction_count: int
    average_confidence: float | None
    history: list[PredictionSummary]


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float


class UserRead(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
