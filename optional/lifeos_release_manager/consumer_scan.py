# ABOUTME: Finds this account's processes that use a Hermes source checkout or its environment generations.
# ABOUTME: Reports process IDs and command names only; it never exports arguments or environment values.
from __future__ import annotations

import os
from pathlib import Path


def _references(data, roots):
    """True when ``data`` names a root itself or a path below it, not a sibling with the same prefix."""
    for root in roots:
        start = data.find(root)
        while start >= 0:
            end = start + len(root)
            if end == len(data) or data[end:end + 1] in (b'/', b'\0', b':', b' ', b'='):
                return True
            start = data.find(root, start + 1)
    return False


def _role(arguments):
    """Classify a Hermes command line as the dashboard, the gateway, or another consumer."""
    words = arguments.split(b'\0')
    if b'dashboard' in words or b'serve' in words:
        return 'dashboard'
    if b'gateway' in words and b'run' in words:
        return 'gateway'
    return 'other'


def start_time(pid):
    """Return the kernel start time of ``pid`` in clock ticks, which identifies one process incarnation."""
    fields = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
    return int(fields[19])


def source_consumers(source, state_dir, *, excluded_pids=frozenset(), excluded_groups=frozenset()):
    """Return ``[{'pid', 'start_time', 'command', 'role'}]`` for account processes that use ``source`` or ``state_dir``.

    Hermes puts the checkout on every process's ``PYTHONPATH`` and runs it from an environment generation
    below its install state directory, so the environment, command line, executable, and working
    directory together identify each consumer. Processes in ``excluded_groups`` (control groups of
    services that the caller has stopped or owns) and in ``excluded_pids`` are skipped, as is this process.
    """
    roots = tuple(str(Path(path).absolute()).encode() for path in (source, state_dir))
    skipped = {os.getpid(), *excluded_pids}
    found = []
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal() or int(process.name) in skipped:
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            groups = {line.removeprefix('0::') for line in (process / 'cgroup').read_text().splitlines()
                      if line.startswith('0::')}
            if groups and groups <= set(excluded_groups):
                continue
            arguments = (process / 'cmdline').read_bytes()
            if not arguments:
                continue
            evidence = [arguments]
            # Non-dumpable programs such as ssh-agent hide their environment and links even from their owner.
            # Hermes runs as an ordinary Python process, whose environment stays readable.
            try:
                evidence.append((process / 'environ').read_bytes())
            except PermissionError:
                pass
            for link in ('exe', 'cwd'):
                try:
                    evidence.append(os.readlink(process / link).removesuffix(' (deleted)').encode())
                except (PermissionError, OSError):
                    pass
            if any(_references(data, roots) for data in evidence):
                found.append({'pid': int(process.name), 'start_time': start_time(int(process.name)),
                              'command': Path(arguments.split(b'\0', 1)[0].decode(errors='replace')).name,
                              'role': _role(arguments)})
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            continue
    return sorted(found, key=lambda item: item['pid'])
