# ABOUTME: Records actual IntegrityCheck consumption of native skill hygiene verdicts.
# ABOUTME: Uses isolated synthetic code and security controls for clean, dirty, and unbound calls.
import json
from test_memory_skill_hygiene import MemorySkillHygieneTests
case = MemorySkillHygieneTests()
case.setUp()
try:
    case.seed()
    rows = []
    for mode in ('clean', 'dirty', 'unbound'):
        if mode != 'clean': case.code.write_text('SyntheticDenyToken0\n')
        result = case.call('IntegrityCheck.ts', '--json', context=mode != 'unbound')
        try: body = json.loads(result.stdout)
        except ValueError: body = None
        rows.append({'mode': mode, 'exit_code': result.returncode, 'stdout': result.stdout,
            'stderr': result.stderr, 'body': body})
    clean, dirty, unbound = [row['body'] for row in rows]
    checks = lambda body: [row for row in body['checks'] if row['name'] == 'skill-hygiene']
    assert checks(clean)[0]['ok'] and checks(clean)[0]['blocking'] == 0
    assert not checks(dirty)[0]['ok'] and checks(dirty)[0]['blocking'] == 1
    assert checks(unbound) == []
    assert 'skill-hygiene: The skill scan requires current owner memory access' in unbound['scanErrors']
    for row in rows:
        assert all(line.startswith(('CarrierProbe:', 'find:', 'fatal: not a git repository',
            'Stopping at filesystem boundary')) for line in row['stderr'].splitlines()), row['stderr']
    print(json.dumps(rows, indent=2))
finally: case.doCleanups()
