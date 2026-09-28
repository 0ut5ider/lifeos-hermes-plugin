# ABOUTME: Compares LifeOS hook registrations with the tracked parity inventory.
# ABOUTME: Refuses missing, changed, or stale rows before a source update is accepted.

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/parity/public-hooks.json"
DEFAULT_ROWS = ROOT / "docs/parity/registrations.csv"
FIELDS = ("event", "matcher", "type", "handler", "async", "timeout")


def registrations(manifest: dict) -> dict[str, dict[str, str]]:
    rows = {}
    for event, groups in manifest["hooks"].items():
        for group_index, group in enumerate(groups, 1):
            for hook_index, hook in enumerate(group["hooks"], 1):
                identifier = f"{event}.{group_index}.{hook_index}"
                hook_type = hook["type"]
                rows[identifier] = {
                    "event": event,
                    "matcher": group.get("matcher", ""),
                    "type": hook_type,
                    "handler": hook.get("command", "") if hook_type == "command" else hook.get("url", ""),
                    "async": str(bool(hook.get("async", False))),
                    "timeout": str(hook.get("timeout", "default")),
                }
    return rows


def check_inventory(manifest_path: Path, rows_path: Path) -> list[str]:
    actual = registrations(json.loads(manifest_path.read_text()))
    tracked = {}
    errors = []
    with rows_path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            identifier = row["id"]
            if identifier in tracked:
                errors.append(f"duplicate inventory row {identifier}")
            tracked[identifier] = row
            if not row.get("status") or not row.get("evidence"):
                errors.append(f"missing status or evidence for {identifier}")
    for identifier, registration in actual.items():
        row = tracked.get(identifier)
        if row is None:
            errors.append(f"untracked registration {identifier}: {registration['handler']}")
            continue
        for field in FIELDS:
            if row[field] != registration[field]:
                errors.append(
                    f"changed registration {identifier} {field}: "
                    f"tracked {row[field]!r}, installed {registration[field]!r}"
                )
    for identifier in tracked.keys() - actual.keys():
        errors.append(f"stale inventory row {identifier}: {tracked[identifier]['handler']}")
    return sorted(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the LifeOS hook parity inventory")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--rows", type=Path, default=DEFAULT_ROWS)
    args = parser.parse_args()
    errors = check_inventory(args.manifest, args.rows)
    for error in errors:
        print(error)
    if errors:
        return 1
    print(f"Tracked {len(registrations(json.loads(args.manifest.read_text())))} LifeOS hook registrations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
