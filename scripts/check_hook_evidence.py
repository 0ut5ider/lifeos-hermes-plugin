# ABOUTME: Checks complete registration coverage and the integrity of paired effect evidence.
# ABOUTME: Refuses a completion claim supported only by dispatch or partial handler cases.
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {'unverified', 'native_handler_checked', 'paired_case_verified', 'paired_effect_verified'}


def check_evidence(inventory: Path, ledger: Path, root: Path, require_complete: bool = False) -> list[str]:
    root = root.resolve()
    identifiers = {row['id'] for row in csv.DictReader(inventory.read_text().splitlines())}
    document = json.loads(ledger.read_text())
    errors = []
    if document.get('registrations_sha256') != hashlib.sha256(inventory.read_bytes()).hexdigest():
        errors.append('registration inventory changed')
    artifacts = document.get('artifacts', {})
    for name, expected_hash in artifacts.items():
        target = (root / name).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            errors.append(f'missing or external artifact: {name}')
        elif hashlib.sha256(target.read_bytes()).hexdigest() != expected_hash:
            errors.append(f'changed artifact: {name}')
    rows = {}
    for row in document['registrations']:
        identifier = row['id']
        if identifier in rows:
            errors.append(f'duplicate evidence: {identifier}')
        rows[identifier] = row
        if not row.get('expected_effect'):
            errors.append(f'expected effect is missing: {identifier}')
        status = row.get('effect_status')
        if status not in STATUSES:
            errors.append(f'unknown effect status: {identifier}')
        cases = row.get('paired_cases', [])
        if status in {'paired_case_verified', 'paired_effect_verified'} and not cases:
            errors.append(f'paired case is missing: {identifier}')
        for case in cases:
            label = f'{identifier}/{case["id"]}'
            if 'native' not in case or 'hermes' not in case or case['native'] != case['hermes']:
                errors.append(f'unequal paired case: {label}')
            names = case.get('artifacts', [])
            if not names or any(name not in artifacts for name in names):
                errors.append(f'paired case lacks a retained artifact: {label}')
        if document.get('complete') and status != 'paired_effect_verified':
            errors.append(f'complete claim includes partial effects: {identifier}')
    for identifier in identifiers - rows.keys():
        errors.append(f'missing evidence: {identifier}')
    for identifier in rows.keys() - identifiers:
        errors.append(f'unregistered evidence: {identifier}')
    if require_complete:
        pending = sorted(identifier for identifier, row in rows.items()
                         if row.get('effect_status') != 'paired_effect_verified')
        if pending:
            errors.append('unverified effects: ' + ', '.join(pending))
    return sorted(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description='Check LifeOS hook effect evidence')
    parser.add_argument('--inventory', type=Path, default=ROOT / 'docs/parity/registrations.csv')
    parser.add_argument('--ledger', type=Path, default=ROOT / 'docs/parity/handler-effects.json')
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    errors = check_evidence(args.inventory, args.ledger, ROOT, args.require_complete)
    for error in errors:
        print(error)
    if errors:
        return 1
    print('Hook effect evidence has complete inventory and unchanged artifacts.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
