"""Run with python -m lab. Output is written locally; no credentials are used."""
import argparse
import json
from pathlib import Path

from .engine import digest, run, simulate_response

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, default=ROOT / "lab/scenario.json")
    parser.add_argument("--policy", type=Path, default=ROOT / "lab/policy.json")
    parser.add_argument("--output", type=Path, default=ROOT / "build/lab")
    parser.add_argument("--simulate-approved", action="store_true",
                        help="Generate a synthetic approval and simulate local session revocation")
    args = parser.parse_args()
    scenario = json.loads(args.scenario.read_text())
    policy = json.loads(args.policy.read_text())
    report = run(scenario, policy)
    args.output.mkdir(parents=True, exist_ok=True)
    args.output.joinpath("report.json").write_text(json.dumps(report, indent=2) + "\n")
    state_path = args.output / "response-state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {"actions": {}}
    actions = []
    if args.simulate_approved:
        for case in report["alerts"]:
            approval = {"case_fingerprint": case["fingerprint"], "action": "revoke_session",
                        "reviewer": "synthetic-incident-commander", "issued_at": scenario["as_of"],
                        "expires_at": "2026-10-01T11:00:00Z"}
            state, outcome = simulate_response(case, approval, policy, state, scenario["as_of"])
            actions.append({"case_id": case["case_id"], "outcome": outcome})
        state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    args.output.joinpath("run-manifest.json").write_text(json.dumps({
        "scenario_sha256": digest(scenario), "policy_sha256": digest(policy),
        "report_sha256": digest(report), "responses": actions}, indent=2) + "\n")
    print(json.dumps({"alerts": len(report["alerts"]), "quarantined": len(report["quarantined_events"]),
                      "duplicates": report["duplicate_events"], "responses": actions}))


if __name__ == "__main__":
    main()
