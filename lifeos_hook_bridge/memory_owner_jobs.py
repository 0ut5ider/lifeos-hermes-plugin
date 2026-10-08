# ABOUTME: Admits fixed native background jobs as the current local account owner.
# ABOUTME: Keeps jobs within current memory grants and confines child process lifetimes.
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import uuid

from .memory_access import NativeMemory
from .memory_policy import CATEGORIES
from .memory_runtime import MemoryAdmissionError, MemoryRuntime
from .memory_service import MemoryService


JOBS = {
    'memory-consolidation': (('LIFEOS/TOOLS/SessionHarvester.ts', '--recent', '20'),
                             ('LIFEOS/TOOLS/LearningPatternSynthesis.ts', '--week')),
    'life-morning-brief': (('LIFEOS/PULSE/checks/life-morning-brief.ts',),),
    'proposal-gc': (('LIFEOS/TOOLS/ProposalGC.ts', '--auto'),),
}
MAX_OUTPUT = 4 * 1024 * 1024


def _terminate(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def _command(arguments, environment, timeout):
    # File-backed pipes keep a bounded job from retaining unbounded output in RAM.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(arguments, env=environment, stdout=output, stderr=errors,
                                   start_new_session=True)
        previous = signal.getsignal(signal.SIGTERM)
        def stop(signum, frame):
            raise SystemExit(128 + signum)
        signal.signal(signal.SIGTERM, stop)
        try:
            process.wait(timeout=timeout)
        except BaseException:
            _terminate(process)
            raise
        finally:
            signal.signal(signal.SIGTERM, previous)
        output.seek(0)
        content = output.read(MAX_OUTPUT + 1)
        if len(content) > MAX_OUTPUT:
            raise ValueError('The selected native job exceeds its output limit')
        return process.returncode, content.decode('utf-8')


class OwnerJobs:
    def __init__(self, configuration: Path):
        self.runtime = MemoryRuntime(configuration)

    def run(self, name: str, *, route: dict, mapping: dict, timeout: float = 540) -> dict:
        if name not in JOBS:
            raise ValueError('Choose a supported native owner job')
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 540:
            raise ValueError('Native owner jobs require a deadline of at most 540 seconds')
        self.runtime.clear()
        if not self.runtime.enabled():
            raise MemoryAdmissionError('Native owner jobs require activated memory ownership')
        configuration = self.runtime.configuration.load()
        root = Path(configuration['root'])
        session = 'owner-job-' + uuid.uuid4().hex
        self.runtime.admit({'HERMES_SESSION_PLATFORM': 'cli', 'HERMES_SESSION_ID': session},
                           **route, is_first_turn=True)
        context = self.runtime.context()
        scope = self.runtime._scope(configuration, context)
        if scope.principal != configuration['principal'] or set(scope.write) != CATEGORIES:
            self.runtime.clear()
            raise MemoryAdmissionError('Native owner jobs require unrestricted owner write permission')
        environment = {key: value for key, value in os.environ.items()
            if not key.startswith(('HERMES_SESSION_', 'HERMES_CRON_', 'LIFEOS_MEMORY_'))}
        environment.update(HOME=str(root.parent), LIFEOS_ACCOUNT_HOME=str(Path.home()),
            LIFEOS_DIR=str(root / 'LIFEOS'), LIFEOS_NOTIFICATION_CHANNEL='headless',
            LIFEOS_MODEL_TIER_MAP=json.dumps(mapping), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment['PATH'] = os.pathsep.join((str(Path(__file__).parent / 'bin'),
            str(Path.home() / '.bun/bin'), str(Path.home() / '.local/bin'), environment.get('PATH', '')))
        self.runtime.bind_environment(environment, session_id=session)
        deadline = time.monotonic() + timeout
        output = []
        for command in JOBS[name]:
            self.runtime.check_call(request={}, **route, session_id=session, metadata={})
            result, text = _command(['bun', '--no-install', str(root / command[0]),
                *command[1:]], environment, max(0.001, deadline - time.monotonic()))
            if result:
                return {'status': 'failed', 'job': name, 'exit_code': result}
            output.append(text)
        projected = MemoryService(self.runtime.configuration).native(context, 'filter_history',
            {'content': ''.join(output), 'timestamp': datetime.now(timezone.utc).isoformat()})
        self.runtime.check_call(request={}, **route, session_id=session, metadata={})
        if not projected.get('ok', True) or projected.get('excluded'):
            return {'status': 'response-withheld', 'job': name}
        return {'status': 'completed', 'job': name, 'output': projected['content']}
