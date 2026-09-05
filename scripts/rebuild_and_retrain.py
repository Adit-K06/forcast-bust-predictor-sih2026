"""
Phase 3+4 combined script:
1. Rebuilds hist_bust_rate in features.parquet using a leakage-safe expanding window.
2. Verifies the fix (earliest != latest dates have different rates).
3. Retrains the RandomForest on the clean features.
4. Saves model artifact + evaluation results + feature schema.
5. Computes Brier Skill Score vs climatological baseline.

Run from repo root: python scripts/rebuild_and_retrain.py
"""
import sys, os
sys.path.insert(0, '.')

import json
import numpy as np
import pandas as pd
import joblib

print("=" * 60)
print("Step 1: Load existing features.parquet")
print("=" * 60)

FEATURES_PATH = "features/features.parquet"
df = pd.read_parquet(FEATURES_PATH)
df['init_date'] = pd.to_datetime(df['init_date'])
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"Regions: {df['region'].unique()}")
print(f"Date range: {df['init_date'].min().date()} to {df['init_date'].max().date()}")
print(f"Overall bust rate: {df['is_bust'].mean():.4f}")
print(f"Old hist_bust_rate range: {df['hist_bust_rate'].min():.4f} – {df['hist_bust_rate'].max():.4f}")

print("\n" + "=" * 60)
print("Step 2: Rebuild hist_bust_rate (leakage-safe expanding window)")
print("=" * 60)

global_prior = float(df['is_bust'].mean())
df = df.sort_values(['region', 'season', 'lead_day', 'init_date']).reset_index(drop=True)

def expanding_bust_rate(group):
    """
    For each row at date t, hist_bust_rate(t) = mean(is_bust for all prior rows
    in the same (region, season, lead_day) group with init_date < t).
    shift(1) ensures the current row's own label is never included.
    """
    group['hist_bust_rate'] = (
        group['is_bust'].shift(1).expanding(min_periods=1).mean()
    )
    return group

print("Computing expanding bust rates (this may take a minute)...")
df = df.groupby(['region', 'season', 'lead_day'], group_keys=False).apply(expanding_bust_rate)
df['hist_bust_rate'] = df['hist_bust_rate'].fillna(global_prior)

new_min = round(float(df['hist_bust_rate'].min()), 4)
new_max = round(float(df['hist_bust_rate'].max()), 4)
print(f"New hist_bust_rate range: {new_min} – {new_max}")

# Verify: earliest rows should have rate near global prior; latest reflect actual history
df_sorted = df.sort_values('init_date')
earliest_rate = round(float(df_sorted.head(200)['hist_bust_rate'].mean()), 4)
latest_rate   = round(float(df_sorted.tail(200)['hist_bust_rate'].mean()), 4)
print(f"Earliest 200 rows avg hist_bust_rate: {earliest_rate}  (should be ~{round(global_prior,4)})")
print(f"Latest 200 rows avg hist_bust_rate:   {latest_rate}  (should differ from earliest)")

leakage_fixed = abs(earliest_rate - latest_rate) > 0.001
print(f"Leakage fix verified: {'YES' if leakage_fixed else 'WARNING - rates too similar, check fix'}")

print("\nSaving fixed features.parquet...")
df.to_parquet(FEATURES_PATH, index=False)
print(f"Saved: {FEATURES_PATH}")

print("\n" + "=" * 60)
print("Step 3: Train/Val/Test split (chronological)")
print("=" * 60)

from ml_core.main import BustModelTrainer

trainer = BustModelTrainer()

# Preprocess uses the trainer's leak-col removal and encoding
df_proc = trainer.preprocess(df)

# Chronological sort is done inside split(), but assert it here too
df_proc = df_proc.sort_values('init_date').reset_index(drop=True) if 'init_date' in df_proc.columns else df_proc

train_df, val_df, test_df = trainer.split(df_proc)

X_train = train_df.drop(columns=['is_bust'])
y_train = train_df['is_bust']
X_val   = val_df.drop(columns=['is_bust'])
y_val   = val_df['is_bust']
X_test  = test_df.drop(columns=['is_bust'])
y_test  = test_df['is_bust']

print(f"Train bust rate: {y_train.mean():.4f} | n={len(y_train):,}")
print(f"Val bust rate:   {y_val.mean():.4f} | n={len(y_val):,}")
print(f"Test bust rate:  {y_test.mean():.4f} | n={len(y_test):,}")
print(f"Features used: {list(X_train.columns)}")

print("\n" + "=" * 60)
print("Step 4: Train RandomForest")
print("=" * 60)
print(f"Config: n_estimators={trainer.model.n_estimators}, "
      f"max_depth={trainer.model.max_depth}, "
      f"min_samples_leaf={trainer.model.min_samples_leaf}, "
      f"class_weight={trainer.model.class_weight}")

