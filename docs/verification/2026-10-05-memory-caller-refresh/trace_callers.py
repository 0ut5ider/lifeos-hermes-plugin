# ABOUTME: Records native memory candidates and resolved source callers from a pinned install.
# ABOUTME: Separates entry-point evidence from behavioral policy verification.
import argparse
import hashlib
import json
from pathlib import Path
import re


def capture(root, output):
    excluded = {'node_modules', '.next', 'dist', 'out', 'test', 'tests', '.git', 'USER', 'MEMORY'}
    texts = {}
    for path in sorted(root.rglob('*')):
        if (path.is_symlink() or not path.is_file() or excluded.intersection(path.relative_to(root).parts)
                or path.name.startswith('test_') or path.suffix not in {'.ts', '.tsx', '.js', '.py', '.sh', '.md', '.toml', '.json', '.conf'}):
            continue
        texts[path.relative_to(root).as_posix()] = path.read_text()
    settings = {'hooks': {}}
    for filename in ('settings.system.json', 'settings.enhancements.json', 'hooks/hooks.json'):
        for event, groups in json.loads((root / filename).read_text()).get('hooks', {}).items():
            settings['hooks'].setdefault(event, []).extend(groups)
    registrations = {}
    for event, groups in settings.get('hooks', {}).items():
        for group in groups:
            for hook in group.get('hooks', []):
                for target in re.findall(r'hooks/[\w./-]+\.(?:ts|sh|py)', hook.get('command', '')):
                    registrations.setdefault(target, []).append({'event': event, 'matcher': group.get('matcher', ''), 'command': hook['command']})
    edges = {}
    for caller, text in texts.items():
        if Path(caller).suffix not in {'.ts', '.tsx', '.js', '.py', '.sh'}:
            continue
        for match in re.finditer(r'(?:from\s+|import\s*\(\s*|import\s+|require\s*\(\s*)[\'\"]([.@][^\'\"]+)[\'\"]', text):
            base = (root / 'LIFEOS/PULSE/Observability/src' / match[1][2:] if match[1].startswith('@/')
                    else root / Path(caller).parent / match[1])
            candidates = [base, *[Path(str(base) + suffix) for suffix in ('.ts', '.tsx', '.js')], base / 'index.ts']
            target = next((path.resolve().relative_to(root.resolve()).as_posix() for path in candidates
                           if path.is_file() and path.resolve().is_relative_to(root.resolve())), None)
            if target in texts:
                edges.setdefault(target, []).append({'path': caller, 'line': text[:match.start()].count('\n') + 1, 'kind': 'import', 'text': match[0]})
    roots = set(registrations) | {'LIFEOS/HERMES/Mount.ts', 'LIFEOS/PULSE/Observability/observability.ts', 'LIFEOS/PULSE/pulse.ts', 'LIFEOS/PULSE/run-job.ts'}
    roots |= set(json.loads((output / 'manual-entrypoints.json').read_text())['roots'])
    roots |= {path for path, text in texts.items() if re.search(r'^(?:await )?(?:main|cli|runCLI)\(', text, re.MULTILINE)
              or path.endswith('.sh') or '/Observability/src/app/' in path and Path(path).name in {'page.tsx', 'layout.tsx', 'route.ts'}}
    roots |= {path for path, text in texts.items() if re.search(r'import\.meta\.main|if __name__', text) and not path.endswith('.md')}
    # Module names are explicit in the PULSE manifest and resolved against modules/.
    manifest = texts.get('LIFEOS/PULSE/PULSE.toml', '')
    for path, text in texts.items():
        if path.endswith('.toml'):
            for target in texts:
                if target.endswith(('.ts', '.sh', '.py')) and target.removeprefix('LIFEOS/PULSE/') in text:
                    roots.add(target)
                    edges.setdefault(target, []).append({'path': path, 'line': 1, 'kind': 'command_manifest', 'text': target})
    for match in re.finditer(r'\bmodule\s*=\s*[\'\"]([^\'\"]+)', manifest):
        target = 'LIFEOS/PULSE/modules/' + match[1].removesuffix('.ts') + '.ts'
        if target in texts:
            roots.add(target)
            edges.setdefault(target, []).append({'path': 'LIFEOS/PULSE/PULSE.toml', 'line': manifest[:match.start()].count('\n') + 1, 'kind': 'manifest', 'text': match[0]})
    reachable = set(roots)
    while True:
        added = {target for target, callers in edges.items() if any(item['path'] in reachable for item in callers)} - reachable
        if not added:
            break
        reachable |= added
    previous = json.loads((output / 'source-traces.json').read_text())
    known = {row['path'] for row in previous}
    for path, text in texts.items():
        if path not in known and not path.endswith(('.md', '.conf')) and re.search(
                r'MEMORY|PRINCIPAL_MEMORY|DA_MEMORY|readMemory|MemoryAccess|RenderSoul|RenderHermesSoul', text):
            previous.append({'path': path, 'sha256': hashlib.sha256(text.encode()).hexdigest(),
                'registered_hooks': registrations.get(path, []), 'cli_guard': bool(re.search(r'import\.meta\.main|if __name__', text)),
                'source_evidence': [{'line': number, 'text': line} for number, line in enumerate(text.splitlines(), 1)
                                    if re.search(r'USER|MEMORY|read|write|append|unlink|rename|spawn|export|main', line)]})
    rows = []
    for row in sorted(previous, key=lambda row: row['path']):
        path = row['path']
        callers = edges.get(path, [])
        row = {key: value for key, value in row.items() if key != 'callers'}
        row.update(resolved_callers=callers, entry_point=('configuration_or_documentation_data' if path.endswith(('.json', '.toml')) else
                   'exported_utility_without_active_caller' if path in {'LIFEOS/PULSE/edit/edit-handler.ts', 'LIFEOS/PULSE/lib/provenance-watcher.ts'} and path not in reachable and not callers else 'registered_hook' if path in registrations else
                   'declared_entry' if path in roots else 'imported_from_entry' if path in reachable else 'unresolved_dynamic_or_manual'),
                   behavioral_status='requires_source_policy_or_existing_test_evidence',
                   source_policy=('contains_governed_api_reference' if 'MemoryAccess' in texts.get(path, '') or 'readMemory' in texts.get(path, '') else 'requires_boundary_review'),
                   source_sha256=hashlib.sha256(texts.get(path, '').encode()).hexdigest())
        rows.append(row)
    output.joinpath('caller-inventory.json').write_text(json.dumps(rows, indent=2) + '\n')
    counts = {kind: sum(row['entry_point'] == kind for row in rows) for kind in sorted({row['entry_point'] for row in rows})}
    print(json.dumps({'files_scanned': len(texts), 'candidates': len(rows), 'entry_points': counts}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    capture(args.root.absolute(), args.output)
