"""
Explainability Layer — converts SHAP values into human-readable meteorological reasoning.

Architecture:
  1. Compute SHAP values for each prediction
  2. Rank features by |SHAP value|
  3. Map top-3 features to templated English phrases
  4. Assemble into a coherent sentence + advisory text
"""

import numpy as np
import pandas as pd
import shap
from loguru import logger
from typing import Literal


# Feature-to-phrase mapping table.
# Each key is a feature name prefix; values define how to interpret that feature.
# direction: "high_bad" = high feature value → higher bust risk, "low_bad" = low value → higher risk
FEATURE_TEMPLATES = {
    "run_jump_mm": {
        "direction": "high_bad",
        "high": "an unusually large 24-hour forecast change in rainfall (model is uncertain about the weather system)",
        "low": "stable forecast across consecutive model runs",
        "units": "mm",
        "threshold_high": 20.0,
        "threshold_low": 5.0,
    },
    "pressure_gradient": {
        "direction": "high_bad",
        "high": "a sharp pressure gradient indicating a fast-evolving synoptic system",
        "low": "a relatively flat pressure pattern",
        "units": "hPa/deg",
        "threshold_high": 2.0,
        "threshold_low": 0.5,
    },
    "wind_speed_850": {
        "direction": "high_bad",
        "high": "elevated low-level wind speeds suggesting an active monsoon surge or jet",
        "low": "weak low-level flow",
        "units": "m/s",
        "threshold_high": 15.0,
        "threshold_low": 5.0,
    },
    "pwat_value_anomaly": {
        "direction": "high_bad",
        "high": "anomalously high atmospheric moisture content (unusual wetness for the region/season)",
        "low": "below-normal atmospheric moisture",
        "units": "std devs",
        "threshold_high": 1.5,
        "threshold_low": -1.5,
    },
    "hist_bust_rate": {
        "direction": "high_bad",
        "high": "a historically high bust frequency for this region and season at this lead time",
        "low": "low historical bust frequency for this region and season",
        "units": "%",
        "threshold_high": 0.15,
        "threshold_low": 0.05,
    },
    "analogue_bust_rate": {
        "direction": "high_bad",
        "high": "similar past synoptic patterns that frequently led to forecast busts",
        "low": "past patterns similar to today that were generally well-forecast",
        "units": "%",
        "threshold_high": 0.20,
        "threshold_low": 0.05,
    },
    "rolling_error_7d": {
        "direction": "high_bad",
        "high": "the model has shown elevated errors over the past 7 days in this region",
        "low": "the model has performed reliably in this region recently",
        "units": "mm",
        "threshold_high": 25.0,
        "threshold_low": 8.0,
    },
    "error_trend_7d": {
        "direction": "high_bad",
        "high": "a worsening trend in recent model performance for this region",
        "low": "an improving trend in recent model performance",
        "units": "mm/day",
        "threshold_high": 2.0,
        "threshold_low": -2.0,
    },
    "has_depression_proxy": {
        "direction": "high_bad",
        "high": "the presence of a synoptic depression-like signal in the model fields (historically bust-prone)",
        "low": None,
        "units": "binary",
        "threshold_high": 0.5,
        "threshold_low": None,
    },
    "has_wd_proxy": {
        "direction": "high_bad",
        "high": "a Western Disturbance signal detected in upper-level fields",
        "low": None,
        "units": "binary",
        "threshold_high": 0.5,
        "threshold_low": None,
    },
    "lead_day": {
        "direction": "high_bad",
        "high": "the long lead time of this forecast (Day {value:.0f}), where NWP uncertainty is inherently high",
        "low": "the short lead time, where model skill is typically higher",
        "units": "days",
        "threshold_high": 6.0,
        "threshold_low": 3.0,
    },
    "precip_forecast_mm": {
        "direction": "high_bad",
        "high": "a high forecast rainfall amount (heavy/extreme events are harder to predict accurately)",
        "low": "a light forecast rainfall amount",
        "units": "mm",
        "threshold_high": 50.0,
        "threshold_low": 10.0,
    },
    "pressure_gradient_anomaly": {
        "direction": "high_bad",
        "high": "an anomalously strong pressure gradient (unusual flow pattern for region/season)",
        "low": "a weak pressure gradient anomaly",
        "units": "std devs",
        "threshold_high": 1.5,
        "threshold_low": -1.5,
    },
}


def _confidence_label(confidence: float) -> Literal["HIGH", "MODERATE", "LOW", "VERY LOW"]:
    if confidence >= 0.80:
        return "HIGH"
    elif confidence >= 0.60:
        return "MODERATE"
    elif confidence >= 0.40:
        return "LOW"
    else:
        return "VERY LOW"


