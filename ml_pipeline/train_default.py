from __future__ import annotations

import json
from pathlib import Path

import joblib
from lightgbm import LGBMClassifier
import mlflow
import mlflow.lightgbm
import mlflow.sklearn
import mlflow.xgboost
import optuna
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from db_utils import insert_model_metric


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "processed_default.csv"
MODEL_DIR = ROOT_DIR / "saved_models" / "default"
MLFLOW_TRACKING_URI = f"sqlite:///{(ROOT_DIR / 'mlflow.db').as_posix()}"


def metrics_for(y_true, probabilities, threshold: float) -> dict[str, float]:
    labels = (probabilities >= threshold).astype(int)
    return {
        "accuracy": accuracy_score(y_true, labels),
        "precision": precision_score(y_true, labels, zero_division=0),
        "recall": recall_score(y_true, labels, zero_division=0),
        "f1": f1_score(y_true, labels, zero_division=0),
        "roc_auc": roc_auc_score(y_true, probabilities),
    }


def main() -> None:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("loan_default_classification")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    x = df.drop(columns=["is_default"])
    y = df["is_default"]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )

    def objective(trial: optuna.Trial) -> float:
        model_name = trial.suggest_categorical("model", ["xgboost", "lightgbm"])
        if model_name == "xgboost":
            model = XGBClassifier(
                n_estimators=trial.suggest_int("n_estimators", 100, 600),
                max_depth=trial.suggest_int("max_depth", 3, 10),
                learning_rate=trial.suggest_float("learning_rate", 0.01, 0.25, log=True),
                subsample=trial.suggest_float("subsample", 0.7, 1.0),
                colsample_bytree=trial.suggest_float("colsample_bytree", 0.7, 1.0),
                eval_metric="logloss",
                random_state=42,
                n_jobs=-1,
            )
        else:
            model = LGBMClassifier(
                n_estimators=trial.suggest_int("n_estimators", 100, 600),
                max_depth=trial.suggest_int("max_depth", 3, 12),
                learning_rate=trial.suggest_float("learning_rate", 0.01, 0.25, log=True),
                num_leaves=trial.suggest_int("num_leaves", 16, 128),
                random_state=42,
                n_jobs=-1,
                verbose=-1,
            )
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_test)[:, 1]
        return roc_auc_score(y_test, probabilities)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=20)

    best = study.best_params.copy()
    model_name = best.pop("model")
    model = (
        XGBClassifier(eval_metric="logloss", random_state=42, n_jobs=-1, **best)
        if model_name == "xgboost"
        else LGBMClassifier(random_state=42, n_jobs=-1, verbose=-1, **best)
    )
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    threshold = 0.5
    metrics = metrics_for(y_test, probabilities, threshold)

    with mlflow.start_run(run_name=f"best_{model_name}"):
        mlflow.log_param("model", model_name)
        mlflow.log_param("threshold", threshold)
        mlflow.log_params(best)
        mlflow.log_metrics(metrics)
        if model_name == "xgboost":
            mlflow.xgboost.log_model(model, "model")
        else:
            mlflow.lightgbm.log_model(model, "model")

    joblib.dump(model, MODEL_DIR / "model.joblib")
    (MODEL_DIR / "features.json").write_text(json.dumps(list(x.columns), indent=2), encoding="utf-8")
    (MODEL_DIR / "threshold.json").write_text(json.dumps({"threshold": threshold}, indent=2), encoding="utf-8")
    insert_model_metric(
        model_name="loan_default",
        model_version=model_name,
        accuracy=metrics["accuracy"],
        precision_score=metrics["precision"],
        recall=metrics["recall"],
        f1_score=metrics["f1"],
        roc_auc=metrics["roc_auc"],
        dataset_size=len(df),
        notes=f"Threshold={threshold}",
    )

    print(f"Best model: {model_name}")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1: {metrics['f1']:.4f}")
    print(f"ROC-AUC: {metrics['roc_auc']:.4f}")


if __name__ == "__main__":
    main()