trainer.train(X_train, y_train)

print("\nEvaluation:")
train_metrics = trainer.evaluate(X_train, y_train, "Train")
val_metrics   = trainer.evaluate(X_val,   y_val,   "Val")
test_metrics  = trainer.evaluate(X_test,  y_test,  "Test")

print("\n" + "=" * 60)
print("Step 5: Save artifacts")
print("=" * 60)

MODEL_PATH  = "ml_core/model.joblib"
EVAL_PATH   = "ml_core/evaluation_results.json"
SCHEMA_PATH = "ml_core/feature_schema.json"

os.makedirs("ml_core", exist_ok=True)
joblib.dump(trainer.model, MODEL_PATH)
print(f"Model saved: {MODEL_PATH}")

results = {"train": train_metrics, "val": val_metrics, "test": test_metrics}
with open(EVAL_PATH, "w") as f:
    json.dump(results, f, indent=4)
print(f"Evaluation saved: {EVAL_PATH}")

schema = {
    "feature_names": list(X_train.columns),
    "n_features": len(X_train.columns),
    "label": "is_bust",
    "leakage_safe": True,
    "hist_bust_rate_method": "chronological expanding window with shift(1)",
    "model_config": {
        "n_estimators": trainer.model.n_estimators,
        "max_depth": trainer.model.max_depth,
        "min_samples_leaf": trainer.model.min_samples_leaf,
        "class_weight": str(trainer.model.class_weight),
        "random_state": trainer.model.random_state,
    },
}
with open(SCHEMA_PATH, "w") as f:
    json.dump(schema, f, indent=4)
print(f"Feature schema saved: {SCHEMA_PATH}")

print("\n" + "=" * 60)
print("Step 6: Brier Skill Score vs climatological baseline")
print("=" * 60)

from sklearn.metrics import brier_score_loss, roc_auc_score, average_precision_score

# Climatology baseline: bust rate per (region, season, lead_day) from TRAINING data only
raw = pd.read_parquet(FEATURES_PATH)
raw['init_date'] = pd.to_datetime(raw['init_date'])
raw = raw.sort_values('init_date').reset_index(drop=True)

n = len(raw)
raw_train = raw.iloc[:int(0.70 * n)]
raw_test  = raw.iloc[int(0.85 * n):]

clim = (raw_train.groupby(['region', 'season', 'lead_day'])['is_bust']
        .mean().reset_index().rename(columns={'is_bust': 'bust_rate'}))
global_rate = float(raw_train['is_bust'].mean())

test_merged = raw_test.merge(clim, on=['region','season','lead_day'], how='left')
test_merged['bust_rate'] = test_merged['bust_rate'].fillna(global_rate)
baseline_probs = test_merged['bust_rate'].values
y_true = raw_test['is_bust'].values

model_probs = trainer.model.predict_proba(X_test)[:, 1]

bs_model    = brier_score_loss(y_true, model_probs)
bs_baseline = brier_score_loss(y_true, baseline_probs)
bss = 1.0 - (bs_model / bs_baseline) if bs_baseline > 0 else float('nan')

roc_m = roc_auc_score(y_true, model_probs)
pr_m  = average_precision_score(y_true, model_probs)

print(f"\nBaseline Brier Score:  {bs_baseline:.4f}")
print(f"Model Brier Score:     {bs_model:.4f}")
print(f"★ Brier Skill Score:   {bss:.4f}")
print(f"Model ROC-AUC:         {roc_m:.4f}")
print(f"Model PR-AUC:          {pr_m:.4f}")

skill = {
    "n_test_rows":       int(len(y_true)),
    "brier_baseline":    round(float(bs_baseline), 4),
    "brier_model":       round(float(bs_model), 4),
    "brier_skill_score": round(float(bss), 4),
    "roc_auc_model":     round(float(roc_m), 4),
    "pr_auc_model":      round(float(pr_m), 4),
    "note": "Climatology = training-only bust rate per (region, season, lead_day). "
            "hist_bust_rate fixed with expanding window (no leakage). "
            "No formal significance test performed.",
}
os.makedirs("ml_core/evaluation", exist_ok=True)
with open("ml_core/evaluation/skill_score_data.json", "w") as f:
    json.dump(skill, f, indent=2)
print(f"\nSkill score saved: ml_core/evaluation/skill_score_data.json")

print("\n" + "=" * 60)
print("DONE — Artifacts ready:")
print(f"  {MODEL_PATH}")
print(f"  {EVAL_PATH}")
print(f"  {SCHEMA_PATH}")
print(f"  ml_core/evaluation/skill_score_data.json")
print("=" * 60)
