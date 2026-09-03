import pandas as pd
import numpy as np
import os
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss


class BustModelTrainer:
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            n_jobs=-1
        )

    def load_data(self):
        path = "data/features/features.parquet"

        if not os.path.exists(path):
            raise FileNotFoundError("features.parquet not found in data/features/")

        df = pd.read_parquet(path)
        print(f"Loaded data: {df.shape}")
        return df

    def preprocess(self, df):
        df = df.copy()

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
        train_size = int(0.7 * len(df))
        val_size = int(0.15 * len(df))

        train = df.iloc[:train_size]
        val = df.iloc[train_size:train_size + val_size]
        test = df.iloc[train_size + val_size:]

        print(f"Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")

        return train, val, test

    def train(self, X, y):
        self.model.fit(X, y)

    def evaluate(self, X, y):
        # Handle single-class case safely
        if len(np.unique(y)) < 2:
            return {
                "roc_auc": 0.5,
                "pr_auc": 0.0,
                "brier": 0.0
            }

        probs = self.model.predict_proba(X)[:, 1]

        return {
            "roc_auc": roc_auc_score(y, probs),
            "pr_auc": average_precision_score(y, probs),
            "brier": brier_score_loss(y, probs)
        }

    def run(self, tune=False):
        import json

        df = self.load_data()

        if "is_bust" not in df.columns:
            raise ValueError("Column 'is_bust' not found in dataset")

        df = self.preprocess(df)

        train_df, val_df, test_df = self.split(df)

        X_train = train_df.drop(columns=["is_bust"])
        y_train = train_df["is_bust"]

        X_val = val_df.drop(columns=["is_bust"])
        y_val = val_df["is_bust"]

        X_test = test_df.drop(columns=["is_bust"])
        y_test = test_df["is_bust"]

        # Train
        self.train(X_train, y_train)

        # Evaluate
        print("\nTrain Metrics:")
        train_metrics = self.evaluate(X_train, y_train)
        print(train_metrics)

        print("\nValidation Metrics:")
        val_metrics = self.evaluate(X_val, y_val)
        print(val_metrics)

        print("\nTest Metrics:")
        test_metrics = self.evaluate(X_test, y_test)
        print(test_metrics)

        # Save model
        os.makedirs("models", exist_ok=True)
        joblib.dump(self.model, "models/model.joblib")
        print("Model saved to models/model.joblib")

        # Save evaluation results
        results = {
            "train": train_metrics,
            "val": val_metrics,
            "test": test_metrics
        }

        with open("models/evaluation_results.json", "w") as f:
            json.dump(results, f, indent=4)

        print("Evaluation results saved to models/evaluation_results.json")

        return self.model