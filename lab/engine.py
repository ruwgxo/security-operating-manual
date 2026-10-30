"""Deterministic detection and response simulation; no network or cloud adapters."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from ipaddress import ip_address


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def instant(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO 8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp needs an explicit timezone")
    return parsed


def validate_config(config):
    for key in ("window_seconds", "minimum_bytes"):
        if type(config.get(key)) is not int or config[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    for key in ("rule_id", "version"):
        if not isinstance(config.get(key), str) or not config[key]:
            raise ValueError(f"{key} must be a nonempty string")
    if type(config.get("kill_switch")) is not bool:
        raise ValueError("kill_switch must be a boolean")


def normalize(events, identities, assets, as_of):
    """Quarantine malformed records; exact duplicates deduplicate; conflicts fail closed."""
    clean, rejected, seen, duplicate_count = [], [], {}, 0
    signatures, conflicts = {}, set()
    for raw in events:
        if isinstance(raw, dict) and isinstance(raw.get("event_id"), str):
            eid, signature = raw["event_id"], digest(raw)
            if eid in signatures and signatures[eid] != signature:
                conflicts.add(eid)
            signatures[eid] = signature
    for raw in events:
        try:
            if not isinstance(raw, dict):
                raise ValueError("event must be an object")
            eid = raw.get("event_id")
            for key in ("event_id", "identity_id", "session_id", "kind", "source", "source_ip"):
                if not isinstance(raw.get(key), str) or not raw[key]:
                    raise ValueError(f"missing or invalid {key}")
            if eid in conflicts:
                raise ValueError("conflicting duplicate event_id")
            if eid in seen:
                duplicate_count += 1
                continue
            occurred = instant(raw.get("occurred_at"))
            received = instant(raw.get("received_at"))
            if occurred > received or received > as_of:
                raise ValueError("event time must be <= received time <= as_of")
            if raw["identity_id"] not in identities:
                raise ValueError("unknown identity")
            ip_address(raw["source_ip"])
            if raw["kind"] == "authentication":
                if raw["source"] != "identity-provider":
                    raise ValueError("authentication requires identity-provider source")
                if type(raw.get("unusual_device")) is not bool:
                    raise ValueError("unusual_device must be a boolean")
                if raw.get("outcome") not in ("success", "failure"):
                    raise ValueError("invalid authentication outcome")
            elif raw["kind"] == "object_read":
                if raw["source"] != "object-store":
                    raise ValueError("object_read requires object-store source")
                if raw.get("asset_id") not in assets:
                    raise ValueError("unknown asset")
                if type(raw.get("bytes")) is not int or raw["bytes"] < 0:
                    raise ValueError("bytes must be a nonnegative integer")
                if raw.get("outcome") not in ("success", "failure"):
                    raise ValueError("invalid read outcome")
            else:
                raise ValueError("unsupported event kind")
            seen[eid] = raw
            clean.append(raw)
        except (ValueError, TypeError) as exc:
            rejected.append({"event_id": raw.get("event_id") if isinstance(raw, dict) else None,
                             "reason": str(exc)})
    return sorted(clean, key=lambda e: (instant(e["occurred_at"]), e["event_id"])), rejected, duplicate_count


def run(scenario, config):
    validate_config(config)
    as_of = instant(scenario["as_of"])
    identities, assets = scenario["identities"], scenario["assets"]
    events, rejected, duplicates = normalize(scenario["events"], identities, assets, as_of)
    intelligence, intel_errors = {}, []
    for item in scenario["intelligence"]:
        if not isinstance(item, dict):
            intel_errors.append({"indicator_id": None, "reason": "indicator must be an object"})
            continue
        try:
            ip_address(item["value"])
            if item["kind"] != "ip" or item["confidence"] not in ("low", "medium", "high"):
                raise ValueError("invalid indicator kind or confidence")
            start, end = instant(item["valid_from"]), instant(item["valid_until"])
            if start >= end:
                raise ValueError("indicator validity interval is empty")
            if item.get("tlp") != "TLP:CLEAR":
                raise ValueError("this public example accepts TLP:CLEAR only")
            if not item.get("source") or not item.get("id"):
                raise ValueError("indicator needs provenance and id")
            if item["confidence"] == "high" and start <= as_of < end:
                intelligence.setdefault(item["value"], []).append(item)
        except (ValueError, KeyError, TypeError) as exc:
            intel_errors.append({"indicator_id": item.get("id"), "reason": str(exc)})
    alerts = []
    for auth in events:
        if (auth["kind"] != "authentication" or auth["outcome"] != "success"
                or not auth["unusual_device"]):
            continue
        indicators = sorted([i for i in intelligence.get(auth["source_ip"], [])
                             if instant(i["valid_from"]) <= instant(auth["occurred_at"]) < instant(i["valid_until"])],
                            key=lambda i: i["id"])
        if not indicators:
            continue
        end = instant(auth["occurred_at"]) + timedelta(seconds=config["window_seconds"])
        reads = [e for e in events if e["kind"] == "object_read" and e["outcome"] == "success"
                 and e["identity_id"] == auth["identity_id"] and e["session_id"] == auth["session_id"]
                 and e["source_ip"] == auth["source_ip"]
                 and instant(auth["occurred_at"]) <= instant(e["occurred_at"]) <= end
                 and assets[e["asset_id"]]["classification"] == "restricted"]
        total = sum(e["bytes"] for e in reads)
        if total < config["minimum_bytes"]:
            continue
        evidence = [auth, *reads]
        payload = {"rule_id": config["rule_id"], "rule_version": config["version"],
                   "identity_id": auth["identity_id"], "session_id": auth["session_id"],
                   "events": evidence, "indicators": indicators, "as_of": scenario["as_of"],
                   "policy": config, "identity_context": identities[auth["identity_id"]],
                   "asset_context": {e["asset_id"]: assets[e["asset_id"]] for e in reads}}
        fingerprint = digest(payload)
        alerts.append({"case_id": "case-" + fingerprint[:16], "fingerprint": fingerprint,
                       "identity_id": auth["identity_id"], "session_id": auth["session_id"],
                       "severity": "high", "bytes_read": total, "rule_id": config["rule_id"],
                       "rule_version": config["version"], "evidence": evidence,
                       "indicators": indicators, "identity_context": payload["identity_context"],
                       "asset_context": payload["asset_context"],
                       "assessment": "Suspected session compromise; object reads do not prove external exfiltration.",
                       "next_steps": ["Validate device and session with identity owner.",
                                      "Inspect grants, object access and adjacent sessions.",
                                      "Preserve evidence before scoped containment."]})
    sources = {e["source"] for e in events}
    gaps = sorted({"identity-provider", "object-store"} - sources)
    return {"scenario_id": scenario["scenario_id"], "as_of": scenario["as_of"],
            "alerts": alerts, "quarantined_events": rejected, "intelligence_errors": intel_errors,
            "duplicate_events": duplicates, "missing_sources": gaps,
            "limitations": ["Batch evaluation only; source presence is not a health check.",
                            "No matching alert is not evidence of a clean environment.",
                            "All context, indicators and telemetry are synthetic."]}


def simulate_response(case, approval, config, state, now):
    """Return a new local state. An approval file is test input, not authentication."""
    validate_config(config)
    action = "revoke_session"
    key = digest({"fingerprint": case["fingerprint"], "action": action})
    if config["kill_switch"]:
        return state, "blocked: kill switch"
    if case["identity_context"].get("protected"):
        return state, "blocked: protected identity"
    if (approval.get("case_fingerprint") != case["fingerprint"] or approval.get("action") != action
            or not isinstance(approval.get("reviewer"), str) or not approval["reviewer"].strip()):
        return state, "blocked: approval binding"
    try:
        issued, expires = instant(approval["issued_at"]), instant(approval["expires_at"])
        if not issued <= instant(now) < expires:
            return state, "blocked: expired or future approval"
    except (ValueError, KeyError, TypeError):
        return state, "blocked: invalid approval time"
    if key in state.get("actions", {}):
        return state, "already simulated"
    result = json.loads(json.dumps(state))
    result.setdefault("actions", {})[key] = {
        "action": action, "case_fingerprint": case["fingerprint"],
        "identity_id": case["identity_id"], "session_id": case["session_id"],
        "reviewer": approval["reviewer"], "simulated_at": now,
        "result": "simulated_only", "recovery": "Issue a new verified session; revocation is not reversible."}
    return result, "simulated"
