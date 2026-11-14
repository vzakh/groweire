"""Metrics, slices, reliability, plots and the model card (PLAN_10 task 13, brief §8.6)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

PLAIN_LOW_LT, PLAIN_HIGH_GE = 0.10, 0.25


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    out = {"n": int(len(y)), "base_rate": float(y.mean()) if len(y) else float("nan")}
    if len(np.unique(y)) < 2:
        return out | {"pr_auc": None, "roc_auc": None, "brier": float(brier_score_loss(y, p)),
                      "log_loss": None}
    return out | {
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
    }


def reliability(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    rows = []
    for b in range(bins):
        m = idx == b
        if m.any():
            rows.append({"bin": b, "p_mean": float(p[m].mean()), "obs": float(y[m].mean()),
                         "n": int(m.sum())})
    return rows


def slices(df: pd.DataFrame, y: np.ndarray, p: np.ndarray) -> dict:
    out: dict = {"by_month": {}, "by_crop_fraction_tercile": {}}
    for mon in sorted(df["mon"].unique()):
        m = (df["mon"] == mon).to_numpy()
        out["by_month"][int(mon)] = metrics(y[m], p[m])
    terc = pd.qcut(df["crop_fraction"].rank(method="first"), 3, labels=["low", "mid", "high"])
    for t in ["low", "mid", "high"]:
        m = (terc == t).to_numpy()
        out["by_crop_fraction_tercile"][t] = metrics(y[m], p[m])
    return out


def band_shares(p: np.ndarray) -> dict:
    return {
        "low": float((p < PLAIN_LOW_LT).mean()),
        "medium": float(((p >= PLAIN_LOW_LT) & (p < PLAIN_HIGH_GE)).mean()),
        "high": float((p >= PLAIN_HIGH_GE).mean()),
    }


def plot_reliability(curves: dict[str, list[dict]], path) -> None:
    import matplotlib  # pylint: disable=import-outside-toplevel

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # pylint: disable=import-outside-toplevel

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], color="#999", lw=1, ls="--", label="perfect")
    for name, rows in curves.items():
        ax.plot([r["p_mean"] for r in rows], [r["obs"] for r in rows], marker="o", label=name)
    ax.set(xlabel="predicted probability", ylabel="observed stress share", xlim=(0, 1), ylim=(0, 1),
           title="Reliability on holdout")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_case(monthly: pd.DataFrame, year: int, path) -> None:
    import matplotlib  # pylint: disable=import-outside-toplevel

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # pylint: disable=import-outside-toplevel

    names = ["Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"]
    fig, ax = plt.subplots(figsize=(7, 4))
    x = monthly.index.to_numpy()
    ax.bar(x - 0.2, monthly["observed"], width=0.4, label="observed stressed share (satellite)",
           color="#c9a227")
    ax.bar(x + 0.2, monthly["predicted"], width=0.4, label="model mean probability (year unseen)",
           color="#2f6f4f")
    ax.plot(x, monthly["climatology"], color="#555", ls="--", marker=".", label="usual year")
    ax.set_xticks(x, [names[m - 3] for m in x])
    ax.set(ylabel="share of farmed cells", ylim=(0, 1), title=f"{year}: model vs satellite, Ireland")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def metrics_markdown(table: dict[str, dict], extra: list[str]) -> str:
    lines = ["# Holdout metrics", "", "| Model | PR-AUC | ROC-AUC | Brier | Log-loss | n |",
             "|---|---|---|---|---|---|"]

    def f(v):
        return "n/a" if v is None else f"{v:.4f}"

    for name, m in table.items():
        lines.append(f"| {name} | {f(m.get('pr_auc'))} | {f(m.get('roc_auc'))} | "
                     f"{f(m.get('brier'))} | {f(m.get('log_loss'))} | {m['n']:,} |")
    return "\n".join(lines + [""] + extra) + "\n"
