# ABOUTME: Rebuilds searchable development indexes from immutable capture files.
# ABOUTME: Reports failures, pending work, hook coverage, and artifact integrity.

import argparse
from contextlib import closing
import gzip
import hashlib
import json
import sqlite3
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
        for path in sorted(root.glob("runs/*/events/*/*.jsonl")):
            with path.open("rb") as stream:
                for line_number, line in enumerate(stream, 1):
                    try:
                        if not line.endswith(b"\n"):
                            db.execute("INSERT INTO issues VALUES(?,?,?)", ("partial_tail", str(path.relative_to(root)), str(line_number)))
                            continue
                        row = json.loads(line)
                        if row.get("schema_version") != 1:
                            raise ValueError("Unsupported event schema")
                        ref = row.get("data_ref") or {}
                        relative = ref.get("path")
                        if relative and relative not in checked:
                            artifact = (root / relative).resolve()
                            if not artifact.is_relative_to(root.resolve()):
                                raise ValueError("Artifact path escapes capture root")
                            try:
                                raw = gzip.decompress(artifact.read_bytes())
                                if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
                                    raise ValueError("Artifact digest mismatch")
                            except (OSError, ValueError, EOFError) as error:
                                db.execute("INSERT INTO issues VALUES(?,?,?)", ("artifact_error", relative, type(error).__name__))
                            checked.add(relative)
                        if row.get("stage") == "inventory.observed" and relative:
                            try:
                                inventory = json.loads(gzip.decompress((root / relative).read_bytes()))
                                for item in inventory.get("registrations", []):
                                    db.execute("INSERT OR IGNORE INTO registrations VALUES(?,?,?,?,?)", tuple(item.get(key) for key in
                                        ("registration_id", "native_event", "hook_kind", "matcher", "settings_origin")))
                            except (OSError, ValueError, TypeError, EOFError):
                                pass  # The integrity check above reports damaged artifacts.
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
        hooks = []
        for registration, count, maximum, mean in db.execute("""SELECT registration_id,COUNT(*),MAX(duration_ns),AVG(duration_ns)
                FROM events WHERE stage IN ('hook.completed','hook.failed') GROUP BY registration_id ORDER BY MAX(duration_ns) DESC"""):
            durations = sorted(r[0] for r in db.execute("SELECT duration_ns FROM events WHERE registration_id IS ? AND duration_ns IS NOT NULL AND stage IN ('hook.completed','hook.failed')", (registration,)))
            hooks.append({"registration_id": registration, "completed": count, "max_ms": (maximum or 0)/1e6,
                          "p50_ms": durations[len(durations)//2]/1e6 if durations else None,
                          "p95_ms": durations[min(len(durations)-1,int(len(durations)*.95))]/1e6 if durations else None})
        unexercised = [dict(zip(("registration_id", "native_event", "hook_kind", "matcher", "settings_origin"), row))
            for row in db.execute("""SELECT * FROM registrations r WHERE NOT EXISTS
                (SELECT 1 FROM events e WHERE e.registration_id=r.registration_id AND e.stage IN ('hook.started','hook.completed','hook.failed'))""")]
        return {"events": total, "statuses": statuses, "incomplete_invocations": incomplete,
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
