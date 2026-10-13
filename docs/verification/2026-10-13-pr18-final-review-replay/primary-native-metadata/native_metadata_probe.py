# ABOUTME: Measures native Hermes metadata generation with a permissive caller and the release stage boundary.
# ABOUTME: Uses only temporary public-source metadata and records modes, child behavior, and caller umask preservation.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from optional.lifeos_release_manager.release_stage import run_stage

NATIVE = Path('/home/outsider/.cache/lifeos-hermes-managed-20261012/upstream')
OUT = Path(__file__).resolve().parent


def modes(root):
    return {str(path.relative_to(root)): oct(path.stat().st_mode & 0o777)
        for path in sorted(root.rglob('*'))}


with tempfile.TemporaryDirectory(prefix='pr18-native-metadata-') as folder:
    job = Path(folder)
    code = ('from pathlib import Path\nimport sys\n'
        'sys.path.insert(0,sys.argv[1])\nfrom scripts.build.agent import write_metadata\n'
        'repo=Path(sys.argv[2]);repo.mkdir()\nwrite_metadata(Path(sys.argv[1])/"pyproject.toml",repo)\n')
    previous = os.umask(0o002)
    try:
        control = job / 'control'
        result = subprocess.run([sys.executable, '-B', '-c', code, str(NATIVE), str(control)],
            env=dict(os.environ), capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stdout == '' and result.stderr == ''
        protected = job / 'protected'
        run_stage([sys.executable, '-B', '-c', code, str(NATIVE), str(protected)],
            job, 'native-metadata', environment=dict(os.environ))
        caller = os.umask(0o002)
        assert caller == 0o002
        control_modes, protected_modes = modes(control), modes(protected)
        assert any(value == '0o775' for value in control_modes.values())
        assert any(value == '0o664' for value in control_modes.values())
        assert all(value in {'0o700', '0o600'} for value in protected_modes.values())
        assert (job / 'native-metadata.stdout').read_bytes() == b''
        assert (job / 'native-metadata.stderr').read_bytes() == b''
        report = {'caller_umask_after_stage': oct(caller), 'unprotected_native_metadata_modes': control_modes,
            'protected_native_metadata_modes': protected_modes,
            'stage_stdout_mode': oct((job/'native-metadata.stdout').stat().st_mode & 0o777),
            'stage_stderr_mode': oct((job/'native-metadata.stderr').stat().st_mode & 0o777),
            'qualified_python': sys.version, 'subprocess_source': subprocess.__file__,
            'scope': 'Real native public-source metadata writer and real stage subprocess; no complete release or guest installation.'}
    finally:
        os.umask(previous)
(OUT / 'native-metadata-probe.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
