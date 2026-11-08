"""Render publication figures from frozen aggregate results; never reopen holdout rows."""

import json

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from ml.predict import CANONICAL_RUN


def main():
    report = json.loads((CANONICAL_RUN / "report.json").read_text())
    candidates = json.loads((CANONICAL_RUN / "candidates.json").read_text())
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                        "svg.hashsalt": "cobi-uci350-v2"})
    fig, (ax, counts) = plt.subplots(2, 1, figsize=(6.3, 6.8), gridspec_kw={"height_ratios": [3, 1]}, layout="constrained")
    ax.plot([0, 1], [0, 1], color="#8c9695", linestyle="--", label="Perfect reliability")
    for key, name, color, offset in [
        ("selected_raw", "XGBoost raw", "#196d60", -0.017),
        ("selected_calibrated", "Sigmoid calibrated", "#a65415", 0.017),
    ]:
        bins = report["models"][key]["reliability"]
        nonempty = [row for row in bins if row["n"]]
        ax.plot([row["mean_predicted"] for row in nonempty], [row["observed_rate"] for row in nonempty],
                marker="o", color=color, label=name)
        counts.bar([row["lower"] + 0.05 + offset for row in bins], [row["n"] for row in bins],
                   width=0.034, color=color, label=name)
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean predicted probability", ylabel="Observed default rate",
           title="UCI 350 · locked test reliability")
    ax.legend(frameon=False, loc="upper left")
    counts.set(xlim=(0, 1), ylabel="Rows", xlabel="Fixed-width probability bin")
    fig.savefig(CANONICAL_RUN / "reliability.svg", metadata={"Date": None})
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), layout="constrained")
    for family, ax, step in zip(("xgb", "mlp"), axes, ("Boosting round", "Epoch")):
        best = min((row for row in candidates if row["family"] == family), key=lambda row: row["validation_loss"])
        rows = best["history"]
        for key, label, color in [("train_loss", "Train", "#196d60"), ("validation_loss", "Validation", "#a65415")]:
            ax.plot([row["step"] for row in rows], [row[key] for row in rows], label=label, color=color)
        ax.axvline(best["parameters"].get("best_epoch", best["parameters"].get("rounds")), color="#747b7a", linestyle="--")
        ax.set(xlabel=step, ylabel="Log loss / BCE", title=best["candidate"])
        ax.legend(frameon=False)
    fig.savefig(CANONICAL_RUN / "training.svg", metadata={"Date": None})
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.8, 4.2), layout="constrained")
    names = ["Train prevalence", "Logistic", "XGBoost raw", "XGBoost sigmoid"]
    for i, (name, result) in enumerate(zip(names, report["models"].values())):
        metric = result["metrics"]["log_loss"]
        p = metric["estimate"]
        low, high = metric["ci95"]
        ax.errorbar(p, i, xerr=[[p - low], [high - p]], fmt="o", capsize=4,
                    color="#a65415" if i == 3 else "#196d60")
    ax.set_yticks(range(len(names)), names)
    ax.invert_yaxis()
    ax.set(xlabel="Test log loss (95% row-bootstrap CI)", title="UCI 350 · probability quality")
    fig.savefig(CANONICAL_RUN / "experiment-results.svg", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    main()
