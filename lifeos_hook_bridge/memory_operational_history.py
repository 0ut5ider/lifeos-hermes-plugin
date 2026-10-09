# ABOUTME: Streams complete work-event history into an anonymous private admitted snapshot.
# ABOUTME: Bounds record validation and rechecks original bytes before native all-time folding.
import hashlib
import json
import os
from contextlib import contextmanager
import tempfile

from .memory_access import MemoryUnavailable
from .memory_source_review import is_reviewed
from .memory_sources import _admit, _source_time, SOURCE_LIMIT, SOURCE_COUNT_LIMIT, CORPUS_LIMIT
from .memory_tab_freshness import _checked


SOURCES = {'LIFEOS/MEMORY/STATE/work-events.jsonl': None,
           'LIFEOS/MEMORY/OBSERVABILITY/tool-activity.jsonl': 512 * 1024}


def fingerprint(memory, relative):
    path = _checked(memory, memory.root / relative)
    if not path.exists(): return (relative, None)
    if not path.is_file(): raise MemoryUnavailable('Operational history requires a regular owner file')
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        if SOURCES[relative] is not None: stream.seek(max(0, before.st_size - SOURCES[relative]))
        while chunk := stream.read(128 * 1024): digest.update(chunk)
    after = path.stat()
    _checked(memory, path)
    keys = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if keys(before) != keys(after): raise MemoryUnavailable('Operational history changes during fingerprinting')
    return (relative, keys(after), digest.hexdigest())


@contextmanager
def snapshot(memory, scope, connection, *, check_current=None):
    from .memory_operational_views import projection, _timestamp
    admitted_digest = hashlib.sha256()
    fingerprints = []
    with tempfile.TemporaryFile(mode='w+b') as output:
        for relative, limit in SOURCES.items():
            path = _checked(memory, memory.root / relative)
            if not path.exists():
                fingerprints.append((relative, None))
                continue
            if not path.is_file(): raise MemoryUnavailable('Operational history requires a regular owner file')
            before = path.stat()
            original = original_bytes = None
            if before.st_size <= SOURCE_LIMIT:
                with path.open('rb') as stream: original_bytes = stream.read(SOURCE_LIMIT + 1)
                if len(original_bytes) > SOURCE_LIMIT:
                    raise MemoryUnavailable('Operational history changes during review collection')
                try: original = original_bytes.decode('utf-8')
                except UnicodeError: pass
            reviewed = original is not None and is_reviewed(memory, connection, scope, relative, original)
            raw_digest = hashlib.sha256()
            batch, size = [], 2

            def flush():
                nonlocal batch, size
                if not batch: return
                if check_current is not None: check_current()
                checked = memory._native('validate_source_batch', contents=[item[2] + '\n' + relative for item in batch])['accepted']
                for (line, timestamp, decoded), valid in zip(batch, checked, strict=True):
                    if valid is True and not _admit(memory, connection, scope, line, relative, timestamp,
                            projection=decoded, source_reviewed=reviewed)['excluded']:
                        body = (json.dumps({'relative': relative, 'content': line}, ensure_ascii=False) + '\n').encode()
                        output.write(body)
                        admitted_digest.update(body)
                batch, size = [], 2

            with path.open('rb') as stream:
                offset = max(0, before.st_size - limit) if limit is not None else 0
                stream.seek(offset)
                if offset:
                    while partial := stream.readline(128 * 1024):
                        raw_digest.update(partial)
                        if partial.endswith(b'\n'): break
                while raw := stream.readline(SOURCE_LIMIT + 2):
                    raw_digest.update(raw)
                    if len(raw.rstrip(b'\r\n')) > SOURCE_LIMIT:
                        raise MemoryUnavailable('An operational history event exceeds its byte limit')
                    if not raw.endswith(b'\n'): break
                    try: line = raw.decode('utf-8').rstrip('\r\n')
                    except UnicodeError as error:
                        raise MemoryUnavailable('Operational history requires valid UTF-8') from error
                    if not line: continue
                    try: row = json.loads(line)
                    except (ValueError, RecursionError): continue
                    if not isinstance(row, dict): continue
                    decoded = projection(line)
                    if decoded is None: continue
                    added = len(json.dumps(decoded + '\n' + relative).encode()) + 2
                    if added > CORPUS_LIMIT - 4096:
                        raise MemoryUnavailable('An operational history projection exceeds its transport limit')
                    if batch and (len(batch) >= SOURCE_COUNT_LIMIT or size + added > CORPUS_LIMIT - 4096): flush()
                    batch.append((line, _timestamp(row, _source_time(before)), decoded))
                    size += added
                flush()
            expected = (relative, (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns), raw_digest.hexdigest())
            if original_bytes is not None and hashlib.sha256(original_bytes).hexdigest() != raw_digest.hexdigest():
                raise MemoryUnavailable('Operational history changes its reviewed source bytes')
            if fingerprint(memory, relative) != expected:
                raise MemoryUnavailable('Operational history changes during admission')
            fingerprints.append(expected)
        output.flush()
        if check_current is not None: check_current()
        # The unlinked file survives only through inherited descriptors. Process death leaves no named copy.
        with os.fdopen(os.open(f'/proc/self/fd/{output.fileno()}', os.O_RDONLY), 'rb') as reader:
            yield reader.fileno(), fingerprints
        output.seek(0)
        after = hashlib.sha256()
        while chunk := output.read(128 * 1024): after.update(chunk)
        if after.hexdigest() != admitted_digest.hexdigest():
            raise MemoryUnavailable('The admitted operational snapshot changes during native rendering')
