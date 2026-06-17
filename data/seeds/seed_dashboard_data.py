from __future__ import annotations

from datetime import datetime, timedelta
import random
from pathlib import Path
import sys

from psycopg2.extras import Json, execute_values


ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "ml_pipeline"))

from db_utils import get_database_url  # noqa: E402
import psycopg2  # noqa: E402


random.seed(84)


def shap_payload(model_type: str) -> dict:
    features = {
        "credit_score": ["monthly_income_myr", "late_payment_count_12m", "credit_utilization_pct", "savings_balance_myr", "years_employed"],
        "loan_default": ["debt_to_income_ratio", "requested_amount_myr", "late_payment_count_12m", "credit_utilization_pct", "bankruptcy_history"],
        "fraud": ["amount_myr", "transaction_hour", "is_international", "merchant_category", "credit_utilization_pct"],
    }[model_type]
    contributions = [
        {
            "feature": feature,
            "shap_value": round(random.uniform(-0.18, 0.22), 4),
            "direction": "positive" if random.random() > 0.45 else "negative",
        }
        for feature in features
    ]
    return {
        "model_type": model_type,
        "expected_value": round(random.uniform(0.15, 0.55), 4),
        "base_value": round(random.uniform(0.15, 0.55), 4),
        "top_features": contributions,
        "feature_contributions": contributions,
    }


def insert_metrics(conn) -> None:
    print("Refreshing model metrics...")
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE model_metrics RESTART IDENTITY CASCADE;")
        rows = [
            ("credit_score", "xgboost", 0.9903, None, None, None, None, datetime.utcnow(), 1000, "MAE=8.3538, RMSE=11.8646, R2=0.9903", datetime.utcnow()),
            ("loan_default", "lightgbm", 0.9180, 0.9020, 0.9410, 0.9210, 0.9700, datetime.utcnow(), 2400, "SMOTE-balanced loan default classifier", datetime.utcnow()),
            ("fraud", "lightgbm", 0.9870, 0.9810, 0.9940, 0.9870, 0.9980, datetime.utcnow(), 193804, "SMOTE-balanced fraud classifier", datetime.utcnow()),
        ]
        execute_values(
            cur,
            """
            INSERT INTO model_metrics (
                model_name, model_version, accuracy, precision_score, recall,
                f1_score, roc_auc, trained_at, dataset_size, notes, created_at
            ) VALUES %s
            """,
            rows,
        )
    conn.commit()
    print("Inserted 3 model metric rows.")


def insert_predictions(conn) -> None:
    print("Refreshing dashboard predictions...")
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE predictions RESTART IDENTITY CASCADE;")
        cur.execute("SELECT id FROM customers ORDER BY id LIMIT 50;")
        first_page_ids = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT id FROM customers WHERE id > 50 ORDER BY random() LIMIT 100;")
        customer_ids = first_page_ids + [row[0] for row in cur.fetchall()]

    rows = []
    for customer_id in customer_ids:
        created_at = datetime.utcnow() - timedelta(days=random.randint(0, 10), hours=random.randint(0, 23))
        credit_score = round(random.triangular(300, 850, 690), 2)
        rows.append(
            (
                customer_id,
                "CREDIT_SCORE",
                Json({"customer_id": customer_id}),
                credit_score,
                "excellent" if credit_score >= 750 else "good" if credit_score >= 650 else "fair" if credit_score >= 550 else "poor",
                round(random.uniform(0.72, 0.96), 4),
                Json(shap_payload("credit_score")),
                "xgboost",
                created_at,
            )
        )

        default_risk = round(min(max(random.betavariate(2.2, 5.0), 0.02), 0.95), 4)
        rows.append(
            (
                customer_id,
                "LOAN_DEFAULT",
                Json({"customer_id": customer_id, "requested_amount_myr": random.randint(5000, 300000)}),
                default_risk,
                "default" if default_risk >= 0.5 else "non_default",
                round(max(default_risk, 1 - default_risk), 4),
                Json(shap_payload("loan_default")),
                "lightgbm",
                created_at + timedelta(minutes=5),
            )
        )

        if random.random() < 0.65:
            fraud_risk = round(min(max(random.betavariate(1.2, 9.5), 0.01), 0.96), 4)
            rows.append(
                (
                    customer_id,
                    "FRAUD",
                    Json({"customer_id": customer_id, "amount_myr": random.randint(20, 12000)}),
                    fraud_risk,
                    "fraud" if fraud_risk >= 0.5 else "legitimate",
                    round(max(fraud_risk, 1 - fraud_risk), 4),
                    Json(shap_payload("fraud")),
                    "lightgbm",
                    created_at + timedelta(minutes=10),
                )
            )

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO predictions (
                customer_id, prediction_type, input_features, predicted_value,
                predicted_label, confidence_score, shap_values, model_version, created_at
            ) VALUES %s
            """,
            rows,
            page_size=1000,
        )
    conn.commit()
    print(f"Inserted {len(rows)} prediction rows.")


def main() -> None:
    with psycopg2.connect(get_database_url()) as conn:
        insert_metrics(conn)
        insert_predictions(conn)
    print("Dashboard data ready.")


if __name__ == "__main__":
    main()
