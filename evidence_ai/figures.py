"""Export slide-ready figures from the sealed evidence reports."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from evidence_ai.replay import read
from evidence_ai.train import RELEASE

COLORS = ["#8c7960", "#4777a2", "#247465", "#a45428"]
LABELS = ["CS V2", "Logistic regression", "XGBoost", "Deep Sets"]


def save(figure, name):
    directory = RELEASE / "figures"
    directory.mkdir(exist_ok=True)
    for extension in ("svg", "png"):
        figure.savefig(directory / f"{name}.{extension}", dpi=180, facecolor="white")
    plt.close(figure)


def main():
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titleweight": "bold", "svg.fonttype": "none"})
    report = read(RELEASE / "synthetic/report.json")
    models = [value for key, value in report["models"].items() if key.startswith("M")]
    fig, axes = plt.subplots(1, 3, figsize=(11.8, 4.0), layout="constrained")
    for ax, (key, title) in zip(axes, [("critical_recall", "Critical-error recall"),
                                      ("average_precision", "Average precision"), ("review_workload", "Case workload")]):
        for i, (color, model) in enumerate(zip(COLORS, models)):
            estimate = model["test"][key]
            low, high = model["ci95"][key]
            ax.errorbar(estimate, i, xerr=[[estimate-low], [high-estimate]], marker="o", capsize=4, color=color)
            ax.annotate(f"{estimate:.3f}", (estimate, i), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9)
        ax.set(yticks=range(4), yticklabels=LABELS if ax == axes[0] else [], ylim=(3.5, -.5),
               title=title, xlim=(.35 if key == "average_precision" else .57, 1.04))
        ax.grid(axis="x", alpha=.18)
    fig.suptitle("Controlled synthetic evidence defects · locked test, 95% customer bootstrap CI")
    save(fig, "synthetic_comparison")

    fig, (ax, counts) = plt.subplots(2, 1, figsize=(7.2, 6.5), layout="constrained",
                                     gridspec_kw={"height_ratios": [3, 1]})
    ax.plot([0, 1], [0, 1], ls="--", color="#7b847b", label="Ideal")
    for j, (color, label, model) in enumerate(zip(COLORS, LABELS, models)):
        bins = model["reliability"]
        ax.plot([row["mean_prediction"] for row in bins], [row["event_rate"] for row in bins],
                marker="o", label=label, color=color)
        counts.bar([row["lower"] + .05 + .017 * (j - 1.5) for row in bins], [row["count"] for row in bins],
                   width=.016, color=color)
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean calibrated prediction", ylabel="Observed defect rate",
           title="Reliability on generated evidence defects")
    ax.legend(frameon=False, loc="upper left")
    counts.set(xlim=(0, 1), xlabel="Probability bin", ylabel="Documents")
    save(fig, "synthetic_calibration")

    fig, ax = plt.subplots(figsize=(8.1, 4.1), layout="constrained")
    variant_names = ["Full Deep Sets", "Drop metadata", "Drop relationships", "Drop CS components", "Drop text embedding"]
    variants = [report["models"][key] for key in ("M3_DEEP_SETS", "ABLATE_metadata", "ABLATE_relationships", "ABLATE_cs", "ABLATE_embedding")]
    for i, variant in enumerate(variants):
        v = variant["test"]["log_loss"]
        low, high = variant["ci95"]["log_loss"]
        ax.errorbar(v, i, xerr=[[v-low], [high-v]], marker="o", capsize=4, color=COLORS[-1] if i else COLORS[2])
    ax.set(yticks=range(len(variant_names)), yticklabels=variant_names, ylim=(4.5, -.5),
           xlabel="Test log loss · 95% customer bootstrap CI", title="One-group-at-a-time Deep Sets ablations")
    ax.grid(axis="x", alpha=.2)
    save(fig, "synthetic_ablations")

    cord = RELEASE / "cord-extraction"
    if (cord / "report.json").is_file():
        extraction = read(cord / "report.json")
        fields = sorted(((key, row) for key, row in extraction["test"]["field_metrics"].items() if row["gold"] >= 10),
                        key=lambda pair: pair[1]["gold"])
        fig, ax = plt.subplots(figsize=(8.2, 5.1), layout="constrained")
        ax.barh([key + f" (n={row['gold']})" for key, row in fields],
                [row["f1"] for _, row in fields], color="#247465")
        ax.set(xlim=(0, 1), xlabel="Exact category and word-span F1", title="CORD receipt extraction pilot · fields with ≥10 gold spans")
        save(fig, "cord_field_f1")


if __name__ == "__main__":
    main()
