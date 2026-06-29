"""Evaluation metrics shared by training and reporting."""
import numpy as np


def regression_metrics(actual, point, low, high):
    actual = np.asarray(actual, float)
    point = np.asarray(point, float)
    low = np.asarray(low, float)
    high = np.asarray(high, float)

    err = point - actual
    ape = np.abs(err) / actual
    within = (actual >= low) & (actual <= high)
    rel_width = (high - low) / point

    # log-space R^2
    la, lp = np.log(actual), np.log(np.clip(point, 1, None))
    ss_res = np.sum((la - lp) ** 2)
    ss_tot = np.sum((la - la.mean()) ** 2)
    r2_log = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    return {
        "n": int(len(actual)),
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "mape_pct": float(np.mean(ape) * 100),
        "median_ape_pct": float(np.median(ape) * 100),
        "within_10pct": float(np.mean(ape <= 0.10) * 100),
        "within_20pct": float(np.mean(ape <= 0.20) * 100),
        "r2_log": float(r2_log),
        "coverage_90_pct": float(np.mean(within) * 100),
        "median_rel_interval_width_pct": float(np.median(rel_width) * 100),
    }


def fmt_aud(x):
    return f"${x:,.0f}"
