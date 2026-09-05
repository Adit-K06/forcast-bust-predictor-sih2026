import pandas as pd
import numpy as np
import os
import json
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    roc_auc_score, average_precision_score, brier_score_loss,
    precision_score, recall_score, f1_score, confusion_matrix
)

# Canonical paths — all relative to repo root
FEATURES_PATH = "features/features.parquet"      # Fix D: was 'data/features/features.parquet'
MODEL_PATH    = "ml_core/model.joblib"            # Fix D: was 'models/model.joblib'
EVAL_PATH     = "ml_core/evaluation_results.json" # Fix D: was 'models/evaluation_results.json'
SCHEMA_PATH   = "ml_core/feature_schema.json"


class BustModelTrainer:
    # Canonical model configuration — one source of truth.
    # Fix D: training script previously had n_estimators=100 but artifact had 50.
    # Canonical choice: 100 trees, depth 8, min_samples_leaf 10, balanced weights.
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_leaf=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

    def load_data(self):
        if not os.path.exists(FEATURES_PATH):
            raise FileNotFoundError(f"features.parquet not found at {FEATURES_PATH}")
        df = pd.read_parquet(FEATURES_PATH)
        print(f"Loaded data: {df.shape}")
        return df

    def preprocess(self, df):
        df = df.copy()

        # Explicit leak-prevention: these columns either ARE the label, or
        # were used to DEFINE the label (is_bust = abs_error_mm >= bust_threshold_mm).
        # Including them lets the model just recover a threshold comparison
        # instead of learning real signal — this was the bug causing 1.0 train AUC.
        leak_cols = ["abs_error_mm", "signed_error_mm", "precip_observed_mm", "bust_threshold_mm"]
        df = df.drop(columns=[c for c in leak_cols if c in df.columns])

        # Drop datetime columns
        for col in df.columns:
            if "date" in col.lower():
                df = df.drop(columns=[col])

        # Convert all object (string) columns to numeric
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype("category").cat.codes

        # Convert any remaining non-numeric safely
        for col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Fill missing values
        df = df.fillna(0)

        return df

    def split(self, df):
        # Fix D: enforce chronological sort before splitting to prevent temporal leakage
        if "init_date" in df.columns:
            df = df.sort_values("init_date").reset_index(drop=True)

        train_size = int(0.7 * len(df))
        val_size   = int(0.15 * len(df))

        train = df.iloc[:train_size]
        val   = df.iloc[train_size:train_size + val_size]
        test  = df.iloc[train_size + val_size:]

        print(f"Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
        return train, val, test

    def train(self, X, y):
        self.model.fit(X, y)

    def evaluate(self, X, y, split_name=""):
        if len(np.unique(y)) < 2:
            return {"roc_auc": 0.5, "pr_auc": 0.0, "brier": 0.0, "n": int(len(y))}

        probs = self.model.predict_proba(X)[:, 1]
        preds = self.model.predict(X)
        cm    = confusion_matrix(y, preds).tolist()

        metrics = {
            "n":         int(len(y)),
            "roc_auc":   round(roc_auc_score(y, probs), 4),
            "pr_auc":    round(average_precision_score(y, probs), 4),
            "brier":     round(brier_score_loss(y, probs), 4),
            "precision": round(precision_score(y, preds, zero_division=0), 4),
            "recall":    round(recall_score(y, preds, zero_division=0), 4),
            "f1":        round(f1_score(y, preds, zero_division=0), 4),
            "confusion_matrix": cm,
        }
        if split_name:
            print(f"  {split_name}: ROC-AUC={metrics['roc_auc']} PR-AUC={metrics['pr_auc']} "
                  f"Brier={metrics['brier']} F1={metrics['f1']}")
        return metrics

    def run(self, tune=False):
        df = self.load_data()

        if "is_bust" not in df.columns:
            raise ValueError("Column 'is_bust' not found in dataset")

        df = self.preprocess(df)
        train_df, val_df, test_df = self.split(df)

        X_train = train_df.drop(columns=["is_bust"])
        y_train = train_df["is_bust"]
        X_val   = val_df.drop(columns=["is_bust"])
        y_val   = val_df["is_bust"]
        X_test  = test_df.drop(columns=["is_bust"])
        y_test  = test_df["is_bust"]

        print(f"\nClass distribution (train): {y_train.value_counts().to_dict()}")

        # Train
        self.train(X_train, y_train)

        # Evaluate
        print("\nEvaluation:")
        train_metrics = self.evaluate(X_train, y_train, "Train")
        val_metrics   = self.evaluate(X_val,   y_val,   "Val")
        test_metrics  = self.evaluate(X_test,  y_test,  "Test")

        # Save model artifact
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(self.model, MODEL_PATH)
        print(f"Model saved to {MODEL_PATH}")
        print(f"  n_estimators={self.model.n_estimators}, "
              f"max_depth={self.model.max_depth}, "
              f"class_weight={self.model.class_weight}")

        # Save evaluation results
        results = {"train": train_metrics, "val": val_metrics, "test": test_metrics}
        with open(EVAL_PATH, "w") as f:
            json.dump(results, f, indent=4)
        print(f"Evaluation results saved to {EVAL_PATH}")

        # Save feature schema (canonical list for train/serve consistency check)
        schema = {
            "feature_names": list(X_train.columns),
            "n_features": len(X_train.columns),
            "label": "is_bust",
            "model_config": {
                "n_estimators": self.model.n_estimators,
                "max_depth": self.model.max_depth,
                "min_samples_leaf": self.model.min_samples_leaf,
                "class_weight": str(self.model.class_weight),
                "random_state": self.model.random_state,
            },
        }
        with open(SCHEMA_PATH, "w") as f:
            json.dump(schema, f, indent=4)
        print(f"Feature schema saved to {SCHEMA_PATH}")

        return self.model