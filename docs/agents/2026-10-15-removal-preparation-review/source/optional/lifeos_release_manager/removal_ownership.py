# ABOUTME: Proves exact guard and Pulse ownership from the installed integration journals.
# ABOUTME: Refuses changed owner software before complete removal selects any target.
import re
from pathlib import Path

from .cli import read_private
from .release_catalog import ReleaseRejected
from .release_operation import validate_plan
from .release_programs import ProgramTransaction,fingerprint
from .release_stage import validate_files


IDENTIFIER=re.compile('[0-9a-f]{32}')


def guard(profile, installed, *, bridge):
    profile,installed=Path(profile).absolute(),Path(installed).absolute()
    mount=bridge.memory_module('mount_transaction')
    baseline=bridge.memory_module('version_drift').default_baseline_path(installed.parent)
    transaction=mount.MountTransaction(installed,profile,baseline)
    try:manifest=transaction._manifest()
    except (RuntimeError,OSError,ValueError) as error:
        raise ReleaseRejected('The current native mount cannot prove guard ownership') from error
    if manifest is None or manifest['state']!='committed':
        raise ReleaseRejected('Complete the current native mount before software removal')
    root=profile/'plugins/lifeos';files={}
    for entry in manifest['entries']:
        target=Path(entry['target'])
        if not target.is_relative_to(root):continue
        actual=fingerprint(target);expected=entry['after']
        if actual!={'type':'file','mode':expected['mode'],'sha256':expected['digest']}:
            raise ReleaseRejected('A native guard changes after its owned mount')
        files[str(target.relative_to(root))]=expected['digest']
    if set(files)!={'__init__.py','guard.py','plugin.yaml','policy.json'}:
        raise ReleaseRejected('The native mount does not prove every guard file')
    validate_files(root,files)
    return fingerprint(root)


def pulse(profile, installed):
    profile,installed=Path(profile).absolute(),Path(installed).absolute()
    target=profile.parent/'.config/systemd/user/com.lifeos.pulse.service'
    identity=fingerprint(target)
    if identity is None or identity['type']!='file':
        raise ReleaseRejected('Removal requires the regular integration-owned Pulse definition')
    root=profile/'.lifeos-releases'
    if root.resolve()!=root or not root.is_dir():raise ReleaseRejected('The original managed service record is unavailable')
    for job in sorted(root.iterdir()):
        if IDENTIFIER.fullmatch(job.name) is None:continue
        try:
            request=read_private(job/'request.json');status=read_private(job/'status.json')
        except FileNotFoundError:continue
        if status.get('state')!='applied' or request.get('profile')!=str(profile) or request.get('installed')!=str(installed):continue
        plan=validate_plan(job,request)
        if plan.get('fresh') is not True:continue
        programs=ProgramTransaction(job/'program-snapshot',expected_entries_sha256=plan['program_entries_sha256'])
        entries=programs._load()['entries']
        if any(entry['target']==str(target) and entry['before'] is None and entry['after']==identity
                and entry['kind']=='file' for entry in entries):return target
    raise ReleaseRejected('The managed integration does not prove ownership of this Pulse definition')
