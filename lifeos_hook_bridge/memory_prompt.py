# ABOUTME: Collects admitted native identity, constitution, skills, and current hot facts for a prompt.
# ABOUTME: Renders one coherent source snapshot without allowing the native formatter to reopen files.
import hashlib
import json
import os
import re
from itertools import count
from pathlib import Path

from .memory_access import MemoryUnavailable
from .memory_sources import read_markdown, authorize
from .memory_transaction import publish
from .memory_wiki import _directory_entries


SOURCES = {'systemPrompt': 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md',
           'daIdentity': 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md',
           'principal': 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md',
           'telos': 'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md', 'projects': 'LIFEOS/USER/PROJECTS.md'}


def admit_names(memory, scope, connection, declared, selected):
    names = memory._native('hermes_soul_names', sources=declared)
    if set(names) != {'name', 'fullName', 'principal'} or any(not isinstance(value, str) or len(value) > 256 for value in names.values()):
        raise MemoryUnavailable('Native Hermes soul naming is invalid')
    for name, fields in (('daIdentity', ('name', 'fullName')), ('principal', ('principal',))):
        projection = declared[name] + '\n' + '\n'.join(names[field] for field in fields)
        valid = memory._native('validate_source_batch', contents=[projection])['accepted']
        timestamp = next((source['lastModified'] for source in selected if source['relative'] == SOURCES[name]),
                         '1970-01-01T00:00:00Z')
        if valid != [True] or memory._filter_history(connection, scope, projection, timestamp, reviewed=True)['excluded']:
            declared[name] = ''


def _collect(memory, scope, connection, keep_output_format):
    authorize(scope)
    if type(keep_output_format) is not bool:
        raise ValueError('Choose whether to retain the native output format')
    skills = memory.root / 'skills'
    if skills.is_symlink():
        raise MemoryUnavailable('The prompt skills directory changes its installed path')
    paths = [str(memory.root / relative) for relative in SOURCES.values()]
    if skills.exists():
        visits = count(1)
        for directory in _directory_entries(skills, visits):
            if directory.name.startswith(('.', '_')):
                continue
            if directory.is_symlink():
                raise MemoryUnavailable('A prompt skill changes its installed path')
            path = directory / 'SKILL.md'
            if directory.is_dir() and (path.exists() or path.is_symlink()):
                paths.append(str(path))
    selected = read_markdown(memory, scope, paths, connection=connection)
    content = {source['relative']: source['content'] for source in selected}
    if SOURCES['systemPrompt'] not in content:
        raise MemoryUnavailable('The LifeOS constitution requires current source review before prompt generation')
    declared = {name: content.get(relative, '') for name, relative in SOURCES.items()}
    for category, name in (('principal', 'principalMemory'), ('assistant', 'daMemory')):
        snapshot = memory._hot_snapshot(connection, category)
        declared[name] = '\n'.join(snapshot['entries'])
    admit_names(memory, scope, connection, declared, selected)
    skill_sources = [{'directory': Path(source['relative']).parent.name, 'content': source['content']}
                     for source in selected if source['relative'].startswith('skills/')]
    result = memory._native('prompt_bundle', sources=declared, skills=skill_sources,
                            options={'keepOutputFormat': keep_output_format, 'integration': True})
    if (set(result) != {'bundle'} or not isinstance(result['bundle'], dict)
            or set(result['bundle']) != {'soul','constitution','identity','skillRouting','skills','launcherName'}
            or any(not isinstance(result['bundle'][name], str) for name in ('soul','constitution','identity','skillRouting','launcherName'))):
        raise MemoryUnavailable('Native prompt rendering returned an invalid bundle')
    if read_markdown(memory, scope, paths, connection=connection) != selected:
        raise MemoryUnavailable('The prompt sources changed during rendering. Review a fresh snapshot.')
    identity = {'sources': selected, 'hot': {name: declared[name] for name in ('principalMemory', 'daMemory')},
                'retired': [dict(row) for row in connection.execute("SELECT * FROM records WHERE status IN ('forgotten','superseded') ORDER BY id")],
                'scope': scope.signature, 'root': str(memory.root), 'options': keep_output_format, 'bundle': result['bundle']}
    signature = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {'bundle': result['bundle'], 'signature': signature,
            'omitted_sources': [str(Path(path).relative_to(memory.root)) for path in paths
                                if path not in {source['path'] for source in selected}]}


def bundle(memory, scope, *, keep_output_format=False):
    with memory._transaction() as connection:
        return _collect(memory, scope, connection, keep_output_format)['bundle']


def _destination(profile):
    profile = Path(profile).absolute()
    if profile.is_symlink() or profile.resolve() != profile or not profile.is_dir() or profile.stat().st_uid != os.getuid():
        raise MemoryUnavailable('Prompt publication needs the installed owner profile')
    path = profile / 'SOUL.md'
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if path.is_symlink() or not path.is_file() or info.st_uid != os.getuid() or info.st_size > 1024 * 1024:
            raise MemoryUnavailable('The installed prompt needs a regular owner file within its size limit')
        data = path.read_bytes()
        after = path.stat()
        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise MemoryUnavailable('The installed prompt changed during collection')
        return path, hashlib.sha256(data).hexdigest()
    return path, 'absent'


def preview(memory, scope, profile, *, keep_output_format=False):
    with memory._transaction() as connection:
        plan = _collect(memory, scope, connection, keep_output_format)
        _, current = _destination(profile)
        return {**plan, 'previous_digest': current}


def publish_prompt(memory, scope, profile, signature, previous_digest, *, keep_output_format=False, check_current=None):
    if (not isinstance(signature, str) or re.fullmatch('[0-9a-f]{64}', signature) is None
            or not isinstance(previous_digest, str)
            or previous_digest != 'absent' and re.fullmatch('[0-9a-f]{64}', previous_digest) is None):
        raise ValueError('Prompt publication requires a reviewed snapshot and installed prompt digest')
    if not {'principal', 'assistant', 'project'} <= set(scope.write):
        raise MemoryUnavailable('Prompt publication requires unrestricted owner write access')
    with memory._transaction() as connection:
        plan = _collect(memory, scope, connection, keep_output_format)
        if check_current is not None:
            check_current()
        if plan['signature'] != signature:
            return {'status': 'conflict', 'reason': 'Prompt sources changed. Review a fresh preview.'}
        destination, current = _destination(profile)
        data = plan['bundle']['soul'].encode()
        desired = hashlib.sha256(data).hexdigest()
        if len(data) > 1024 * 1024 or len(plan['bundle']['soul']) > 100_000:
            raise MemoryUnavailable('The native prompt exceeds its configured publication limit')
        if current == desired and destination.stat().st_mode & 0o777 == 0o600:
            return {'status': 'unchanged', 'digest': desired}
        if current != previous_digest:
            return {'status': 'conflict', 'reason': 'The installed prompt changed. Review a fresh preview.'}
        publish(destination, data)
        return {'status': 'committed', 'digest': desired}
