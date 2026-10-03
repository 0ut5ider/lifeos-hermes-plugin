# ABOUTME: Rebuilds searchable development indexes from immutable capture files.
# ABOUTME: Reports failures, pending work, hook coverage, and artifact integrity.

import argparse
from contextlib import closing
import gzip
import hashlib
import json
import sqlite3
import zlib
from pathlib import Path


def rebuild(root: Path):
    root = Path(root)
    destination = root / "analysis/index.sqlite"
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.touch(mode=0o600, exist_ok=True)
    with closing(sqlite3.connect(destination)) as db, db:
        db.executescript("""
          DROP TABLE IF EXISTS events; DROP TABLE IF EXISTS issues; DROP TABLE IF EXISTS registrations;
          CREATE TABLE registrations(registration_id TEXT PRIMARY KEY,native_event TEXT,hook_kind TEXT,matcher TEXT,settings_origin TEXT);
          CREATE TABLE events(event_id TEXT PRIMARY KEY, run_id TEXT, process_id TEXT, sequence INTEGER,
            time_utc TEXT, stage TEXT, session_id TEXT, callback_id TEXT, dispatch_id TEXT,
            invocation_id TEXT, registration_id TEXT, native_event TEXT, hermes_event TEXT,
            status TEXT, decision TEXT, duration_ns INTEGER, exit_code INTEGER, span_id TEXT, parent_span_id TEXT, data_path TEXT, record TEXT);
          CREATE TABLE issues(kind TEXT, path TEXT, detail TEXT);
          CREATE INDEX by_registration ON events(registration_id,stage,status);
          CREATE INDEX by_session ON events(session_id,time_utc);
          CREATE INDEX by_invocation ON events(invocation_id,stage);
          CREATE INDEX by_stage ON events(stage,time_utc);
          CREATE INDEX by_span ON events(span_id,parent_span_id);
        """)
        columns = [row[1] for row in db.execute("PRAGMA table_info(events)")]
        checked = set()
        invalid_references = set()
        for path in sorted(root.glob("runs/*/events/*/*.jsonl")):
            with path.open("rb") as stream:
                for line_number, line in enumerate(stream, 1):
                    try:
                        if not line.endswith(b"\n"):
                            db.execute("INSERT INTO issues VALUES(?,?,?)", ("partial_tail", str(path.relative_to(root)), str(line_number)))
                            continue
                        row = json.loads(line)
                        if not isinstance(row, dict):
                            raise ValueError("Event must be an object")
                        if row.get("schema_version") != 1:
                            raise ValueError("Unsupported event schema")
                        if any(not isinstance(row.get(key), str) or not row[key]
                               for key in ("event_id", "run_id", "process_id", "time_utc", "stage")):
                            raise ValueError("Missing event identity")
                        if not isinstance(row.get("sequence"), int) or isinstance(row["sequence"], bool) or row["sequence"] < 1:
                            raise ValueError("Invalid event sequence")
                        text_fields = ("event_id", "run_id", "process_id", "time_utc", "stage", "session_id", "callback_id",
                                       "dispatch_id", "invocation_id", "registration_id", "native_event", "hermes_event",
                                       "status", "decision", "span_id", "parent_span_id")
                        if any(row.get(key) is not None and not isinstance(row[key], str) for key in text_fields):
                            raise ValueError("Invalid event text field")
                        if any(row.get(key) is not None and (not isinstance(row[key], int) or isinstance(row[key], bool)
                               or not -(2**63) <= row[key] < 2**63)
                               for key in ("sequence", "duration_ns", "exit_code")):
                            raise ValueError("Invalid event numeric field")
                        ref = row.get("data_ref")
                        if ref is None:
                            ref = {}
                        if not isinstance(ref, dict):
                            raise ValueError("Artifact reference must be an object")
                        relative = ref.get("path")
                        if relative is not None and (not isinstance(relative, str) or not isinstance(ref.get("sha256"), str)):
                            raise ValueError("Invalid artifact reference")
                        reference_id = (relative, ref.get("sha256"))
                        if relative and reference_id not in checked:
                            artifact = (root / relative).resolve()
                            if not artifact.is_relative_to(root.resolve()):
                                raise ValueError("Artifact path escapes capture root")
                            try:
                                raw = gzip.decompress(artifact.read_bytes())
                                if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
                                    raise ValueError("Artifact digest mismatch")
                            except (OSError, ValueError, EOFError, zlib.error) as error:
                                db.execute("INSERT INTO issues VALUES(?,?,?)", ("artifact_error", relative, type(error).__name__))
                                invalid_references.add(reference_id)
                            checked.add(reference_id)
                        if row.get("stage") == "inventory.observed" and relative and reference_id not in invalid_references:
                            try:
                                inventory = json.loads(gzip.decompress((root / relative).read_bytes()))
                                if not isinstance(inventory, dict) or not isinstance(inventory.get("registrations"), list):
                                    raise ValueError("Invalid inventory object")
                                keys = ("registration_id", "native_event", "hook_kind", "matcher", "settings_origin")
                                registrations = []
                                for item in inventory["registrations"]:
                                    if not isinstance(item, dict) or not isinstance(item.get("registration_id"), str) or not item["registration_id"]:
                                        raise ValueError("Invalid registration identity")
                                    if any(item.get(key) is not None and not isinstance(item[key], str) for key in keys):
                                        raise ValueError("Invalid registration field")
                                    registrations.append(tuple(item.get(key) for key in keys))
                                db.executemany("INSERT OR IGNORE INTO registrations VALUES(?,?,?,?,?)", registrations)
                            except (OSError, ValueError, TypeError, AttributeError, EOFError, zlib.error):
                                db.execute("INSERT INTO issues VALUES(?,?,?)", ("invalid_inventory", relative, "Invalid inventory data"))
                        values = [json.dumps(row, separators=(",", ":")) if key == "record" else
                                  relative if key == "data_path" else row.get(key) for key in columns]
                        db.execute(f"INSERT OR IGNORE INTO events VALUES({','.join('?' for _ in columns)})", values)
                    except (ValueError, KeyError, TypeError) as error:
                        db.execute("INSERT INTO issues VALUES(?,?,?)", ("invalid_event", str(path.relative_to(root)), f"line {line_number}: {type(error).__name__}"))
    return destination


