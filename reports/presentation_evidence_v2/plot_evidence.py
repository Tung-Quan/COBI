"""Scientific figures from frozen predictions and verified audit aggregates."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import precision_recall_curve, roc_curve

FIGURES = Path(__file__).resolve().parent / "figures"
LABELS = {"dummy": "Dummy", "logistic": "Logistic regression", "selected_raw": "XGBoost raw", "selected_calibrated": "XGBoost sigmoid"}
COLORS = {"dummy": "#647481", "logistic": "#405da0", "selected_raw": "#1e7565", "selected_calibrated": "#a54f1d"}
GREEN, BLUE, AMBER, GRAY = "#1e7565", "#405da0", "#a54f1d", "#647481"


def save(fig, name):
    FIGURES.mkdir(parents=True, exist_ok=True)
    for format in ("svg", "png"):
        fig.savefig(FIGURES / f"{name}.{format}", dpi=180, facecolor="white")
    plt.close(fig)


def panel(width=8, height=4.4):
    return plt.subplots(figsize=(width, height), layout="constrained")


def diagram(name, title, nodes, notes, secondary=None):
    fig, ax = panel(10, 3.35 if secondary else 2.7)
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    ax.text(.015, .91, title, fontsize=16, fontweight="bold")
    rows = [(nodes, .60, GREEN)]
    if secondary:
        rows.append((secondary, .33, BLUE))
    for labels, y, color in rows:
        centers = np.linspace(.105, .895, len(labels))
        for i, (x, label) in enumerate(zip(centers, labels)):
            ax.text(x, y, label, va="center", ha="center", fontsize=9.5, fontweight="bold", color=color,
                    bbox=dict(boxstyle="round,pad=.55", ec=color, fc="#f6f8f7", lw=1.2))
            if i:
                dx = (x - centers[i - 1]) * .43
                ax.annotate("", (x - dx, y), (centers[i - 1] + dx, y), arrowprops={"arrowstyle": "->", "color": GRAY})
    ax.text(.015, .07, notes, fontsize=9, color=GRAY, wrap=True)
    save(fig, name)


def render(audit, test, candidates, grouped):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 13, "axes.titleweight": "bold",
                         "axes.spines.top": False, "axes.spines.right": False, "axes.labelcolor": "#203a37",
                         "axes.titlecolor": "#153833", "svg.fonttype": "none", "figure.dpi": 120})
    models = audit["test_metrics"]
    cohorts = audit["dataset"]["cohorts"]
    pos = sum(row["events"] for row in cohorts.values())
    neg = sum(row["non_events"] for row in cohorts.values())
    fig, ax = panel(8, 2.8)
    ax.barh([0], [neg], color=BLUE, height=.40)
    ax.barh([0], [pos], left=neg, color=AMBER, height=.40)
    for x, n, label in [(neg / 2, neg, "No default"), (neg + pos / 2, pos, "Default")]:
        ax.text(x, 0, f"{label}\n{n:,} ({n / (pos+neg):.2%})", ha="center", va="center", color="white", weight="bold")
    ax.set(xlim=(0, neg + pos), ylim=(-.45, .45), title="Next-month default in UCI 350")
    ax.axis("off")
    ax.title.set_visible(True)
    save(fig, "class_distribution")

    diagram("dataset_processing", "Dataset processing and held-out roles",
            ["Official XLS / CSV\n30,000 rows", "19 predictors\nexclude ID and demographics",
             "Random stratified split\nseed 42", "Train-fitted scaler\n13 + 6 × 12 = 85"],
            "Only the train cohort fits preprocessing. The ordered roles below are separate cohorts. Source: UCI 350 and split lock.",
            ["Train\n18,000", "Validation\n4,500", "Calibration\n3,000", "Locked test\n4,500"])
    diagram("architecture", "COBI V2 workspaces",
            ["Synthetic case\nCredit Workbench", "Policy gates and\ncalculation", "Eligible review\nroutes", "Officer action\nand audit"],
            "The UCI schema and next-month label restrict predictions to Research Lab. Checkout PD remains unavailable.",
            ["UCI 350\nResearch Lab", "Locked experiment\nand evaluation", "Checksummed\nregistry", "UCI-only\nprediction"])
    diagram("workbench_flow", "Workbench calculation and review sequence",
            ["P1\nHard gates", "P2–P4\nEvidence and features", "P5–P7\nCapacity and scenario", "P8\nFeasible route", "P9\nOfficer audit"],
            "Failed hard gates yield HOLD and null scores. P10 runs a separate what-if calculation without changing the original.")
    diagram("pilot_measurement", "Proposed bank-approved pilot",
            ["Define cohort\nand approvals", "Shadow validation\nwith mature labels", "Controlled review\nworkflow comparison",
             "Monitor outcomes\nand safeguards"],
            "Proposed measures: decision time, processing cost, conversion, credit loss and officer workload. Current outcome status: NOT_MEASURED.")

    candidates_sorted = sorted(candidates, key=lambda row: row["validation_loss"])
    fig, ax = panel(8, 5.25)
    family_color = {"dummy": GRAY, "logistic": BLUE, "mlp": "#94764b", "xgb": GREEN}
    for i, row in enumerate(candidates_sorted):
        best = row["candidate"] == audit["selection"]["selected"]
        ax.scatter(row["validation_loss"], i, s=85 if best else 35, c=family_color[row["family"]],
                   marker="D" if best else "o", zorder=3)
        ax.text(row["validation_loss"] + .0015, i, f'{row["validation_loss"]:.6f}', va="center", fontsize=9)
    ax.set_yticks(range(len(candidates_sorted)), [row["candidate"] for row in candidates_sorted])
    ax.invert_yaxis()
    ax.set(xlim=(.423, .552), xlabel="Validation log loss (lower is better)", title="Eleven candidates on the validation cohort")
    ax.grid(axis="x", alpha=.2)
    save(fig, "validation_performance")

    fig, axs = plt.subplots(1, 2, figsize=(10, 4.3), layout="constrained")
    for ax, name, units in zip(axs, ("xgb-d2-lr0.1", "mlp-b128"), ("Boosting round", "Epoch")):
        row = next(row for row in candidates if row["candidate"] == name)
        trace = row["history"]
        best = row["parameters"].get("rounds", row["parameters"].get("best_epoch"))
        for key, label, color in [("train_loss", "Train", GREEN), ("validation_loss", "Validation", AMBER)]:
            ax.plot([h["step"] for h in trace], [h[key] for h in trace], lw=2, label=label, color=color)
        ax.axvline(best, linestyle="--", color=GRAY, label=f"Best {best}")
        ax.set(title=name, xlabel=units, ylabel="Log loss / BCE")
        ax.legend(frameon=False)
    save(fig, "training_performance")

    fig, axs = plt.subplots(1, 2, figsize=(10, 4.15), layout="constrained")
    for ax, (key, title) in zip(axs, [("roc_auc", "Discrimination"), ("log_loss", "Probability quality")]):
        for i, name in enumerate(LABELS):
            m = models[name]["metrics"][key]
            p, (lo, hi) = m["estimate"], m["ci95"]
            ax.errorbar(p, i, xerr=[[p-lo], [hi-p]], marker="o", color=COLORS[name], capsize=4)
            ax.annotate(f"{p:.4f}", (p, i), xytext=(0, 9), textcoords="offset points", ha="center", fontsize=9)
        ax.set_yticks(range(len(LABELS)), list(LABELS.values()))
        ax.set_ylim(3.45, -.45)
        ax.set_title(title)
        ax.set_xlabel(("ROC-AUC (higher)" if key == "roc_auc" else "Log loss (lower)") + " · 95% row bootstrap CI")
        ax.grid(axis="x", alpha=.2)
    save(fig, "test_comparison")

    y = test["y"].to_numpy()
    for name, title, curve in [("roc", "ROC on the locked UCI test", roc_curve),
                               ("precision_recall", "Precision–recall on the locked UCI test", precision_recall_curve)]:
        fig, ax = panel(6.8, 4.8)
        for key in ("dummy", "logistic", "selected_calibrated", "selected_raw"):
            x_values, y_values, _ = curve(y, test[key])
            if name == "precision_recall":
                x_values, y_values = y_values, x_values
            value = models[key]["metrics"]["roc_auc" if name == "roc" else "average_precision"]["estimate"]
            label = ("XGBoost raw and sigmoid" if key == "selected_raw" else LABELS[key]) + f" ({value:.3f})"
            if key == "selected_calibrated":  # Positive sigmoid slope preserves ranking and the curves coincide.
                continue
            ax.plot(x_values, y_values, color=COLORS[key], lw=2, label=label, drawstyle="steps-post" if name != "roc" else "default")
        if name == "precision_recall":
            ax.axhline(y.mean(), color=GRAY, linestyle=":", lw=1, label=f"Prevalence {y.mean():.1%}")
        ax.set(title=title, xlim=(0, 1), ylim=(0, 1.025),
               xlabel="False positive rate" if name == "roc" else "Recall", ylabel="True positive rate" if name == "roc" else "Precision")
        ax.legend(frameon=False, loc="lower right")
        save(fig, name)

    fig, (ax, count) = plt.subplots(2, 1, figsize=(7, 6), gridspec_kw={"height_ratios": [3, 1]}, layout="constrained")
    ax.plot([0, 1], [0, 1], linestyle=":", color=GRAY, label="Ideal")
    for key, offset in [("selected_raw", -.016), ("selected_calibrated", .016)]:
        bins = models[key]["reliability"]
        nonempty = [b for b in bins if b["n"]]
        ax.plot([b["mean_predicted"] for b in nonempty], [b["observed_rate"] for b in nonempty],
                marker="o", color=COLORS[key], label=LABELS[key])
        count.bar([b["lower"] + .05 + offset for b in bins], [b["n"] for b in bins], width=.031, color=COLORS[key])
    ax.set(title="Reliability on the locked UCI test", xlim=(0, 1), ylim=(0, 1), xlabel="Mean prediction in bin", ylabel="Observed default rate")
    ax.legend(frameon=False)
    count.set(xlim=(0, 1), xlabel="Fixed-width probability bin", ylabel="Rows")
    save(fig, "reliability")

    fig, ax = panel(8.1, 3.7)
    pair = next(p for p in audit["additional_paired_comparisons"] if p["first"] == "selected_calibrated" and p["reference"] == "selected_raw")
    for i, key in enumerate(("log_loss", "brier")):
        item = pair["metrics"][key]
        v, (lo, hi) = item["delta"], item["delta_ci95"]
        ax.errorbar(1000*v, i, xerr=[[1000*(v-lo)], [1000*(hi-v)]], marker="o", color=AMBER, capsize=5)
    ax.axvline(0, color=GRAY, linestyle=":")
    ax.set_yticks([0, 1], ["Log loss", "Brier"])
    ax.set_ylim(1.5, -.5)
    ax.set(title="Sigmoid minus raw probability error", xlabel="Paired change × 1,000 (positive is worse) · 95% bootstrap CI")
    ax.grid(axis="x", alpha=.2)
    save(fig, "calibration_delta")

    fig, ax = panel(8.6, 3.7)
    for i, (key, label) in enumerate([("full", "Full locked test"), ("unseen_in_train", "No exact train vector"), ("unseen_in_development", "No exact development vector")]):
        item = audit["duplicates"]["subsets"][key]
        val = item["calibrated_minus_raw_log_loss"]
        v, (lo, hi) = val["delta"], val["ci95"]
        ax.errorbar(1000*v, i, xerr=[[1000*(v-lo)], [1000*(hi-v)]], marker="o", color=[AMBER, GREEN, BLUE][i], capsize=5)
        ax.text(.995, i, f'n={item["n"]:,}', transform=ax.get_yaxis_transform(), ha="right", va="bottom", fontsize=9)
    ax.axvline(0, color=GRAY, linestyle=":")
    ax.set_yticks(range(3), ["Full locked test", "No exact train vector", "No exact development vector"])
    ax.set_ylim(2.45, -.45)
    ax.set(title="Post-hoc sensitivity to duplicate predictor vectors", xlabel="Sigmoid minus raw log loss × 1,000 · descriptive 95% CI")
    save(fig, "duplicate_sensitivity")

    explain = audit["explainability"]
    top = list(explain["mean_abs_grouped_shap"])[:10]
    fig, ax = panel(8.3, 4.9)
    ax.barh(top[::-1], [explain["mean_abs_grouped_shap"][name] for name in top[::-1]], color=GREEN)
    ax.set(title="XGBoost global source-feature attribution", xlabel="Mean absolute grouped TreeSHAP (raw log odds) · validation n=4,500")
    save(fig, "feature_importance")
    fig, ax = panel(8.3, 4.9)
    rng = np.random.default_rng(42)
    for i, name in enumerate(top[::-1]):
        contributions = grouped[name].to_numpy()
        y_positions = i + rng.uniform(-.23, .23, size=len(contributions))
        ax.scatter(contributions, y_positions, s=4, c=np.where(contributions >= 0, AMBER, BLUE),
                   alpha=.13, linewidth=0, rasterized=True)
    ax.axvline(0, color=GRAY, linestyle=":")
    ax.set_yticks(range(len(top)), top[::-1])
    ax.set(title="TreeSHAP distribution by source feature", xlabel="Grouped contribution to raw log odds · validation n=4,500")
    save(fig, "shap_summary")
    fig, ax = panel(7.4, 4.15)
    effect = explain["pay_0_partial_dependence"]
    x = np.arange(len(effect))
    ax.scatter(x, [p["average_raw_probability"] for p in effect], color=GREEN, s=50)
    ax.set_xticks(x, [str(p["code"]) for p in effect])
    ax.set(title="Model response to September repayment status", xlabel="PAY_0 category observed in validation", ylabel="Mean raw model probability")
    ax.set_ylim(bottom=0)
    ax.text(.02, .95, "Each category substituted across 4,500 validation records", transform=ax.transAxes, va="top", fontsize=9, color=GRAY)
    save(fig, "pay_0_response")

    affordability = audit["workbench"]["assessment"]["affordability"]
    fig, ax = panel(8.5, 3.65)
    values = [affordability[k] / 1e6 for k in ("proposed_installment_vnd", "dti_capacity_vnd", "residual_capacity_vnd")]
    ax.barh(["Contract payment", "DTI capacity", "Stressed residual capacity"], values, color=[BLUE, GREEN, AMBER])
    ax.invert_yaxis()
    for i, val in enumerate(values):
        ax.text(val + .06, i, f"{val:.3f}m", va="center", fontweight="bold")
    ax.set(xlim=(0, 5.5), xlabel="VND million per month", title="DEMO-001 affordability in the synthetic fixture")
    save(fig, "demo_001_trace")
