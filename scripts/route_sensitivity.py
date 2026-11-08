"""E5 grid on synthetic fixtures, comparing two policies over the same feasible sets."""

import itertools
import json

from backend.app.calculations import DEFAULT_ROUTE_COSTS_VND, POLICY_VERSION, calculate_application
from ml.contracts import ROOT, write_json


def main():
    seed = ROOT / "backend/data"
    applications = json.loads((seed / "seed_applications.json").read_text())
    demo = json.loads((seed / "demo_001_v2.json").read_text())
    rows = []
    for dti, buffer, fast_cost in itertools.product((.25, .35, .45), (.15, .25, .35), (42000, 130000)):
        costs = DEFAULT_ROUTE_COSTS_VND | {"FAST_TRACK_CANDIDATE": fast_cost}
        cases = []
        for original in applications:
            case = original | (demo if original["application_id"] == demo["application_id"] else {})
            routing = calculate_application(case, costs, dti, buffer=buffer).routing
            feasible = routing["eligible_routes"]
            baseline = next(route for route in ("STANDARD_REVIEW", "ENHANCED_REVIEW", "HOLD_FOR_HUMAN_HANDLING") if route in feasible)
            selected = routing["recommended_route"]
            cases.append({"application_id": case["application_id"], "fixed": baseline, "constrained": selected,
                          "eligible": feasible, "assumed_difference_vnd": costs[baseline] - costs[selected]})
        rows.append({"max_dti": dti, "buffer": buffer, "fast_track_cost_vnd": fast_cost, "cases": cases,
                     "assumed_difference_vnd": sum(case["assumed_difference_vnd"] for case in cases)})
    write_json(ROOT / "reports/final/route-sensitivity.json",
               {"status": "SIMULATED_ROUTE_COMPARISON", "policy": POLICY_VERSION,
                "comparison": "fixed eligible order standard, enhanced, hold versus minimum eligible assumed cost",
                "grid": rows})


if __name__ == "__main__":
    main()