def _confidence_color(confidence: float) -> str:
    """Returns hex color for UI display — green → amber → orange → red."""
    if confidence >= 0.80:
        return "#2ecc71"
    elif confidence >= 0.60:
        return "#f39c12"
    elif confidence >= 0.40:
        return "#e67e22"
    else:
        return "#e74c3c"


class ExplainabilityEngine:
    """
    Converts ML model output + SHAP values into human-readable explanations.

    Usage:
        engine = ExplainabilityEngine()
        result = engine.explain(
            bust_probability=0.72,
            shap_values=shap_array,
            feature_values=X_row,
            feature_names=model.feature_names,
        )
        print(result["summary"])   # plain-English sentence
        print(result["confidence"])  # 0.28
    """

    def explain(
        self,
        bust_probability: float,
        shap_values: np.ndarray,
        feature_values: pd.Series | dict,
        feature_names: list[str],
        n_top_features: int = 3,
    ) -> dict:
        """
        Generate a complete explanation dict for one prediction.

        Returns keys: bust_probability, confidence, confidence_label, confidence_color,
                       top_factors, summary, detail, advisory
        """
        confidence = 1.0 - bust_probability

        # Rank features by absolute SHAP impact
        shap_abs = pd.Series(np.abs(shap_values), index=feature_names).sort_values(ascending=False)
        shap_signed = pd.Series(shap_values, index=feature_names)

        top_factors = []
        phrases = []

        # Iterate through top candidates; stop once we have n_top_features with valid phrases
        for feat in shap_abs.index[:n_top_features * 2]:
            if len(top_factors) >= n_top_features:
                break

            feat_val = (
                feature_values[feat]
                if feat in (feature_values.keys() if isinstance(feature_values, dict) else feature_values.index)
                else np.nan
            )
            phrase = self._feature_to_phrase(feat, float(shap_signed[feat]), feat_val)

            if phrase:
                top_factors.append({
                    "feature": feat,
                    "shap_value": float(shap_signed[feat]),
                    "feature_value": float(feat_val) if not np.isnan(feat_val) else None,
                    "phrase": phrase,
                })
                phrases.append(phrase)

        summary = self._assemble_summary(confidence, phrases, bust_probability)
        detail = self._assemble_detail(confidence, top_factors)
        advisory = self._generate_advisory(confidence, bust_probability)

        return {
            "bust_probability": round(bust_probability, 3),
            "confidence": round(confidence, 3),
            "confidence_label": _confidence_label(confidence),
            "confidence_color": _confidence_color(confidence),
            "top_factors": top_factors,
            "summary": summary,
            "detail": detail,
            "advisory": advisory,
        }

    def explain_batch(
        self,
        bust_probabilities: np.ndarray,
        shap_values: np.ndarray,
        feature_df: pd.DataFrame,
        n_top_features: int = 3,
    ) -> list[dict]:
        """Explain a batch of predictions — e.g. all regions for one date."""
        return [
            self.explain(
                bust_probability=float(bust_probabilities[i]),
                shap_values=shap_values[i],
                feature_values=feature_df.iloc[i],
                feature_names=list(feature_df.columns),
                n_top_features=n_top_features,
            )
            for i in range(len(bust_probabilities))
        ]

    # ── Private helpers ──────────────────────────────────────────────────────

    def _feature_to_phrase(self, feature_name: str, shap_value: float, feature_value: float) -> str | None:
        """Map one (feature, SHAP value) pair to an English phrase. Returns None if no template matches."""
        template = None
        for key, tmpl in FEATURE_TEMPLATES.items():
            if feature_name.startswith(key) or feature_name == key:
                template = tmpl
                break

        if template is None:
            return None

        direction = template["direction"]
        is_increasing_risk = (
            (direction == "high_bad" and shap_value > 0) or
            (direction == "low_bad" and shap_value < 0)
        )

        # Skip features that are barely contributing
        if not is_increasing_risk and abs(shap_value) < 0.05:
            return None

        phrase = template["high"] if is_increasing_risk else template.get("low")
        if phrase is None:
            return None

        if "{value" in phrase and not np.isnan(feature_value):
            phrase = phrase.format(value=feature_value)

        return phrase

    def _assemble_summary(self, confidence: float, phrases: list[str], bust_prob: float) -> str:
        """One-sentence summary: confidence level + top reasons."""
        label = _confidence_label(confidence)
        pct = int(round(confidence * 100))

        if not phrases:
            return f"{label} confidence ({pct}%): forecast uncertainty is elevated based on model pattern analysis."

        if len(phrases) == 1:
            reason_str = phrases[0]
        elif len(phrases) == 2:
            reason_str = f"{phrases[0]}, and {phrases[1]}"
        else:
            reason_str = f"{phrases[0]}, {phrases[1]}, and {phrases[2]}"

        return f"{label} confidence ({pct}%): driven by {reason_str}."

    def _assemble_detail(self, confidence: float, top_factors: list[dict]) -> str:
        """Longer meteorological context for the drill-down panel."""
        if not top_factors:
            return "Insufficient feature data for detailed explanation."

        lines = ["Key factors increasing forecast uncertainty:"]
        for i, factor in enumerate(top_factors, 1):
            shap_sign = "↑ risk" if factor["shap_value"] > 0 else "↓ risk"
            lines.append(f"  {i}. {factor['phrase'].capitalize()} ({shap_sign})")

        return "\n".join(lines)

    def _generate_advisory(self, confidence: float, bust_prob: float) -> str:
        """Actionable advisory text for the forecaster."""
        if confidence >= 0.80:
            return (
                "Model agreement is high. Forecast can be used with standard confidence. "
                "Routine monitoring recommended."
            )
        elif confidence >= 0.60:
            return (
                "Moderate forecast uncertainty detected. Consider consulting ensemble "
                "spread or higher-resolution regional guidance before finalising the forecast."
            )
        elif confidence >= 0.40:
            return (
                "Elevated bust risk. Cross-check with latest ensemble output, satellite "
                "imagery, and any NWP model disagreement. Issue forecast with appropriate "
                "uncertainty range."
            )
        else:
            return (
                "CAUTION: Very high bust risk detected. This region/lead-time combination "
                "is in a historically unreliable pattern. Strongly recommend ensemble "
                "consensus approach and consider issuing a probabilistic or range-based "
                "forecast rather than a deterministic value."
            )


