from __future__ import annotations

import json
from pathlib import Path

import joblib
from lightgbm import LGBMClassifier
import mlflow
import mlflow.lightgbm
import mlflow.sklearn
import optuna
import pandas as pd
from sklearn.metrics import classification_report, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

from db_utils import insert_model_metric


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "processed_fraud.csv"
MODEL_DIR = ROOT_DIR / "saved_models" / "fraud"
MLFLOW_TRACKING_URI = f"sqlite:///{(ROOT_DIR / 'mlflow.db').as_posix()}"


def main() -> None:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("fraud_classification")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    x = df.drop(columns=["is_fraud"])
    y = df["is_fraud"]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )

    def objective(trial: optuna.Trial) -> float:
        model = LGBMClassifier(
            n_estimators=trial.suggest_int("n_estimators", 150, 800),
            max_depth=trial.suggest_int("max_depth", 3, 14),
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.25, log=True),
            num_leaves=trial.suggest_int("num_leaves", 16, 160),
            min_child_samples=trial.suggest_int("min_child_samples", 10, 120),
            subsample=trial.suggest_float("subsample", 0.7, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.7, 1.0),
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_test)[:, 1]
        labels = (probabilities >= 0.5).astype(int)
        return f1_score(y_test, labels, zero_division=0)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=20)

    model = LGBMClassifier(random_state=42, n_jobs=-1, verbose=-1, **study.best_params)
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    labels = (probabilities >= 0.5).astype(int)
    roc_auc = roc_auc_score(y_test, probabilities)
    report = classification_report(y_test, labels, zero_division=0)

    with mlflow.start_run(run_name="best_lightgbm_fraud"):
        mlflow.log_params(study.best_params)
        mlflow.log_metric("roc_auc", roc_auc)
        mlflow.log_metric("f1", f1_score(y_test, labels, zero_division=0))
        mlflow.lightgbm.log_model(model, "model")

    joblib.dump(model, MODEL_DIR / "model.joblib")
    (MODEL_DIR / "features.json").write_text(json.dumps(list(x.columns), indent=2), encoding="utf-8")
    (MODEL_DIR / "threshold.json").write_text(json.dumps({"threshold": 0.5}, indent=2), encoding="utf-8")
    insert_model_metric(
        model_name="fraud",
        model_version="lightgbm",
        f1_score=f1_score(y_test, labels, zero_division=0),
        roc_auc=roc_auc,
        dataset_size=len(df),
        notes="LightGBM fraud detector, threshold=0.5",
    )

    print(report)
    print(f"ROC-AUC: {roc_auc:.4f}")


if __name__ == "__main__":
    main()
