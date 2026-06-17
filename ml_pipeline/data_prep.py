from __future__ import annotations

from pathlib import Path

from imblearn.over_sampling import SMOTE
import pandas as pd
import psycopg2


DATABASE_URL = "postgresql://postgres:rodolfo@localhost:5432/creditiq"
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"


CUSTOMER_FEATURES = [
    "age",
    "monthly_income_myr",
    "monthly_expenses_myr",
    "years_employed",
    "num_dependents",
    "existing_loans_count",
    "existing_loans_total_myr",
    "bankruptcy_history",
    "late_payment_count_12m",
    "credit_utilization_pct",
    "savings_balance_myr",
    "education_level",
    "employment_status",
]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def load_table(conn, table_name: str) -> pd.DataFrame:
    print(f"Loading {table_name}...")
    return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)


def encode_frame(df: pd.DataFrame, categorical_columns: list[str]) -> pd.DataFrame:
    return pd.get_dummies(df, columns=categorical_columns, drop_first=False, dtype=int)


def build_credit_score_data(customers: pd.DataFrame) -> pd.DataFrame:
    df = customers[CUSTOMER_FEATURES].copy()
    df["bankruptcy_history"] = df["bankruptcy_history"].astype(int)
    df["credit_score"] = (
        600
        + (df["monthly_income_myr"] / 1000) * 2
        - (df["late_payment_count_12m"] * 20)
        - (df["bankruptcy_history"] * 150)
        + (df["years_employed"] * 5)
        - (df["credit_utilization_pct"] * 0.5)
        + (df["savings_balance_myr"] / 10000) * 10
    ).clip(300, 850)
    return encode_frame(df, ["education_level", "employment_status"])


def build_default_data(customers: pd.DataFrame, loans: pd.DataFrame) -> pd.DataFrame:
    df = loans.merge(customers, left_on="customer_id", right_on="id", suffixes=("_loan", ""))
    feature_cols = CUSTOMER_FEATURES + ["requested_amount_myr", "tenure_months", "loan_type"]
    df = df[feature_cols + ["status"]].copy()
    df["bankruptcy_history"] = df["bankruptcy_history"].astype(int)
    df["debt_to_income_ratio"] = (
        df["existing_loans_total_myr"] / df["monthly_income_myr"].replace(0, pd.NA)
    ).fillna(0)
    df["is_default"] = (df["status"].astype(str).str.upper() == "DEFAULTED").astype(int)
    df = df.drop(columns=["status"])
    df = encode_frame(df, ["education_level", "employment_status", "loan_type"])

    x = df.drop(columns=["is_default"])
    y = df["is_default"]
    print("Default class distribution before SMOTE:")
    print(y.value_counts().to_string())
    if y.nunique() < 2:
        print("WARNING: Only one default class found; skipping SMOTE for loan default data.")
        return df

    x_resampled, y_resampled = SMOTE(random_state=42).fit_resample(x, y)
    balanced = pd.DataFrame(x_resampled, columns=x.columns)
    balanced["is_default"] = y_resampled
    return balanced


def build_fraud_data(customers: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    customer_cols = ["id", "monthly_income_myr", "credit_utilization_pct"]
    df = transactions.merge(customers[customer_cols], left_on="customer_id", right_on="id")
    df = df[
        [
            "amount_myr",
            "transaction_hour",
            "is_international",
            "merchant_category",
            "device_type",
            "transaction_type",
            "monthly_income_myr",
            "credit_utilization_pct",
            "is_fraud",
        ]
    ].copy()
    df["is_international"] = df["is_international"].astype(int)
    df["is_fraud"] = df["is_fraud"].astype(int)
    df = encode_frame(df, ["merchant_category", "device_type", "transaction_type"])

    x = df.drop(columns=["is_fraud"])
    y = df["is_fraud"]
    print("Fraud class distribution before SMOTE:")
    print(y.value_counts().to_string())
    x_resampled, y_resampled = SMOTE(random_state=42).fit_resample(x, y)
    balanced = pd.DataFrame(x_resampled, columns=x.columns)
    balanced["is_fraud"] = y_resampled
    return balanced


def save_dataset(df: pd.DataFrame, filename: str, target: str) -> None:
    output_path = DATA_DIR / filename
    df.to_csv(output_path, index=False)
    print(f"Saved {filename}: shape={df.shape}")
    if target in df.columns:
        print(f"{target} distribution:")
        print(df[target].value_counts().to_string())


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with psycopg2.connect(DATABASE_URL) as conn:
        customers = load_table(conn, "customers")
        transactions = load_table(conn, "transactions")
        loans = load_table(conn, "loan_applications")

    credit_score = build_credit_score_data(customers)
    default = build_default_data(customers, loans)
    fraud = build_fraud_data(customers, transactions)

    save_dataset(credit_score, "processed_credit_score.csv", "credit_score")
    save_dataset(default, "processed_default.csv", "is_default")
    save_dataset(fraud, "processed_fraud.csv", "is_fraud")


if __name__ == "__main__":
    main()
