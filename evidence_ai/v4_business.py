"""Illustrative business-cost sensitivity using registered E1 rates only."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml

from evidence_ai.replay import read
from evidence_ai.train import RELEASE
from evidence_ai.v4_experiments import MODELS, LABELS, COLORS, OUT, _v3_test, bootstrap
from ml.contracts import ROOT, write_json

CONFIG = OUT / "config/cost_scenarios.yaml"


def _write_csv(path: Path, rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _cost(cases: int, workload: float, critical_fn_per_case: float, volume: int,
          review_cost: float, missed_cost: float, inference_per_case: float, fixed: float) -> dict:
    flagged = volume * workload
    missed_documents = volume * critical_fn_per_case
    review_total = flagged * review_cost
    missed_total = missed_documents * missed_cost
    inference_total = volume * inference_per_case
    total = review_total + missed_total + inference_total + fixed
    return {"projected_applications": volume, "flagged_cases_expected": flagged,
            "missed_critical_documents_expected": missed_documents,
            "review_cost_vnd": review_total, "missed_error_cost_vnd": missed_total,
            "inference_cost_vnd": inference_total, "fixed_operating_cost_vnd": fixed,
            "total_cost_vnd": total}


def run():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8-sig"))
    e1 = read(OUT / "E1_RESULTS.json")
    test_cases, data, probabilities, lock = _v3_test()
    thresholds = {name: float(lock["all_thresholds"][name]) for name in MODELS}
    groups = [row["customer_group"] for row in test_cases]
    draws = int(read(OUT / "experiment_protocol.json")["bootstrap"]["draws"])
    seed = int(read(OUT / "experiment_protocol.json")["bootstrap"]["seed"])
    bootstrap_result = bootstrap(data, probabilities, thresholds, groups, draws, seed)
    rates = {
        name: {"cases": e1["models"][name]["cases"], "documents": e1["models"][name]["documents"],
               "case_workload": e1["models"][name]["review_workload"],
               "critical_false_negatives": e1["models"][name]["critical_false_negatives"],
               "critical_fn_per_case": e1["models"][name]["critical_fn_per_case"],
               "case_workload_ci95": e1["models"][name]["ci95"]["review_workload"],
               "critical_fn_per_case_ci95": e1["models"][name]["ci95"]["critical_fn_per_case"]}
        for name in MODELS
    }

    scenario_rows = []
    sensitivity: dict[str, dict] = {}
    for volume in config["application_volumes"]:
        for scenario in config["scenario_grid"]:
            review_cost = float(config["review_cost_per_flagged_case"][scenario["review"]])
            missed_cost = float(config["missed_critical_document_cost"][scenario["missed"]])
            baseline_cost = _cost(
                rates["M0_CS_V2"]["cases"], rates["M0_CS_V2"]["case_workload"],
                rates["M0_CS_V2"]["critical_fn_per_case"], int(volume), review_cost, missed_cost,
                float(config["inference_cost_per_application"]["cs_v2"]),
                float(config["fixed_operating_cost"]["cs_v2"]))
            for name in MODELS:
                model_cost = _cost(
                    rates[name]["cases"], rates[name]["case_workload"], rates[name]["critical_fn_per_case"],
                    int(volume), review_cost, missed_cost,
                    float(config["inference_cost_per_application"]["cs_v2"] if name == "M0_CS_V2"
                          else config["inference_cost_per_application"]["learned_model"]),
                    float(config["fixed_operating_cost"]["cs_v2"] if name == "M0_CS_V2"
                          else config["fixed_operating_cost"]["learned_model"]))
                savings = baseline_cost["total_cost_vnd"] - model_cost["total_cost_vnd"]
                scenario_rows.append({
                    "scenario_id": f"{scenario['id']}_volume_{volume}", "model": name,
                    "volume": int(volume), "review_assumption": scenario["review"],
                    "review_cost_per_flagged_case_vnd": review_cost,
                    "missed_error_assumption": scenario["missed"],
                    "missed_critical_cost_per_document_vnd": missed_cost,
                    "inference_cost_per_application_vnd": (
                        0 if name == "M0_CS_V2" else float(config["inference_cost_per_application"]["learned_model"])),
                    "fixed_operating_cost_vnd": (
                        0 if name == "M0_CS_V2" else float(config["fixed_operating_cost"]["learned_model"])),
                    **model_cost,
                    "baseline_cs_v2_cost_vnd": baseline_cost["total_cost_vnd"],
                    "savings_vs_cs_v2_vnd": savings,
                    "savings_rate": savings / baseline_cost["total_cost_vnd"] if baseline_cost["total_cost_vnd"] > 0 else None,
                    "interpretation": "illustrative assumption-based simulation",
                })
            sensitivity.setdefault(str(volume), {})[scenario["id"]] = {
                name: next(row for row in reversed(scenario_rows)
                           if row["scenario_id"] == f"{scenario['id']}_volume_{volume}" and row["model"] == name)["savings_vs_cs_v2_vnd"]
                for name in MODELS if name != "M0_CS_V2"
            }

    # Full 3x3 sensitivity at 10,000 cases, including combinations not in the compact scenario register.
    volume = 10_000
    review_levels = config["review_cost_per_flagged_case"]
    missed_levels = config["missed_critical_document_cost"]
    heatmap = {name: [] for name in MODELS if name != "M0_CS_V2"}
    for missed_label, missed_cost in missed_levels.items():
        row = []
        for review_label, review_cost in review_levels.items():
            baseline = _cost(1, rates["M0_CS_V2"]["case_workload"], rates["M0_CS_V2"]["critical_fn_per_case"],
                             volume, review_cost, missed_cost, 0, 0)["total_cost_vnd"]
            cell = {"missed_cost_level": missed_label, "review_cost_level": review_label,
                    "missed_cost_vnd": missed_cost, "review_cost_vnd": review_cost}
            for name in heatmap:
                inferred = _cost(1, rates[name]["case_workload"], rates[name]["critical_fn_per_case"],
                                 volume, review_cost, missed_cost,
                                 config["inference_cost_per_application"]["learned_model"],
                                 config["fixed_operating_cost"]["learned_model"])["total_cost_vnd"]
                cell[f"{name}_savings_vnd"] = baseline - inferred
            row.append(cell)
        for model in heatmap:
            heatmap[model].append([cell[f"{model}_savings_vnd"] for cell in row])

    # Sampling uncertainty holds each assumption fixed and resamples V3 customers.
    sampling = {}
    draws_by_model = bootstrap_result["_values"]
    for name in MODELS:
        sampling[name] = {}
        for scenario in config["scenario_grid"]:
            review_cost = float(config["review_cost_per_flagged_case"][scenario["review"]])
            missed_cost = float(config["missed_critical_document_cost"][scenario["missed"]])
            for volume in config["application_volumes"]:
                baseline_draws = []
                model_draws = []
                for w_cs, fn_cs, w_m, fn_m in zip(
                        draws_by_model["M0_CS_V2"]["review_workload"],
                        draws_by_model["M0_CS_V2"]["critical_fn_per_case"],
                        draws_by_model[name]["review_workload"],
                        draws_by_model[name]["critical_fn_per_case"], strict=True):
                    baseline_draws.append(_cost(1, w_cs, fn_cs, int(volume), review_cost, missed_cost, 0, 0)["total_cost_vnd"])
                    model_draws.append(_cost(1, w_m, fn_m, int(volume), review_cost, missed_cost,
                                              0 if name == "M0_CS_V2" else config["inference_cost_per_application"]["learned_model"],
                                              0 if name == "M0_CS_V2" else config["fixed_operating_cost"]["learned_model"])["total_cost_vnd"])
                delta = np.asarray(baseline_draws) - np.asarray(model_draws)
                sampling[name][f"{scenario['id']}_volume_{volume}"] = {
                    "savings_vnd_percentile_2_5_97_5": [float(x) for x in np.quantile(delta, [.025, .975])],
                    "draws": len(delta), "assumptions_held_fixed": True,
                    "sampling_unit": "customer_group",
                }

    # Analytic break-even missed-error cost at 10,000 applications.
    volume = 10_000
    break_even = {name: [] for name in MODELS if name != "M0_CS_V2"}
    for review_cost in np.linspace(float(min(review_levels.values())), float(max(review_levels.values())), 50):
        for name in break_even:
            review_delta = rates[name]["case_workload"] - rates["M0_CS_V2"]["case_workload"]
            missed_delta = rates[name]["critical_fn_per_case"] - rates["M0_CS_V2"]["critical_fn_per_case"]
            inference_delta = float(config["inference_cost_per_application"]["learned_model"])
            fixed_delta = float(config["fixed_operating_cost"]["learned_model"])
            numerator = volume * review_delta * review_cost + volume * inference_delta + fixed_delta
            value = None if abs(missed_delta) < 1e-12 else -numerator / (volume * missed_delta)
            break_even[name].append({"review_cost_per_case_vnd": float(review_cost),
                                     "break_even_missed_cost_vnd": float(value) if value is not None else None,
                                     "finite_nonnegative": bool(value is not None and value >= 0)})

    result = {
        "experiment_id": "cobi-evidence-v4-e3",
        "status": "ILLUSTRATIVE_ASSUMPTION_BASED_SIMULATION",
        "interpretation": "Scenario-based economic feasibility, not realized operational savings.",
        "currency": config["currency"], "assumption_file": "config/cost_scenarios.yaml",
        "assumptions": config,
        "measured_v3_synthetic_rates": rates,
        "scenario_rows": len(scenario_rows),
        "sampling_uncertainty": {
            "source": "300 customer-cluster bootstrap resamples of the frozen V3 synthetic test",
            "interpretation": "sampling variability conditional on the selected cost assumptions; does not cover uncertainty in assumed costs",
            "by_model_scenario_volume": sampling,
        },
        "assumption_grid_sensitivity_at_10000_applications": {
            "review_cost_levels": review_levels, "missed_error_cost_levels": missed_levels,
            "savings_vs_cs_v2_vnd": heatmap,
        },
        "break_even_frontier_at_10000_applications": break_even,
        "limitations": ["cost inputs are illustrative assumptions, not bank quotations",
                        "event rates are from a previously inspected synthetic test",
                        "case workload and missed-document counts have different denominators",
                        "no realized operational savings are measured"],
    }
    write_json(OUT / "E3_COST_RESULTS.json", result)
    _write_csv(OUT / "tables/business_scenarios.csv", scenario_rows)
    _write_figures(result, review_levels, missed_levels)
    _write_report(result, scenario_rows)
    return result


def _write_figures(result: dict, review_levels: dict, missed_levels: dict):
    fig_dir = OUT / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                         "axes.spines.right": False, "svg.fonttype": "none"})
    models = [name for name in MODELS if name != "M0_CS_V2"]
    volume_key = "10000"
    matrix = result["assumption_grid_sensitivity_at_10000_applications"]["savings_vs_cs_v2_vnd"]
    fig, axes = plt.subplots(1, len(models), figsize=(12.5, 4.2), layout="constrained")
    all_values = [value for name in models for row in matrix[name] for value in row]
    limit = max(abs(min(all_values)), abs(max(all_values)), 1)
    for ax, name in zip(axes, models, strict=True):
        array = np.asarray(matrix[name]) / 1_000_000
        image = ax.imshow(array, cmap="RdYlGn", vmin=-limit / 1_000_000, vmax=limit / 1_000_000)
        ax.set(xticks=range(3), xticklabels=[f"{x/1000:.0f}k" for x in review_levels.values()],
               yticks=range(3), yticklabels=[f"{x/1_000_000:g}m" for x in missed_levels.values()],
               xlabel="Review cost / flagged case (VND)", ylabel="Missed critical document cost (VND)",
               title=LABELS[name])
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{array[i,j]:.1f}m", ha="center", va="center", fontsize=8)
    cbar = fig.colorbar(image, ax=axes, shrink=.88)
    cbar.set_label("Estimated savings vs CS_V2 (million VND)")
    fig.suptitle("Illustrative cost sensitivity — 10,000 applications")
    fig.text(.01, -.03, "Positive values mean lower simulated cost than CS_V2. All unit costs and operating costs are assumptions; this is not a bank quote or measured saving.", fontsize=8)
    for ext in ("svg", "png"):
        fig.savefig(fig_dir / f"business_cost_sensitivity.{ext}", dpi=220, facecolor="white")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.4, 5.1), layout="constrained")
    for name, rows in result["break_even_frontier_at_10000_applications"].items():
        valid = [row for row in rows if row["break_even_missed_cost_vnd"] is not None]
        ax.plot([row["review_cost_per_case_vnd"] for row in valid],
                [row["break_even_missed_cost_vnd"] / 1_000_000 for row in valid],
                color=COLORS[name], label=LABELS[name])
    ax.set(xlabel="Assumed review cost per flagged case (VND)", ylabel="Break-even missed-error cost per critical document (million VND)",
           title="Analytic break-even frontier — 10,000 applications")
    ax.grid(alpha=.2)
    ax.legend(frameon=False)
    ax.text(.01, -.20, "Values below zero are economically infeasible under nonnegative missed-error costs for that review-cost assumption. Cost parameters remain illustrative.", transform=ax.transAxes, fontsize=8)
    for ext in ("svg", "png"):
        fig.savefig(fig_dir / f"business_break_even.{ext}", dpi=220, facecolor="white")
    plt.close(fig)


def _write_report(result: dict, rows: list[dict]):
    md = ["# E3 Business Cost Sensitivity", "",
          "**Interpretation: scenario-based economic feasibility, not realized operational savings.**", "",
          "Measured inputs are frozen V3 synthetic case-workload and critical false-negative rates. Review costs, missed-error costs, inference costs, fixed costs, and application volumes are assumptions in `config/cost_scenarios.yaml`; they are not bank quotations.", "",
          "## Cost equation", "",
          "`Total cost = flagged cases × review cost + missed critical evidence documents × missed-document cost + inference cost + fixed operating cost`.", "",
          "Review is charged per flagged case. Missed-error cost is charged per false-negative critical evidence document. The units differ and are not combined into one count.", "",
          "## Sampling variability and assumptions", "",
          "The report gives customer-cluster bootstrap distributions while holding each cost scenario fixed. Differences across cost assumptions are scenario sensitivity, not confidence intervals. The sample bootstrap conditions on the frozen models and thresholds.", "",
          "| Model | Cases flagged / case | Critical FN / case |", "|---|---:|---:|"]
    for name, row in result["measured_v3_synthetic_rates"].items():
        md.append(f"| {LABELS[name]} | {row['case_workload']:.4f} | {row['critical_fn_per_case']:.4f} |")
    md += ["", f"The scenario table contains {len(rows)} model-volume-assumption rows. See `tables/business_scenarios.csv`, `E3_COST_RESULTS.json`, and the sensitivity and break-even figures.", "",
           "No projected difference is a measured bank saving. The workbench's existing route-cost assumptions were not reused as document-verification costs."]
    (OUT / "E3_BUSINESS_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    output = run()
    print(json.dumps({"status": output["status"], "scenario_rows": output["scenario_rows"]}, indent=2))
