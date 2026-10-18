# ABOUTME: Finds this account's processes that use a Hermes source checkout or its environment generations.
# ABOUTME: Reports process IDs and command names, plus a dashboard's --host and --port; never environment values.
from __future__ import annotations

import os
from pathlib import Path
import re


def _references(data, roots):
    """True when ``data`` names a root itself or a path below it, not a sibling with the same prefix.

    A path ends at a separator, the end of an argument or variable, or a closing quote: the stock
    launcher passes the checkout inside Python code as a quoted string.
    """
    for root in roots:
        start = data.find(root)
        while start >= 0:
            end = start + len(root)
            if end == len(data) or data[end:end + 1] in (b'/', b'\0', b':', b' ', b'=', b"'", b'"'):
                return True
            start = data.find(root, start + 1)
    return False


def _commands(words, names):
    """Return the positions of ``names`` that are command words, not the value of a preceding ``--option``."""
    def text(word):
        return word.decode(errors='replace') if isinstance(word, bytes) else word
    return [index for index, word in enumerate(words) if word in names
            and not (index and text(words[index - 1]).startswith('--') and '=' not in text(words[index - 1]))]


def _role(arguments):
    """Classify a Hermes command line as the dashboard, the gateway, or another consumer."""
    words = arguments.split(b'\0')
    if _commands(words, (b'dashboard', b'serve')):
        return 'dashboard'
    if _commands(words, (b'gateway',)) and b'run' in words:
        return 'gateway'
    return 'other'


DASHBOARD_HOST = re.compile(r'[A-Za-z0-9._:\[\]-]{1,253}')


def dashboard_options(pid):
    """Return the ``--host`` and ``--port`` that a hand-started dashboard or ``serve`` runs with.

    The unit that replaces it must listen on the same address, or the owner loses the dashboard.
    Only these two options are read; the rest of the command line stays private. The defaults,
    which a unit without options also uses, are left out, and a shortened option refuses.
    """
    from .release_catalog import ReleaseRejected
    words = [word.decode(errors='replace') for word in Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0')[:-1]]
    commands = _commands(words, ('dashboard', 'serve'))
    if not commands:
        return {}
    rest, options, index = words[commands[0] + 1:], {}, 0
    refused = ReleaseRejected('A hand-started dashboard runs with an address that its unit cannot keep. '
                              'Start it with a plain --host and --port, then prepare again')
    while index < len(rest):
        written = rest[index].split('=', 1)[0]
        if any(flag != written and flag.startswith(written) and len(written) > 2 for flag in ('--host', '--port')):
            raise refused
        for name in ('host', 'port'):
            flag = '--' + name
            if rest[index] == flag:
                if index + 1 >= len(rest):
                    raise refused
                options[name] = rest[index + 1]
                index += 1
            elif rest[index].startswith(flag + '='):
                options[name] = rest[index].split('=', 1)[1]
        index += 1
    if 'host' in options and DASHBOARD_HOST.fullmatch(options['host']) is None:
        raise refused
    if 'port' in options:
        if not options['port'].isdecimal() or not 0 < int(options['port']) < 65536:
            raise refused
        options['port'] = int(options['port'])
    return {name: value for name, value in options.items() if value != {'host': '127.0.0.1', 'port': 9119}[name]}


def stat_fields(pid):
    """Return the fields of ``/proc/<pid>/stat`` after the command name, starting with the process state."""
    return Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()


def start_time(pid):
    """Return the kernel start time of ``pid`` in clock ticks, which identifies one process incarnation."""
    return int(stat_fields(pid)[19])


def parent(pid):
    """Return the parent process ID of ``pid``."""
    return int(stat_fields(pid)[1])


def process_names(items):
    """Return ``command (pid)`` for each found process, for a message that asks the owner to close them."""
    return ', '.join(item['command'] + ' (' + str(item['pid']) + ')' for item in items)


def source_consumers(source, state_dir, *, excluded_pids=frozenset(), excluded_groups=frozenset()):
    """Return ``[{'pid', 'start_time', 'command', 'role'}]`` for account processes that use ``source`` or ``state_dir``.

    Hermes puts the checkout on every process's ``PYTHONPATH`` and runs it from an environment generation
    below its install state directory, so the environment, command line, executable, and working
    directory together identify each consumer. Processes in ``excluded_groups`` (control groups of
    services that the caller has stopped or owns) and in ``excluded_pids`` are skipped. This process is
    skipped too unless it is a dashboard or gateway: a hand-started dashboard that serves the review is
    a consumer that its new unit replaces.
    """
    roots = tuple(str(Path(path).absolute()).encode() for path in (source, state_dir))
    skipped = set(excluded_pids)
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
            if not arguments or int(process.name) == os.getpid() and _role(arguments) == 'other':
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
