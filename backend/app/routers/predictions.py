from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.database import get_db
from app.ml.explainer import explainer
from app.ml.predictor import InvalidModelTypeError, ModelNotAvailableError, predictor
from app.models.models import Customer, Prediction, PredictionType
from app.routers.customers import get_customer_or_404
from app.schemas.schemas import (
    BatchPredictionResponse,
    CreditScorePredictionRequest,
    FraudPredictionRequest,
    LoanDefaultPredictionRequest,
    PredictionResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predictions", tags=["predictions"])


def _customer_features(customer: Customer) -> dict[str, Any]:
    return {
        "age": customer.age,
        "monthly_income_myr": customer.monthly_income_myr,
        "monthly_expenses_myr": customer.monthly_expenses_myr,
        "years_employed": customer.years_employed,
        "num_dependents": customer.num_dependents,
        "existing_loans_count": customer.existing_loans_count,
        "existing_loans_total_myr": customer.existing_loans_total_myr,
        "bankruptcy_history": int(customer.bankruptcy_history),
        "late_payment_count_12m": customer.late_payment_count_12m,
        "credit_utilization_pct": customer.credit_utilization_pct,
        "savings_balance_myr": customer.savings_balance_myr,
        "education_level": customer.education_level,
        "employment_status": customer.employment_status,
    }


def _prediction_response(prediction: Prediction, missing_features: list[str]) -> PredictionResponse:
    return PredictionResponse(
        id=prediction.id,
        customer_id=prediction.customer_id,
        prediction_type=prediction.prediction_type.value,
        predicted_value=prediction.predicted_value,
        predicted_label=prediction.predicted_label,
        confidence_score=prediction.confidence_score,
        model_version=prediction.model_version,
        shap_explanation=prediction.shap_values,
        missing_features=missing_features,
        created_at=prediction.created_at,
    )


async def _run_prediction(
    db: AsyncSession,
    customer_id: int,
    model_type: str,
    prediction_type: PredictionType,
    features: dict[str, Any],
) -> PredictionResponse:
    try:
        result = await run_in_threadpool(predictor.predict, model_type, features)
        shap_explanation = await run_in_threadpool(explainer.explain, model_type, features)
    except ModelNotAvailableError as exc:
        logger.exception("Model unavailable for %s", model_type)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except (InvalidModelTypeError, ValueError) as exc:
        logger.exception("Invalid prediction request for %s", model_type)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Prediction failed for %s", model_type)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Prediction failed.") from exc

    prediction = Prediction(
        customer_id=customer_id,
        prediction_type=prediction_type,
        input_features=features,
        predicted_value=result["predicted_value"],
        predicted_label=result["predicted_label"],
        confidence_score=result["confidence_score"],
        shap_values=shap_explanation,
        model_version=result["model_version"],
    )
    db.add(prediction)
    await db.commit()
    await db.refresh(prediction)
    logger.info("Stored %s prediction %s for customer %s", model_type, prediction.id, customer_id)
    return _prediction_response(prediction, result["missing_features"])


@router.post("/credit-score", response_model=PredictionResponse)
async def predict_credit_score(
    payload: CreditScorePredictionRequest,
    db: AsyncSession = Depends(get_db),
) -> PredictionResponse:
    """Predict a customer's credit score and store the audit record."""
    customer = await get_customer_or_404(db, payload.customer_id)
    features = _customer_features(customer)
    features.update(payload.overrides)
    return await _run_prediction(db, customer.id, "credit_score", PredictionType.CREDIT_SCORE, features)


@router.post("/loan-default", response_model=PredictionResponse)
async def predict_loan_default(
    payload: LoanDefaultPredictionRequest,
    db: AsyncSession = Depends(get_db),
) -> PredictionResponse:
    """Assess loan default risk and store the audit record."""
    customer = await get_customer_or_404(db, payload.customer_id)
    features = _customer_features(customer)
    features.update(
        {
            "requested_amount_myr": payload.requested_amount_myr,
            "tenure_months": payload.tenure_months,
            "loan_type": payload.loan_type,
            "debt_to_income_ratio": customer.existing_loans_total_myr / max(customer.monthly_income_myr, 1),
        }
    )
    features.update(payload.overrides)
    return await _run_prediction(db, customer.id, "default", PredictionType.LOAN_DEFAULT, features)


@router.post("/fraud", response_model=PredictionResponse)
async def predict_fraud(
    payload: FraudPredictionRequest,
    db: AsyncSession = Depends(get_db),
) -> PredictionResponse:
    """Detect transaction fraud risk and store the audit record."""
    customer = await get_customer_or_404(db, payload.customer_id)
    features = {
        "amount_myr": payload.amount_myr,
        "transaction_hour": payload.transaction_hour,
        "is_international": int(payload.is_international),
        "merchant_category": payload.merchant_category,
        "device_type": payload.device_type,
        "transaction_type": payload.transaction_type,
        "monthly_income_myr": customer.monthly_income_myr,
        "credit_utilization_pct": customer.credit_utilization_pct,
    }
    features.update(payload.overrides)
    return await _run_prediction(db, customer.id, "fraud", PredictionType.FRAUD, features)


@router.post("/credit-score/batch", response_model=BatchPredictionResponse)
async def batch_predict_credit_score(
    payloads: list[CreditScorePredictionRequest],
    db: AsyncSession = Depends(get_db),
) -> BatchPredictionResponse:
    """Run batch credit score predictions."""
    predictions = [await predict_credit_score(payload, db) for payload in payloads]
    return BatchPredictionResponse(predictions=predictions)


@router.post("/loan-default/batch", response_model=BatchPredictionResponse)
async def batch_predict_loan_default(
    payloads: list[LoanDefaultPredictionRequest],
    db: AsyncSession = Depends(get_db),
) -> BatchPredictionResponse:
    """Run batch loan default predictions."""
    predictions = [await predict_loan_default(payload, db) for payload in payloads]
    return BatchPredictionResponse(predictions=predictions)


@router.post("/fraud/batch", response_model=BatchPredictionResponse)
async def batch_predict_fraud(
    payloads: list[FraudPredictionRequest],
    db: AsyncSession = Depends(get_db),
) -> BatchPredictionResponse:
    """Run batch fraud predictions."""
    predictions = [await predict_fraud(payload, db) for payload in payloads]
    return BatchPredictionResponse(predictions=predictions)
