# ABOUTME: Checks fixed recovery request admission with real authenticated local routes.
# ABOUTME: Replaces only the service launcher and saves no private runtime data.
import json
from unittest.mock import patch
from test_memory_admin_dashboard import MemoryAdminDashboardTests
for label, suffix, options in (
    ('origin', '', {'headers':{'Origin':'https://other.invalid'}}),
    ('query', '?job=other', {}),
    ('body', '', {'json':{'job':'other'}})):
    fixture=MemoryAdminDashboardTests()
    fixture.setUp()
    try:
        fixture.login()
        job=fixture.interrupted_job()
        before_request=(job/'request.json').read_bytes()
        before_status=(job/'status.json').read_bytes()
        with patch.object(fixture.api, '_launch_lifeos_update') as launched:
            response=fixture.client.post(fixture.prefix+'/update/recover'+suffix, **options)
        print(json.dumps({'case':label, 'status':response.status_code, 'launch_count':launched.call_count,
            'job_unchanged':before_request==(job/'request.json').read_bytes() and before_status==(job/'status.json').read_bytes(),
            'grant_count':len(fixture.grants())}, sort_keys=True))
    finally:
        fixture.doCleanups()
