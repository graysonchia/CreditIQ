from __future__ import annotations

from datetime import datetime
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.ml.predictor import InvalidModelTypeError, ModelNotAvailableError
from app.ml.explainer import explainer
from app.models.models import Customer, ModelMetric, Prediction, PredictionType
from app.routers.customers import _customer_payload, get_customer_or_404
from app.schemas.schemas import (
    CustomerInsights,
    CustomerRead,
    FeatureImportanceItem,
    ModelMetricRead,
    PredictionDistributionItem,
    PredictionSummary,
    TopRiskCustomer,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


def _date_filters(start_date: datetime | None, end_date: datetime | None) -> list:
    filters = []
    if start_date is not None:
        filters.append(Prediction.created_at >= start_date)
    if end_date is not None:
        filters.append(Prediction.created_at <= end_date)
    return filters


@router.get("/model-performance", response_model=list[ModelMetricRead])
async def model_performance(
    model_name: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ModelMetricRead]:
    """Return model performance metrics with optional model/date filters."""
    query = select(ModelMetric)
    if model_name:
        query = query.where(ModelMetric.model_name == model_name)
    if start_date is not None:
        query = query.where(ModelMetric.trained_at >= start_date)
    if end_date is not None:
        query = query.where(ModelMetric.trained_at <= end_date)
    query = query.order_by(desc(ModelMetric.trained_at))

    result = await db.execute(query)
    return [ModelMetricRead.model_validate(metric) for metric in result.scalars().all()]


@router.get("/prediction-distribution", response_model=list[PredictionDistributionItem])
async def prediction_distribution(
    prediction_type: PredictionType | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[PredictionDistributionItem]:
    """Return monthly prediction counts and average predicted values."""
    month_expr = func.date_trunc("month", Prediction.created_at).label("month")
    query = (
        select(
            Prediction.prediction_type,
            month_expr,
            func.count(Prediction.id).label("count"),
            func.avg(Prediction.predicted_value).label("avg_predicted_value"),
        )
        .where(*_date_filters(start_date, end_date))
        .group_by(Prediction.prediction_type, month_expr)
        .order_by(month_expr, Prediction.prediction_type)
    )
    if prediction_type is not None:
        query = query.where(Prediction.prediction_type == prediction_type)

    result = await db.execute(query)
    return [
        PredictionDistributionItem(
            prediction_type=row.prediction_type.value,
            month=row.month.strftime("%Y-%m"),
            count=row.count,
            avg_predicted_value=float(row.avg_predicted_value) if row.avg_predicted_value is not None else None,
        )
        for row in result
    ]


@router.get("/top-risk-customers", response_model=list[TopRiskCustomer])
async def top_risk_customers(
    risk_type: Literal["loan_default", "fraud"] | None = None,
    limit: int = Query(default=10, ge=1, le=100),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[TopRiskCustomer]:
    """Return customers with the highest default or fraud prediction risk."""
    prediction_types = [PredictionType.LOAN_DEFAULT, PredictionType.FRAUD]
    if risk_type == "loan_default":
        prediction_types = [PredictionType.LOAN_DEFAULT]
    elif risk_type == "fraud":
        prediction_types = [PredictionType.FRAUD]

    query = (
        select(Prediction, Customer)
        .join(Customer, Customer.id == Prediction.customer_id)
        .where(
            Prediction.prediction_type.in_(prediction_types),
            Customer.is_deleted.is_(False),
            *_date_filters(start_date, end_date),
        )
        .order_by(desc(Prediction.predicted_value), desc(Prediction.created_at))
        .limit(limit)
    )
    result = await db.execute(query)
    return [
        TopRiskCustomer(
            customer_id=customer.id,
            customer_code=customer.customer_code,
            full_name=customer.full_name,
            risk_type=prediction.prediction_type.value,
            risk_score=prediction.predicted_value,
            predicted_label=prediction.predicted_label,
            created_at=prediction.created_at,
        )
        for prediction, customer in result.all()
    ]


@router.get("/customer-insights/{customer_id}", response_model=CustomerInsights)
async def customer_insights(
    customer_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> CustomerInsights:
    """Return prediction history and aggregate trends for one customer."""
    customer = await get_customer_or_404(db, customer_id)
    query = (
        select(Prediction)
        .where(Prediction.customer_id == customer_id, *_date_filters(start_date, end_date))
        .order_by(desc(Prediction.created_at))
    )
    result = await db.execute(query)
    history = result.scalars().all()
    average_confidence = (
        sum(item.confidence_score for item in history) / len(history)
        if history
        else None
    )
    return CustomerInsights(
        customer=CustomerRead.model_validate(_customer_payload(customer, history[:5])),
        prediction_count=len(history),
        average_confidence=average_confidence,
        history=[PredictionSummary.model_validate(item) for item in history],
    )


@router.get("/feature-importance/{model_type}", response_model=list[FeatureImportanceItem])
async def feature_importance(
    model_type: Literal["credit_score", "default", "fraud"],
    limit: int = Query(default=20, ge=1, le=200),
) -> list[FeatureImportanceItem]:
    """Return global feature importance for a trained model."""
    try:
        importance = await run_in_threadpool(explainer.global_feature_importance, model_type, limit)
    except ModelNotAvailableError as exc:
        logger.exception("Feature importance failed for %s", model_type)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except InvalidModelTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [FeatureImportanceItem(**item) for item in importance]
