# ABOUTME: Summarizes private Claude Code and Hermes hook traces without exposing hook payloads.
# ABOUTME: Keeps every registered hook visible until a matched live event executes it.

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def _rows(path: Path, session_id: str) -> dict[str, list[dict]]:
    found: dict[str, list[dict]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("session_id") == session_id:
            found[row["id"]].append(row)
    return found


def _outcome(row: dict) -> dict:
    return {
        "exit_code": row["exit_code"],
        "stdout_present": row["stdout_size"] > 0,
        "stderr_present": row["stderr_size"] > 0,
        "tool_name": row.get("tool_name"),
    }


def build_coverage(registrations: Path, pairs: list[tuple]) -> dict:
    manifest = registrations.read_bytes()
    items = list(csv.DictReader(manifest.decode("utf-8").splitlines()))
    identifiers = [row["id"] for row in items]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Registration IDs are not unique")
    evidence: dict[str, list[dict]] = {identifier: [] for identifier in identifiers}
    scenarios = []
    for pair in pairs:
        label, native_path, native_session, hermes_path, hermes_session = pair[:5]
        event_filter = pair[5] if len(pair) == 6 else None
        native = _rows(native_path, native_session)
        hermes = _rows(hermes_path, hermes_session)
        unknown = (native.keys() | hermes.keys()) - evidence.keys()
        if unknown:
            raise ValueError(f"Trace contains unregistered hooks: {sorted(unknown)}")
        scenarios.append({"label": label, "native_session": native_session,
                          "hermes_session": hermes_session,
                          "event_filter": event_filter,
                          "native_trace_sha256": hashlib.sha256(native_path.read_bytes()).hexdigest(),
                          "hermes_trace_sha256": hashlib.sha256(hermes_path.read_bytes()).hexdigest()})
        for identifier in identifiers:
            if event_filter and identifier.split(".", 1)[0] != event_filter:
                continue
            native_rows = native.get(identifier, ())
            hermes_rows = hermes.get(identifier, ())
            left = [_outcome(row) for row in native_rows]
            right = [_outcome(row) for row in hermes_rows]
            if not left and not right:
                continue
            same_final_text = (identifier.startswith("Stop.") and left and right and
                               [row.get("last_assistant_message") for row in native_rows] !=
                               [row.get("last_assistant_message") for row in hermes_rows])
            evidence[identifier].append({"scenario": label, "native": left, "hermes": right,
                                         "transport_match": None if same_final_text else left == right,
                                         "incomparable_reason": "different_final_text" if same_final_text else None})
    results = []
    for row in items:
        matches = evidence[row["id"]]
        status = ("not_observed" if not matches else
                  "mismatch" if any(case["transport_match"] is False for case in matches) else
                  "matched_dispatch_and_output_shape" if any(case["transport_match"] is True for case in matches)
                  else "observed_with_different_input")
        results.append({"id": row["id"], "event": row["event"], "handler": row["handler"],
                        "status": status, "cases": matches})
    return {"scope": "registration dispatch, exit code, and output presence only; handler side effects require separate evidence",
            "registrations_sha256": hashlib.sha256(manifest).hexdigest(),
            "scenarios": scenarios, "registrations": results,
            "counts": {status: sum(row["status"] == status for row in results) for status in
                       ("matched_dispatch_and_output_shape", "mismatch", "observed_with_different_input",
                        "not_observed")}}


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize paired live hook traces")
    parser.add_argument("registrations", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pair", action="append", nargs=5, default=[],
                        metavar=("LABEL", "NATIVE_TRACE", "NATIVE_SESSION", "HERMES_TRACE", "HERMES_SESSION"),
                        help="Compare every event in a matched session")
    parser.add_argument("--pair-event", action="append", nargs=6, default=[],
                        metavar=("EVENT", "LABEL", "NATIVE_TRACE", "NATIVE_SESSION", "HERMES_TRACE", "HERMES_SESSION"),
                        help="Compare only one event when another event had different inputs")
    args = parser.parse_args()
    if not args.pair and not args.pair_event:
        parser.error("At least one --pair or --pair-event is required")
    pairs = [(label, Path(native), native_session, Path(hermes), hermes_session)
             for label, native, native_session, hermes, hermes_session in args.pair]
    pairs.extend((label, Path(native), native_session, Path(hermes), hermes_session, event)
                 for event, label, native, native_session, hermes, hermes_session in args.pair_event)
    report = build_coverage(args.registrations, pairs)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"]))


if __name__ == "__main__":
    main()