def summary(index):
    with closing(sqlite3.connect(index)) as db:
        total = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        statuses = dict(db.execute("SELECT status,COUNT(*) FROM events WHERE status IS NOT NULL GROUP BY status"))
        incomplete = db.execute("""SELECT COUNT(DISTINCT a.invocation_id) FROM events a
            WHERE a.stage IN ('hook.started','async.handoff') AND NOT EXISTS(SELECT 1 FROM events b WHERE
            b.run_id=a.run_id AND b.invocation_id=a.invocation_id AND b.stage IN ('hook.completed','hook.failed'))""").fetchone()[0]
        issues = dict(db.execute("SELECT kind,COUNT(*) FROM issues GROUP BY kind"))
        losses = list(db.execute("""SELECT run_id,process_id,MAX(CAST(json_extract(record,'$.prior_capture_failures') AS INTEGER))
                FROM events WHERE CAST(json_extract(record,'$.prior_capture_failures') AS INTEGER)>0
                GROUP BY run_id,process_id"""))
        gaps = db.execute("SELECT COUNT(*) FROM events WHERE status='capture_gap'").fetchone()[0]
        hooks = []
        for registration, count, maximum, mean, successes, interventions, failures in db.execute("""SELECT registration_id,COUNT(*),MAX(duration_ns),AVG(duration_ns),
                SUM(status='completed' AND exit_code=0), SUM(status='intervention' OR exit_code=2),
                SUM(stage='hook.failed' OR status IN ('no_result','exit_failure','timeout','exception'))
                FROM events WHERE stage IN ('hook.completed','hook.failed') GROUP BY registration_id ORDER BY MAX(duration_ns) DESC"""):
            durations = sorted(r[0] for r in db.execute("SELECT duration_ns FROM events WHERE registration_id IS ? AND duration_ns IS NOT NULL AND stage IN ('hook.completed','hook.failed')", (registration,)))
            hooks.append({"registration_id": registration, "terminal_outcomes": count,
                          "successful_executions": successes or 0, "interventions": interventions or 0,
                          "failures": failures or 0, "max_ms": (maximum or 0)/1e6,
                          "p50_ms": durations[len(durations)//2]/1e6 if durations else None,
                          "p95_ms": durations[min(len(durations)-1,int(len(durations)*.95))]/1e6 if durations else None})
        unexercised = [dict(zip(("registration_id", "native_event", "hook_kind", "matcher", "settings_origin"), row))
            for row in db.execute("""SELECT * FROM registrations r WHERE NOT EXISTS
                (SELECT 1 FROM events e WHERE e.registration_id=r.registration_id AND e.stage IN ('hook.started','hook.completed','hook.failed'))""")]
        return {"events": total, "statuses": statuses, "incomplete_invocations": incomplete,
                "known_lost_events": sum(row[2] for row in losses), "capture_failure_processes": len(losses),
                "capture_gaps": gaps,
                "known_registrations": db.execute("SELECT COUNT(*) FROM registrations").fetchone()[0],
                "unexercised_registrations": unexercised,
                "partial_tails": issues.get("partial_tail", 0), "integrity_issues": issues,
                "hooks": hooks, "note": "Completion is execution evidence, not semantic parity."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--session")
    parser.add_argument("--stage")
    parser.add_argument("--status")
    parser.add_argument("--registration")
    parser.add_argument("--invocation")
    parser.add_argument("--from-utc")
    parser.add_argument("--to-utc")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--artifact", help="Artifact relative path to expand")
    args = parser.parse_args()
    if args.artifact:
        path = (args.root / args.artifact).resolve()
        if not path.is_relative_to(args.root.resolve()):
            parser.error("Artifact must be inside capture root")
        print(gzip.decompress(path.read_bytes()).decode())
        return
    index = rebuild(args.root)
    if not any((args.session, args.stage, args.status, args.registration, args.invocation, args.from_utc, args.to_utc)):
        print(json.dumps(summary(index), indent=2))
        return
    filters, values = [], []
    for key, value in (("session_id", args.session), ("stage", args.stage), ("status", args.status),
                       ("registration_id", args.registration), ("invocation_id", args.invocation)):
        if value:
            filters.append(key + "=?")
            values.append(value)
    for operator, value in ((">=", args.from_utc), ("<=", args.to_utc)):
        if value:
            filters.append("time_utc" + operator + "?")
            values.append(value)
    with closing(sqlite3.connect(index)) as db:
        for (row,) in db.execute("SELECT record FROM events WHERE " + " AND ".join(filters) + " ORDER BY time_utc,process_id,sequence LIMIT ?", (*values, max(1,min(args.limit,10000)))):
            print(row)


if __name__ == "__main__":
    main()
