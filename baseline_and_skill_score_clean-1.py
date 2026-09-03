import argparse
import os
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score, average_precision_score

# add model.py directory to import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import BustModelTrainer

LABEL_COL = "is_bust"
DATE_COL = "init_date"
GROUP_COLS = ["region", "lead_day", "season"]
MIN_OBS = 5  # minimum group size


def load_raw(path):
    df = pd.read_parquet(path)
    required = GROUP_COLS + [LABEL_COL, DATE_COL]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns {missing}, got {list(df.columns)}")
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    return df


def positional_split(df):
    # 70/15/15 chronological split
    n = len(df)
    train_end = int(0.7 * n)
    val_end = int(0.85 * n)
    train = df.iloc[:train_end].reset_index(drop=True)
    val = df.iloc[train_end:val_end].reset_index(drop=True)
    test = df.iloc[val_end:].reset_index(drop=True)
    return train, val, test


def compute_climatology(train_df):
    # historical bust rate by group
    clim = (
        train_df.groupby(GROUP_COLS)[LABEL_COL]
        .agg(bust_rate="mean", n_obs="count")
        .reset_index()
    )
    clim.attrs["global_rate"] = train_df[LABEL_COL].mean()
    return clim


def predict_climatology(clim, query_df):
    merged = query_df.merge(clim, on=GROUP_COLS, how="left")
    global_rate = clim.attrs.get("global_rate")
    if global_rate is None:
        global_rate = float(np.average(clim["bust_rate"], weights=clim["n_obs"]))
    low_support = merged["n_obs"].isna() | (merged["n_obs"] < MIN_OBS)
    merged.loc[low_support, "bust_rate"] = global_rate
    return merged["bust_rate"]


def brier_skill_score(y_true, p_model, p_baseline):
    bs_model = brier_score_loss(y_true, p_model)
    bs_baseline = brier_score_loss(y_true, p_baseline)
    bss = 1 - (bs_model / bs_baseline) if bs_baseline > 0 else float("nan")
    return bss, bs_model, bs_baseline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="forecast_errors.parquet")
    parser.add_argument("--output-dir", default="ml/baseline/output")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    raw = load_raw(args.input)
    raw_sorted = raw.sort_values(DATE_COL).reset_index(drop=True)

    raw_train, raw_val, raw_test = positional_split(raw_sorted)
    print(f"rows -> train: {len(raw_train)}  val: {len(raw_val)}  test: {len(raw_test)}")
    print(f"test date range: {raw_test[DATE_COL].min()} to {raw_test[DATE_COL].max()}")

    # baseline
    clim = compute_climatology(raw_train)
    baseline_test_probs = predict_climatology(clim, raw_test)

    # model preprocessing
    trainer = BustModelTrainer()
    proc = trainer.preprocess(raw_sorted)
    proc_train, proc_val, proc_test = positional_split(proc)

    X_train = proc_train.drop(columns=[LABEL_COL])
    y_train = proc_train[LABEL_COL]
    X_test = proc_test.drop(columns=[LABEL_COL])
    y_test = proc_test[LABEL_COL]

    trainer.train(X_train, y_train)
    model_test_probs = trainer.model.predict_proba(X_test)[:, 1]

    if len(model_test_probs) != len(baseline_test_probs):
        raise RuntimeError(
            "model and baseline test sets differ in size"
        )
    y_true = y_test.reset_index(drop=True)

    bss, bs_model, bs_baseline = brier_skill_score(y_true, model_test_probs, baseline_test_probs)
    roc_model = roc_auc_score(y_true, model_test_probs)
    roc_baseline = roc_auc_score(y_true, baseline_test_probs)
    pr_model = average_precision_score(y_true, model_test_probs)
    pr_baseline = average_precision_score(y_true, baseline_test_probs)

    print(f"\nbrier - baseline: {bs_baseline:.4f}  model: {bs_model:.4f}")
    print(f"brier skill score: {bss:.4f}")
    print(f"roc-auc - baseline: {roc_baseline:.4f}  model: {roc_model:.4f}")
    print(f"pr-auc  - baseline: {pr_baseline:.4f}  model: {pr_model:.4f}")

    baseline_predictions = raw_test.copy()
    baseline_predictions["baseline_bust_probability"] = baseline_test_probs.values
    baseline_predictions["model_bust_probability"] = model_test_probs
    baseline_predictions["actual_is_bust"] = y_true.values
    baseline_predictions.to_parquet(
        os.path.join(args.output_dir, "baseline_predictions.parquet"), index=False
    )

    skill_score_data = pd.DataFrame([{
        "n_test_rows": len(y_true),
        "brier_baseline": bs_baseline,
        "brier_model": bs_model,
        "brier_skill_score": bss,
        "roc_auc_baseline": roc_baseline,
        "roc_auc_model": roc_model,
        "pr_auc_baseline": pr_baseline,
        "pr_auc_model": pr_model,
    }])
    skill_score_data.to_parquet(
        os.path.join(args.output_dir, "skill_score_data.parquet"), index=False
    )

    report_path = os.path.join(args.output_dir, "skill_score_report.md")
    with open(report_path, "w") as f:
        f.write("# Skill Score: ML Model vs Climatological Baseline\n\n")
        f.write(f"Test rows: {len(y_true)}\n\n")
        f.write("| Metric | Baseline | Model | Improvement |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| Brier score (lower=better) | {bs_baseline:.4f} | {bs_model:.4f} | {bs_baseline - bs_model:.4f} |\n")
        f.write(f"| ROC-AUC | {roc_baseline:.4f} | {roc_model:.4f} | {roc_model - roc_baseline:.4f} |\n")
        f.write(f"| PR-AUC | {pr_baseline:.4f} | {pr_model:.4f} | {pr_model - pr_baseline:.4f} |\n\n")
        f.write(f"**Brier Skill Score: {bss:.4f}**\n\n")
        f.write("(above 0 means the model's actually better than just guessing "
                 "the historical rate, 0 means no improvement, below 0 means "
                 "the model is somehow worse than the naive baseline)\n")

    print(f"\nsaved report to {report_path}")
    print(f"saved baseline_predictions.parquet and skill_score_data.parquet to {args.output_dir}")


if __name__ == "__main__":
    main()
