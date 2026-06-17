from __future__ import annotations

import json
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
import optuna
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from db_utils import insert_model_metric


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "processed_credit_score.csv"
MODEL_DIR = ROOT_DIR / "saved_models" / "credit_score"
MLFLOW_TRACKING_URI = f"sqlite:///{(ROOT_DIR / 'mlflow.db').as_posix()}"


def evaluate(y_true, y_pred) -> dict[str, float]:
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": r2_score(y_true, y_pred),
    }


def main() -> None:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("credit_score_regression")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_PATH)
    x = df.drop(columns=["credit_score"])
    y = df["credit_score"]
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

    def objective(trial: optuna.Trial) -> float:
        model_name = trial.suggest_categorical("model", ["random_forest", "xgboost"])
        if model_name == "random_forest":
            model = RandomForestRegressor(
                n_estimators=trial.suggest_int("n_estimators", 100, 500),
                max_depth=trial.suggest_int("max_depth", 4, 24),
                min_samples_split=trial.suggest_int("min_samples_split", 2, 10),
                random_state=42,
                n_jobs=-1,
            )
        else:
            model = XGBRegressor(
                n_estimators=trial.suggest_int("n_estimators", 100, 600),
                max_depth=trial.suggest_int("max_depth", 3, 10),
                learning_rate=trial.suggest_float("learning_rate", 0.01, 0.25, log=True),
                subsample=trial.suggest_float("subsample", 0.7, 1.0),
                colsample_bytree=trial.suggest_float("colsample_bytree", 0.7, 1.0),
                objective="reg:squarederror",
                random_state=42,
                n_jobs=-1,
            )

        model.fit(x_train, y_train)
        preds = model.predict(x_test)
        return mean_absolute_error(y_test, preds)

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=20)

    best = study.best_params.copy()
    model_name = best.pop("model")
    model = (
        RandomForestRegressor(random_state=42, n_jobs=-1, **best)
        if model_name == "random_forest"
        else XGBRegressor(objective="reg:squarederror", random_state=42, n_jobs=-1, **best)
    )
    model.fit(x_train, y_train)
    preds = model.predict(x_test)
    metrics = evaluate(y_test, preds)

    with mlflow.start_run(run_name=f"best_{model_name}"):
        mlflow.log_param("model", model_name)
        mlflow.log_params(best)
        mlflow.log_metrics(metrics)
        if model_name == "xgboost":
            mlflow.xgboost.log_model(model, "model")
        else:
            mlflow.sklearn.log_model(model, "model")

    joblib.dump(model, MODEL_DIR / "model.joblib")
    (MODEL_DIR / "features.json").write_text(json.dumps(list(x.columns), indent=2), encoding="utf-8")
    insert_model_metric(
        model_name="credit_score",
        model_version=model_name,
        accuracy=metrics["r2"],
        dataset_size=len(df),
        notes=f"MAE={metrics['mae']:.4f}, RMSE={metrics['rmse']:.4f}, R2={metrics['r2']:.4f}",
    )

    print(f"Best model: {model_name}")
    print(f"MAE: {metrics['mae']:.4f}")
    print(f"RMSE: {metrics['rmse']:.4f}")
    print(f"R2: {metrics['r2']:.4f}")


if __name__ == "__main__":
    main()
