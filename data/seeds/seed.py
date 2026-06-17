from __future__ import annotations

from datetime import date, datetime, timedelta
import random

from faker import Faker
import psycopg2
from psycopg2.extras import execute_values


# Replace yourpassword with your local PostgreSQL password before running.
DATABASE_URL = "postgresql://postgres:rodolfo@localhost:5432/creditiq"

fake = Faker("en_US")
random.seed(42)
Faker.seed(42)

MERCHANT_CATEGORIES = [
    "groceries",
    "fuel",
    "utilities",
    "restaurants",
    "travel",
    "electronics",
    "healthcare",
    "education",
    "entertainment",
    "online_shopping",
]
TRANSACTION_TYPES = ["card", "online_transfer", "e_wallet", "atm_withdrawal"]
DEVICE_TYPES = ["mobile", "desktop", "pos_terminal", "atm"]
LOAN_TYPES = ["personal", "auto", "mortgage", "education", "business"]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def build_customers() -> list[tuple]:
    print("Generating 1000 customers...")
    customers = []
    education_levels = ["SPM", "Diploma", "Bachelor", "Master", "PhD"]
    employment_statuses = ["employed", "self_employed", "contract", "unemployed", "retired"]

    for idx in range(1, 1001):
        age = random.randint(22, 65)
        income = round(random.triangular(2000, 25000, 6500), 2)
        savings_factor = random.uniform(0.5, 7.5)
        savings = round(clamp(income * savings_factor + random.gauss(0, 5000), 0, 250000), 2)
        utilization = round(clamp(95 - (savings / 3000) + random.gauss(0, 13), 3, 98), 2)
        late_lambda = clamp(3.5 - (income / 8000) + (utilization / 60), 0.05, 6)
        late_payments = min(12, int(random.expovariate(1 / late_lambda)))
        bankruptcy = random.random() < 0.10
        years_employed = round(clamp(age - random.randint(20, 28) + random.uniform(-1, 2), 0, 42), 1)
        dependents = random.choices([0, 1, 2, 3, 4, 5], [22, 23, 25, 17, 9, 4])[0]
        expenses_ratio = random.uniform(0.38, 0.82) + dependents * 0.03
        expenses = round(clamp(income * expenses_ratio, 900, income * 0.96), 2)
        loans_count = random.choices([0, 1, 2, 3, 4, 5], [26, 31, 22, 12, 6, 3])[0]
        loans_total = round(max(0, loans_count * income * random.uniform(4, 28)), 2)

        customers.append(
            (
                f"CUST{idx:05d}",
                fake.name(),
                age,
                random.choice(["male", "female", "other"]),
                random.choice(["single", "married", "divorced", "widowed"]),
                random.choices(employment_statuses, [62, 18, 10, 6, 4])[0],
                income,
                expenses,
                years_employed,
                dependents,
                random.choices(education_levels, [18, 24, 38, 16, 4])[0],
                loans_count,
                loans_total,
                bankruptcy,
                late_payments,
                utilization,
                savings,
                datetime.utcnow(),
            )
        )

    return customers


def insert_customers(conn) -> list[int]:
    customers = build_customers()
    sql = """
        INSERT INTO customers (
            customer_code, full_name, age, gender, marital_status, employment_status,
            monthly_income_myr, monthly_expenses_myr, years_employed, num_dependents,
            education_level, existing_loans_count, existing_loans_total_myr,
            bankruptcy_history, late_payment_count_12m, credit_utilization_pct,
            savings_balance_myr, created_at
        ) VALUES %s RETURNING id
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, customers, page_size=1000)
        ids = [row[0] for row in cur.fetchall()]
    conn.commit()
    print(f"Inserted {len(ids)} customers.")
    return ids


def insert_transactions(conn, customer_ids: list[int]) -> None:
    print("Generating and inserting 100000 transactions...")
    rows = []
    start = date(2023, 1, 1)
    end = date(2024, 12, 31)

    for idx in range(100000):
        is_fraud = random.random() < 0.03
        category = random.choices(
            MERCHANT_CATEGORIES,
            [22, 12, 8, 16, 5, 7, 6, 4, 8, 12],
        )[0]

        if is_fraud:
            amount = round(random.triangular(800, 18000, 4200), 2)
            hour = random.randint(1, 5)
            international = random.random() < 0.82
            device = random.choice(["mobile", "desktop"])
        else:
            amount = round(random.triangular(8, 2500, 110), 2)
            hour = random.choices(range(24), weights=[1, 1, 1, 1, 1, 2, 5, 8, 10, 12, 13, 13, 12, 12, 12, 13, 15, 15, 12, 9, 6, 4, 2, 1])[0]
            international = random.random() < 0.08
            device = random.choices(DEVICE_TYPES, [45, 20, 30, 5])[0]

        rows.append(
            (
                random.choice(customer_ids),
                random_date(start, end),
                amount,
                category,
                random.choices(TRANSACTION_TYPES, [52, 22, 21, 5])[0],
                international,
                hour,
                device,
                fake.city(),
                is_fraud,
                datetime.utcnow(),
            )
        )

        if len(rows) >= 5000:
            flush_transactions(conn, rows)
            print(f"Inserted {idx + 1} transactions...")
            rows.clear()

    if rows:
        flush_transactions(conn, rows)
    print("Inserted 100000 transactions.")


def flush_transactions(conn, rows: list[tuple]) -> None:
    sql = """
        INSERT INTO transactions (
            customer_id, transaction_date, amount_myr, merchant_category,
            transaction_type, is_international, transaction_hour, device_type,
            location, is_fraud, created_at
        ) VALUES %s
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=5000)
    conn.commit()


def insert_loan_applications(conn, customer_ids: list[int]) -> None:
    print("Generating and inserting 1500 loan applications...")
    rows = []
    statuses = ["DEFAULTED"] * 300
    statuses.extend(random.choices(["PENDING", "APPROVED"], [25, 55], k=1200))
    random.shuffle(statuses)

    for status in statuses:
        loan_type = random.choices(LOAN_TYPES, [35, 22, 18, 12, 13])[0]
        requested_amount = round(random.triangular(3000, 600000, 45000), 2)
        tenure = random.choice([6, 12, 24, 36, 48, 60, 84, 120, 180, 240, 300, 360])

        rows.append(
            (
                random.choice(customer_ids),
                random_date(date(2023, 1, 1), date(2024, 12, 31)),
                loan_type,
                requested_amount,
                tenure,
                random.choice(["debt_consolidation", "home", "vehicle", "education", "working_capital", "medical"]),
                status,
                datetime.utcnow(),
            )
        )

    sql = """
        INSERT INTO loan_applications (
            customer_id, application_date, loan_type, requested_amount_myr,
            tenure_months, purpose, status, created_at
        ) VALUES %s
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=1000)
    conn.commit()
    print("Inserted 1500 loan applications.")


def main() -> None:
    print("Connecting to PostgreSQL...")
    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE predictions, loan_applications, transactions, customers, "
                "model_metrics, users RESTART IDENTITY CASCADE;"
            )
        conn.commit()
        print("Cleared existing data.")

        customer_ids = insert_customers(conn)
        insert_transactions(conn, customer_ids)
        insert_loan_applications(conn, customer_ids)
    print("Seeding complete.")


if __name__ == "__main__":
    main()
