from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg2


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / "backend" / ".env")


def get_database_url() -> str:
    sync_url = os.getenv("SYNC_DATABASE_URL", "postgresql+psycopg2://postgres:yourpassword@localhost:5432/creditiq")
    return sync_url.replace("postgresql+psycopg2://", "postgresql://")


def insert_model_metric(
    *,
    model_name: str,
    model_version: str,
    dataset_size: int,
    accuracy: float | None = None,
    precision_score: float | None = None,
    recall: float | None = None,
    f1_score: float | None = None,
    roc_auc: float | None = None,
    notes: str | None = None,
) -> None:
    sql = """
        INSERT INTO model_metrics (
            model_name, model_version, accuracy, precision_score, recall,
            f1_score, roc_auc, trained_at, dataset_size, notes, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    now = datetime.utcnow()
    with psycopg2.connect(get_database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    model_name,
                    model_version,
                    accuracy,
                    precision_score,
                    recall,
                    f1_score,
                    roc_auc,
                    now,
                    dataset_size,
                    notes,
                    now,
                ),
            )
        conn.commit()
