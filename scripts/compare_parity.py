# ABOUTME: Compares recorded Claude Code and Hermes outcomes for the same action.
# ABOUTME: Checks final tool input and side effects while normalizing only declared path roots.

from __future__ import annotations

import argparse
import json
from pathlib import Path


MISSING = object()


def select(data: object, path: str) -> object:
    current = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return MISSING
        current = current[key]
    return current


def normalize(value: object, kind: str) -> object:
    if kind == "identity":
        return value
    if kind == "basename" and isinstance(value, str):
        return Path(value).name
    raise ValueError(f"unsupported normalizer or value: {kind}")


def compare_manifest(path: Path) -> list[str]:
    document = json.loads(path.read_text())
    if document.get("version") != 1 or not isinstance(document.get("cases"), list):
        raise ValueError("comparison manifest needs version 1 and a cases list")
    issues = []
    seen = set()
    for case in document["cases"]:
        identifier = case["id"]
        if identifier in seen:
            issues.append(f"duplicate case: {identifier}")
            continue
        seen.add(identifier)
        native = json.loads((path.parent / case["native"]).read_text())
        hermes = json.loads((path.parent / case["hermes"]).read_text())
        for name, field in case["fields"].items():
            if "expected" not in field:
                issues.append(f"{identifier}.{name}: missing expected result")
                continue
            values = []
            for side, artifact in (("native", native), ("hermes", hermes)):
                value = select(artifact, field[side])
                if value is MISSING:
                    issues.append(f"{identifier}.{name}: missing {side} field {field[side]}")
                    continue
                values.append((side, normalize(value, field.get("normalize", "identity"))))
            if len(values) != 2:
                continue
            if values[0][1] != values[1][1]:
                issues.append(f"{identifier}.{name}: native {values[0][1]!r} differs from Hermes {values[1][1]!r}")
            if values[0][1] != field["expected"]:
                issues.append(f"{identifier}.{name}: native {values[0][1]!r} differs from expected {field['expected']!r}")
            if values[1][1] != field["expected"]:
                issues.append(f"{identifier}.{name}: Hermes {values[1][1]!r} differs from expected {field['expected']!r}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare paired native and Hermes hook outcomes")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        issues = compare_manifest(args.manifest)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Parity comparison failed: {error}\n")
    for issue in issues:
        print(issue)
    if issues:
        return 1
    cases = json.loads(args.manifest.read_text())["cases"]
    print(f"Matched {len(cases)} paired outcome cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
