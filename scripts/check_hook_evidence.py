# ABOUTME: Checks complete registration coverage and the integrity of paired effect evidence.
# ABOUTME: Refuses a completion claim supported only by dispatch or partial handler cases.
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

if __package__:
    from .paired_lifecycle_effects import FILE_CASES, TOOL_REPEATS, check_pair
else:
    from paired_lifecycle_effects import FILE_CASES, TOOL_REPEATS, check_pair

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {'unverified', 'native_handler_checked', 'paired_case_verified', 'paired_effect_verified'}


MODEL_CHOSEN_COUNTS = ('model_generation_requests', 'model_successful_responses', 'hook_exit_codes')


def comparable(case_id: str, outcome: dict) -> dict:
    # The model chooses how many tool calls it makes in these cases. check_pair validates each side;
    # the equality rule then compares every other recorded field.
    if case_id in TOOL_REPEATS or case_id in FILE_CASES:
        return {key: value for key, value in outcome.items() if key not in MODEL_CHOSEN_COUNTS}
    return outcome


def check_lifecycle_case(identifier: str, case: dict, artifacts: dict, root: Path) -> list[str]:
    label = f'{identifier}/{case["id"]}'
    name = case.get('result_artifact')
    if name not in artifacts or name not in case.get('artifacts', []):
        return [f'lifecycle result is not retained: {label}']
    target = (root / name).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        return [f'lifecycle result is missing: {label}']
    records = json.loads(target.read_text()).get('cases', [])
    matches = [record for record in records if record.get('id') == case['id']]
    if len(matches) != 1:
        return [f'lifecycle case is missing or duplicated: {label}']
    record = matches[0]
    errors = [f'invalid lifecycle case: {label}: {error}' for error in check_pair(record)]
    if identifier not in record.get('registrations', []):
        errors.append(f'lifecycle case does not cover registration: {label}')
    for side in ('native', 'hermes'):
        outcome = {key: value for key, value in record[side].items() if key != 'metadata_requests'}
        if case.get(side) != outcome:
            errors.append(f'ledger outcome differs from lifecycle result: {label}/{side}')
    return errors


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
            if ('native' not in case or 'hermes' not in case
                    or comparable(case['id'], case['native']) != comparable(case['id'], case['hermes'])):
                errors.append(f'unequal paired case: {label}')
            names = case.get('artifacts', [])
            if not names or any(name not in artifacts for name in names):
                errors.append(f'paired case lacks a retained artifact: {label}')
            if case.get('kind') == 'paired_lifecycle':
                errors.extend(check_lifecycle_case(identifier, case, artifacts, root))
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
