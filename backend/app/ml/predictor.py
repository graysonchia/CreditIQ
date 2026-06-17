from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[3]
SAVED_MODELS_DIR = ROOT_DIR / "saved_models"


class ModelNotAvailableError(RuntimeError):
    pass


class InvalidModelTypeError(ValueError):
    pass


class CreditIQPredictor:
    def __init__(self, models_dir: Path = SAVED_MODELS_DIR) -> None:
        self.models_dir = models_dir
        self.models: dict[str, Any | None] = {}
        self.features: dict[str, list[str]] = {}
        self.thresholds: dict[str, float] = {}
        self.model_versions: dict[str, str] = {}

        for model_type in ("credit_score", "default", "fraud"):
            model, features = self._load_model_bundle(model_type)
            self.models[model_type] = model
            self.features[model_type] = features
            self.thresholds[model_type] = self._load_threshold(model_type, 0.5)
            self.model_versions[model_type] = self._load_model_version(model_type)

        self.credit_score_model = self.models["credit_score"]
        self.default_model = self.models["default"]
        self.fraud_model = self.models["fraud"]
        self.credit_score_features = self.features["credit_score"]
        self.default_features = self.features["default"]
        self.fraud_features = self.features["fraud"]
        self.default_threshold = self.thresholds["default"]
        self.fraud_threshold = self.thresholds["fraud"]

    def _load_model_bundle(self, name: str) -> tuple[Any | None, list[str]]:
        model_path = self.models_dir / name / "model.joblib"
        features_path = self.models_dir / name / "features.json"
        if not model_path.exists() or not features_path.exists():
            return None, []

        model = joblib.load(model_path)
        features = json.loads(features_path.read_text(encoding="utf-8"))
        return model, features

    def _load_threshold(self, name: str, default: float) -> float:
        threshold_path = self.models_dir / name / "threshold.json"
        if not threshold_path.exists():
            return default
        return float(json.loads(threshold_path.read_text(encoding="utf-8")).get("threshold", default))

    def _load_model_version(self, name: str) -> str:
        model_path = self.models_dir / name / "model.joblib"
        if not model_path.exists():
            return "unavailable"
        return str(int(model_path.stat().st_mtime))

    def _validate_model_type(self, model_type: str) -> None:
        if model_type not in self.models:
            raise InvalidModelTypeError(f"Unsupported model type: {model_type}")

    def _value_for_feature(self, feature_name: str, raw_features: dict[str, Any]) -> float:
        if feature_name in raw_features:
            value = raw_features[feature_name]
            return float(value if value is not None else 0)

        for prefix in ("education_level", "employment_status", "loan_type", "merchant_category", "device_type", "transaction_type"):
            marker = f"{prefix}_"
            if feature_name.startswith(marker):
                expected_value = feature_name.removeprefix(marker)
                return float(str(raw_features.get(prefix, "")) == expected_value)

        return 0.0

    def _frame(self, features: dict[str, Any], feature_names: list[str]) -> pd.DataFrame:
        if not feature_names:
            raise ModelNotAvailableError("Feature metadata is missing for this model.")
        return pd.DataFrame([{name: self._value_for_feature(name, features) for name in feature_names}])

    def get_missing_features(self, model_type: str, features: dict[str, Any]) -> list[str]:
        self._validate_model_type(model_type)
        return [
            name
            for name in self.features[model_type]
            if name not in features and not any(name.startswith(f"{prefix}_") and prefix in features for prefix in ("education_level", "employment_status", "loan_type", "merchant_category", "device_type", "transaction_type"))
        ]

    def get_feature_frame(self, model_type: str, features: dict[str, Any]) -> pd.DataFrame:
        self._validate_model_type(model_type)
        return self._frame(features, self.features[model_type])

    def predict(self, model_type: str, features: dict[str, Any]) -> dict[str, Any]:
        self._validate_model_type(model_type)
        model = self.models[model_type]
        if model is None:
            raise ModelNotAvailableError(f"{model_type} model is not available.")

        frame = self.get_feature_frame(model_type, features)
        if model_type == "credit_score":
            value = float(model.predict(frame)[0])
            return {
                "model_type": model_type,
                "predicted_value": value,
                "predicted_label": None,
                "confidence_score": self.get_prediction_confidence(model_type, value),
                "model_version": self.model_versions[model_type],
                "missing_features": self.get_missing_features(model_type, features),
            }

        probability = self.predict_proba(model_type, features)
        threshold = self.thresholds[model_type]
        positive_label = "default" if model_type == "default" else "fraud"
        negative_label = "non_default" if model_type == "default" else "legitimate"
        label = positive_label if probability >= threshold else negative_label
        return {
            "model_type": model_type,
            "predicted_value": probability,
            "predicted_label": label,
            "confidence_score": self.get_prediction_confidence(model_type, probability),
            "model_version": self.model_versions[model_type],
            "missing_features": self.get_missing_features(model_type, features),
        }

    def predict_proba(self, model_type: str, features: dict[str, Any]) -> float:
        self._validate_model_type(model_type)
        if model_type == "credit_score":
            raise InvalidModelTypeError("credit_score is a regression model and has no probability output.")
        model = self.models[model_type]
        if model is None:
            raise ModelNotAvailableError(f"{model_type} model is not available.")
        frame = self.get_feature_frame(model_type, features)
        return float(model.predict_proba(frame)[0][1])

    def get_prediction_confidence(self, model_type: str, prediction: float) -> float:
        if model_type == "credit_score":
            distance_from_midpoint = abs(prediction - 575) / 275
            return float(max(0.5, min(0.99, 0.65 + distance_from_midpoint * 0.25)))
        return float(max(prediction, 1 - prediction))

    def predict_credit_score(self, customer_features: dict[str, Any]) -> float:
        return float(self.predict("credit_score", customer_features)["predicted_value"])

    def predict_loan_default(self, loan_features: dict[str, Any]) -> dict[str, Any]:
        result = self.predict("default", loan_features)
        return {"probability": result["predicted_value"], "label": result["predicted_label"]}

    def predict_fraud(self, transaction_features: dict[str, Any]) -> dict[str, Any]:
        result = self.predict("fraud", transaction_features)
        return {"probability": result["predicted_value"], "label": result["predicted_label"]}


predictor = CreditIQPredictor()


def predict_credit_score(customer_features: dict[str, Any]) -> float:
    return predictor.predict_credit_score(customer_features)


def predict_loan_default(loan_features: dict[str, Any]) -> dict[str, Any]:
    return predictor.predict_loan_default(loan_features)


def predict_fraud(transaction_features: dict[str, Any]) -> dict[str, Any]:
    return predictor.predict_fraud(transaction_features)
