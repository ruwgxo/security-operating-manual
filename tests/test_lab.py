import copy
import json
import unittest
from pathlib import Path

from lab.engine import instant, run, simulate_response

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.scenario = json.loads((ROOT / "lab/scenario.json").read_text())
        self.policy = json.loads((ROOT / "lab/policy.json").read_text())

    def test_scenario_evidence_and_benign_controls(self):
        report = run(self.scenario, self.policy)
        self.assertEqual(len(report["alerts"]), 1)
        case = report["alerts"][0]
        self.assertEqual(case["bytes_read"], 110000000)
        self.assertEqual([e["event_id"] for e in case["evidence"]],
                         ["auth-suspect", "read-01", "read-02"])
        self.assertEqual(report["duplicate_events"], 1)
        self.assertEqual(report["quarantined_events"][0]["event_id"], "auth-malformed")
        self.assertEqual(report["missing_sources"], [])

    def test_shuffled_ingestion_is_deterministic(self):
        expected = run(self.scenario, self.policy)
        self.scenario["events"].reverse()
        self.assertEqual(run(self.scenario, self.policy), expected)

    def test_expired_indicator_does_not_correlate(self):
        self.scenario["intelligence"][0]["valid_until"] = self.scenario["as_of"]
        self.assertEqual(run(self.scenario, self.policy)["alerts"], [])

    def test_indicator_not_known_at_authentication_does_not_correlate(self):
        self.scenario["intelligence"][0]["valid_from"] = "2026-10-01T10:01:00Z"
        self.assertEqual(run(self.scenario, self.policy)["alerts"], [])

    def test_low_confidence_indicator_does_not_correlate(self):
        self.scenario["intelligence"][0]["confidence"] = "low"
        self.assertEqual(run(self.scenario, self.policy)["alerts"], [])

    def test_missing_indicator_provenance_is_reported(self):
        self.scenario["intelligence"][0]["source"] = ""
        report = run(self.scenario, self.policy)
        self.assertEqual(report["alerts"], [])
        self.assertEqual(len(report["intelligence_errors"]), 1)

    def test_restricted_intelligence_is_rejected(self):
        self.scenario["intelligence"][0]["tlp"] = "TLP:AMBER+STRICT"
        self.assertEqual(len(run(self.scenario, self.policy)["intelligence_errors"]), 1)

    def test_threshold_boundary(self):
        self.policy["minimum_bytes"] = 110000000
        self.assertEqual(len(run(self.scenario, self.policy)["alerts"]), 1)
        self.policy["minimum_bytes"] += 1
        self.assertEqual(run(self.scenario, self.policy)["alerts"], [])

    def test_window_boundary(self):
        for e in self.scenario["events"]:
            if e["event_id"] == "read-02":
                e["occurred_at"] = "2026-10-01T10:15:00Z"
        self.assertEqual(len(run(self.scenario, self.policy)["alerts"]), 1)
        for e in self.scenario["events"]:
            if e["event_id"] == "read-02":
                e["occurred_at"] = "2026-10-01T10:15:01Z"
        self.assertEqual(run(self.scenario, self.policy)["alerts"], [])

    def test_cross_identity_cannot_supply_read_evidence(self):
        for e in self.scenario["events"]:
            if e["kind"] == "object_read":
                e["identity_id"] = "backup-01"
        self.assertEqual(run(self.scenario, self.policy)["alerts"], [])

    def test_failed_reads_do_not_count(self):
        for e in self.scenario["events"]:
            if e["kind"] == "object_read":
                e["outcome"] = "failure"
        self.assertEqual(run(self.scenario, self.policy)["alerts"], [])

    def test_failed_authentication_does_not_correlate(self):
        for e in self.scenario["events"]:
            if e["kind"] == "authentication":
                e["outcome"] = "failure"
        self.assertEqual(run(self.scenario, self.policy)["alerts"], [])

    def test_conflicting_duplicate_quarantines_both_versions(self):
        other = copy.deepcopy(self.scenario["events"][2])
        other["source_ip"] = "192.0.2.99"
        self.scenario["events"].append(other)
        report = run(self.scenario, self.policy)
        self.assertEqual(report["alerts"], [])
        self.assertEqual(sum(e["reason"] == "conflicting duplicate event_id"
                             for e in report["quarantined_events"]), 2)

    def test_missing_telemetry_is_visible(self):
        self.scenario["events"] = [e for e in self.scenario["events"] if e["kind"] != "object_read"]
        report = run(self.scenario, self.policy)
        self.assertEqual(report["missing_sources"], ["object-store"])
        self.assertEqual(report["alerts"], [])

    def test_invalid_bytes_and_unknown_identity_are_quarantined(self):
        self.scenario["events"][1]["bytes"] = True
        self.scenario["events"][0]["identity_id"] = "unknown"
        report = run(self.scenario, self.policy)
        self.assertTrue(any("bytes" in e["reason"] for e in report["quarantined_events"]))
        self.assertTrue(any("unknown identity" in e["reason"] for e in report["quarantined_events"]))

    def test_future_receipt_is_quarantined(self):
        self.scenario["events"][2]["received_at"] = "2026-10-01T11:00:00Z"
        self.assertEqual(run(self.scenario, self.policy)["alerts"], [])

    def test_wrong_source_is_quarantined(self):
        self.scenario["events"][2]["source"] = "object-store"
        self.assertEqual(run(self.scenario, self.policy)["alerts"], [])

    def test_malformed_event_id_and_indicator_do_not_crash_batch(self):
        self.scenario["events"].append({"event_id": ["invalid"]})
        self.scenario["intelligence"].append("invalid")
        report = run(self.scenario, self.policy)
        self.assertEqual(len(report["alerts"]), 1)
        self.assertEqual(len(report["quarantined_events"]), 2)
        self.assertEqual(len(report["intelligence_errors"]), 1)

    def test_context_change_invalidates_case_fingerprint(self):
        original = run(self.scenario, self.policy)["alerts"][0]["fingerprint"]
        self.scenario["assets"]["ledger-export"]["owner"] = "Another synthetic team"
        self.assertNotEqual(run(self.scenario, self.policy)["alerts"][0]["fingerprint"], original)

    def test_invalid_config_fails_before_evaluation(self):
        self.policy["window_seconds"] = True
        with self.assertRaises(ValueError):
            run(self.scenario, self.policy)

    def test_timestamp_requires_timezone(self):
        with self.assertRaises(ValueError):
            instant("2026-10-01T10:00:00")

    def test_response_approval_replay_and_recovery_record(self):
        case = run(self.scenario, self.policy)["alerts"][0]
        approval = {"case_fingerprint": case["fingerprint"], "action": "revoke_session",
                    "reviewer": "synthetic-reviewer", "issued_at": "2026-10-01T10:20:00Z",
                    "expires_at": "2026-10-01T11:00:00Z"}
        state = {"actions": {}}
        new, status = simulate_response(case, approval, self.policy, state, self.scenario["as_of"])
        self.assertEqual(status, "simulated")
        self.assertEqual(state, {"actions": {}})
        self.assertEqual(len(new["actions"]), 1)
        again, status = simulate_response(case, approval, self.policy, new, self.scenario["as_of"])
        self.assertEqual(status, "already simulated")
        self.assertEqual(new, again)

    def test_response_guardrails(self):
        case = run(self.scenario, self.policy)["alerts"][0]
        good = {"case_fingerprint": case["fingerprint"], "action": "revoke_session",
                "reviewer": "synthetic-reviewer", "issued_at": "2026-10-01T10:20:00Z",
                "expires_at": "2026-10-01T11:00:00Z"}
        for patch, expected in [({"case_fingerprint": "wrong"}, "approval binding"),
                                ({"reviewer": ""}, "approval binding"),
                                ({"action": "disable_account"}, "approval binding"),
                                ({"expires_at": self.scenario["as_of"]}, "expired"),
                                ({"issued_at": "2026-10-01T10:31:00Z"}, "future"),
                                ({"expires_at": "invalid"}, "invalid approval time")]:
            with self.subTest(patch=patch):
                state, status = simulate_response(case, {**good, **patch}, self.policy,
                                                  {"actions": {}}, self.scenario["as_of"])
                self.assertIn(expected, status)
                self.assertEqual(state, {"actions": {}})
        self.policy["kill_switch"] = True
        self.assertIn("kill switch", simulate_response(case, good, self.policy, {}, self.scenario["as_of"])[1])
        self.policy["kill_switch"] = False
        case["identity_context"]["protected"] = True
        self.assertIn("protected identity", simulate_response(case, good, self.policy, {}, self.scenario["as_of"])[1])


if __name__ == "__main__":
    unittest.main()
