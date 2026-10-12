# ABOUTME: Exercises actual public restore admission against an isolated applied operation.
# ABOUTME: Captures the preflight variable error without services, credentials, or live installation changes.
import json
import tempfile
import traceback
from pathlib import Path
from test_release_operation import ReleaseOperationTests
from optional.lifeos_release_manager.cli import read_private, write_state
from optional.lifeos_release_manager.release_worker import admit_operation
with tempfile.TemporaryDirectory() as temp:
    profile, job, request = ReleaseOperationTests().recovery_fixture(Path(temp))
    write_state(job, 'applied')
    try:
        admit_operation(job, request, 'restore')
    except Exception as error:
        print(type(error).__name__ + ': ' + str(error))
        traceback.print_exc()
    print('state after admission:', read_private(job / 'status.json')['state'])
    print('admission written:', (job / 'admission.json').exists())
