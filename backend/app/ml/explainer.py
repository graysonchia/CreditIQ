from __future__ import annotations

from typing import Any

import numpy as np
import shap

from app.ml.predictor import ModelNotAvailableError, predictor


class CreditIQExplainer:
    def __init__(self) -> None:
        self.explainers = {
            "credit_score": self._make_explainer(predictor.credit_score_model),
            "default": self._make_explainer(predictor.default_model),
            "fraud": self._make_explainer(predictor.fraud_model),
        }
        self.credit_score_explainer = self.explainers["credit_score"]
        self.default_explainer = self.explainers["default"]
        self.fraud_explainer = self.explainers["fraud"]

    def _make_explainer(self, model):
        if model is None:
            return None
        return shap.TreeExplainer(model)

    def _expected_value(self, explainer: Any) -> float | list[float] | None:
        value = getattr(explainer, "expected_value", None)
        if value is None:
            return None
        array = np.asarray(value)
        if array.ndim == 0:
            return float(array)
        return [float(item) for item in array.tolist()]

    def _class_values(self, shap_values: Any) -> np.ndarray:
        values = shap_values
        if isinstance(values, list):
            values = values[1] if len(values) > 1 else values[0]
        values = np.asarray(values)
        if values.ndim == 2:
            values = values[0]
        if values.ndim == 3:
            values = values[0, :, 1]
        return values

    def _top_impacts(self, shap_values: Any, feature_names: list[str], limit: int = 5) -> list[dict[str, Any]]:
        values = self._class_values(shap_values)
        ranked = sorted(
            zip(feature_names, values, strict=False),
            key=lambda item: abs(float(item[1])),
            reverse=True,
        )[:limit]
        return [
            {
                "feature": feature,
                "shap_value": float(value),
                "direction": "positive" if float(value) >= 0 else "negative",
            }
            for feature, value in ranked
        ]

    def explain(self, model_type: str, features: dict[str, Any], limit: int = 5) -> dict[str, Any]:
        explainer = self.explainers.get(model_type)
        if explainer is None:
            raise ModelNotAvailableError(f"{model_type} model is not available for SHAP explanation.")

        frame = predictor.get_feature_frame(model_type, features)
        shap_values = explainer.shap_values(frame)
        expected_value = self._expected_value(explainer)
        class_values = self._class_values(shap_values)
        base_value = expected_value[1] if isinstance(expected_value, list) and len(expected_value) > 1 else expected_value

        return {
            "model_type": model_type,
            "expected_value": expected_value,
            "base_value": base_value,
            "top_features": self._top_impacts(shap_values, list(frame.columns), limit=limit),
            "feature_contributions": [
                {
                    "feature": feature,
                    "shap_value": float(value),
                    "direction": "positive" if float(value) >= 0 else "negative",
                }
                for feature, value in zip(frame.columns, class_values, strict=False)
            ],
        }

    def global_feature_importance(self, model_type: str, limit: int = 20) -> list[dict[str, Any]]:
        model = predictor.models.get(model_type)
        if model is None:
            raise ModelNotAvailableError(f"{model_type} model is not available.")
        feature_names = predictor.features[model_type]
        values = getattr(model, "feature_importances_", None)
        if values is None:
            return []
        ranked = sorted(
            zip(feature_names, values, strict=False),
            key=lambda item: float(item[1]),
            reverse=True,
        )[:limit]
        return [{"feature": feature, "importance": float(value)} for feature, value in ranked]

    def explain_credit_score(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        return self.explain("credit_score", features)["top_features"]

    def explain_default(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        return self.explain("default", features)["top_features"]

    def explain_fraud(self, features: dict[str, Any]) -> list[dict[str, Any]]:
        return self.explain("fraud", features)["top_features"]


explainer = CreditIQExplainer()


def explain_credit_score(features: dict[str, Any]) -> list[dict[str, Any]]:
    return explainer.explain_credit_score(features)


def explain_fraud(features: dict[str, Any]) -> list[dict[str, Any]]:
    return explainer.explain_fraud(features)


def explain_default(features: dict[str, Any]) -> list[dict[str, Any]]:
    return explainer.explain_default(features)
