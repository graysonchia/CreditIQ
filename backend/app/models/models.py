from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class LoanStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFAULTED = "defaulted"


class PredictionType(str, Enum):
    CREDIT_SCORE = "credit_score"
    LOAN_DEFAULT = "loan_default"
    FRAUD = "fraud"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.VIEWER,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(30), nullable=False)
    marital_status: Mapped[str] = mapped_column(String(50), nullable=False)
    employment_status: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_income_myr: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_expenses_myr: Mapped[float] = mapped_column(Float, nullable=False)
    years_employed: Mapped[float] = mapped_column(Float, nullable=False)
    num_dependents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    education_level: Mapped[str] = mapped_column(String(100), nullable=False)
    existing_loans_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    existing_loans_total_myr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bankruptcy_history: Mapped[bool] = mapped_column(nullable=False, default=False)
    late_payment_count_12m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credit_utilization_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    savings_balance_myr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    loan_applications: Mapped[list["LoanApplication"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_myr: Mapped[float] = mapped_column(Float, nullable=False)
    merchant_category: Mapped[str] = mapped_column(String(100), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_international: Mapped[bool] = mapped_column(nullable=False, default=False)
    transaction_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    is_fraud: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    customer: Mapped["Customer"] = relationship(back_populates="transactions")


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    application_date: Mapped[date] = mapped_column(Date, nullable=False)
    loan_type: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_amount_myr: Mapped[float] = mapped_column(Float, nullable=False)
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[LoanStatus] = mapped_column(
        SQLEnum(LoanStatus, name="loan_status"),
        nullable=False,
        default=LoanStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    customer: Mapped["Customer"] = relationship(back_populates="loan_applications")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    prediction_type: Mapped[PredictionType] = mapped_column(
        SQLEnum(PredictionType, name="prediction_type"),
        nullable=False,
    )
    input_features: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    shap_values: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    customer: Mapped["Customer"] = relationship(back_populates="predictions")


class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    roc_auc: Mapped[float | None] = mapped_column(Float, nullable=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dataset_size: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