# ── Convenience function called by api/main.py ────────────────────────────────

def explain_single_prediction(model, X_row: pd.DataFrame, feature_names: list[str]) -> dict:
    """
    One-shot: runs inference + SHAP + explanation for one feature row.
    Handles both TreeExplainer (XGBoost/LightGBM) and KernelExplainer fallback.
    """
    engine = ExplainabilityEngine()

    # predict_proba returns shape (n_samples, n_classes); [0][1] = P(bust=1) for first row
    bust_prob = float(model.predict_proba(X_row)[0][1])

    # Try TreeExplainer first (fast); fall back to model's built-in method if available
    try:
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_row)
    except Exception:
        if hasattr(model, "get_shap_values"):
            shap_vals = model.get_shap_values(X_row)
        else:
            # No SHAP available — return explanation without SHAP factors
            logger.warning("SHAP computation failed; returning explanation without top factors.")
            shap_vals = np.zeros((1, len(feature_names)))

    # For binary classification TreeExplainer returns a list [class0_shap, class1_shap]
    if isinstance(shap_vals, list):
        shap_vals = shap_vals[1]

    shap_row = shap_vals[0] if shap_vals.ndim == 2 else shap_vals

    return engine.explain(
        bust_probability=bust_prob,
        shap_values=shap_row,
        feature_values=X_row.iloc[0],
        feature_names=feature_names,
    )


if __name__ == "__main__":
    # Smoke test with synthetic data
    engine = ExplainabilityEngine()
    dummy_shap = np.random.randn(15)
    dummy_features = pd.Series({
        "run_jump_mm": 35.2,
        "pressure_gradient": 3.1,
        "wind_speed_850": 18.4,
        "pwat_value_anomaly": 2.1,
        "hist_bust_rate": 0.18,
        "analogue_bust_rate": 0.22,
        "rolling_error_7d": 30.0,
        "error_trend_7d": 3.5,
        "has_depression_proxy": 1.0,
        "has_wd_proxy": 0.0,
        "lead_day": 7,
        "precip_forecast_mm": 85.0,
        "month_sin": 0.5,
        "month_cos": -0.866,
        "lead_day_norm": 0.67,
    })
    feature_names = list(dummy_features.index)

    result = engine.explain(
        bust_probability=0.74,
        shap_values=dummy_shap,
        feature_values=dummy_features,
        feature_names=feature_names,
    )
    print("Summary:", result["summary"])
    print("Advisory:", result["advisory"])
    print("Top factors:", [f["phrase"] for f in result["top_factors"]])
