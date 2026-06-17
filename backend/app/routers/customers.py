from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.models import Customer, Prediction
from app.schemas.schemas import CustomerCreate, CustomerListResponse, CustomerRead, CustomerUpdate


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/customers", tags=["customers"])


def _customer_payload(customer: Customer, predictions: list[Prediction] | None = None) -> dict:
    payload = {
        "id": customer.id,
        "customer_code": customer.customer_code,
        "full_name": customer.full_name,
        "age": customer.age,
        "gender": customer.gender,
        "marital_status": customer.marital_status,
        "employment_status": customer.employment_status,
        "monthly_income_myr": customer.monthly_income_myr,
        "monthly_expenses_myr": customer.monthly_expenses_myr,
        "years_employed": customer.years_employed,
        "num_dependents": customer.num_dependents,
        "education_level": customer.education_level,
        "existing_loans_count": customer.existing_loans_count,
        "existing_loans_total_myr": customer.existing_loans_total_myr,
        "bankruptcy_history": customer.bankruptcy_history,
        "late_payment_count_12m": customer.late_payment_count_12m,
        "credit_utilization_pct": customer.credit_utilization_pct,
        "savings_balance_myr": customer.savings_balance_myr,
        "is_deleted": getattr(customer, "is_deleted", False),
        "created_at": customer.created_at,
        "prediction_history": predictions or [],
    }
    return payload


async def get_customer_or_404(db: AsyncSession, customer_id: int) -> Customer:
    result = await db.execute(
        select(Customer)
        .where(Customer.id == customer_id, Customer.is_deleted.is_(False))
        .options(selectinload(Customer.predictions))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    return customer


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> CustomerListResponse:
    """List active customers with pagination and recent prediction summaries."""
    total = await db.scalar(select(func.count()).select_from(Customer).where(Customer.is_deleted.is_(False)))
    result = await db.execute(
        select(Customer)
        .where(Customer.is_deleted.is_(False))
        .order_by(Customer.id)
        .limit(limit)
        .offset(offset)
        .options(selectinload(Customer.predictions))
    )
    customers = result.scalars().all()
    items = [
        CustomerRead.model_validate(
            _customer_payload(customer, sorted(customer.predictions, key=lambda item: item.created_at, reverse=True)[:5])
        )
        for customer in customers
    ]
    return CustomerListResponse(total=total or 0, limit=limit, offset=offset, items=items)


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_db)) -> CustomerRead:
    """Retrieve a full customer profile with prediction history."""
    customer = await get_customer_or_404(db, customer_id)
    history = sorted(customer.predictions, key=lambda item: item.created_at, reverse=True)
    return CustomerRead.model_validate(_customer_payload(customer, history))


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(payload: CustomerCreate, db: AsyncSession = Depends(get_db)) -> CustomerRead:
    """Create a new customer profile."""
    existing = await db.scalar(select(Customer).where(Customer.customer_code == payload.customer_code))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="customer_code already exists.")

    customer = Customer(**payload.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    logger.info("Created customer %s", customer.id)
    return CustomerRead.model_validate(_customer_payload(customer))


@router.put("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
) -> CustomerRead:
    """Update customer attributes."""
    customer = await get_customer_or_404(db, customer_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(customer, field, value)

    await db.commit()
    await db.refresh(customer)
    logger.info("Updated customer %s", customer.id)
    return CustomerRead.model_validate(_customer_payload(customer, customer.predictions))


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(customer_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Soft delete a customer by marking it inactive."""
    customer = await get_customer_or_404(db, customer_id)
    customer.is_deleted = True
    await db.commit()
    logger.info("Soft deleted customer %s", customer.id)
