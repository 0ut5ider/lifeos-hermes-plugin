# ABOUTME: Verifies native all-time climb behavior after operational log growth.
# ABOUTME: Uses actual owner services and independent native controls with disposable large histories.
from datetime import datetime, timedelta, timezone
import json
import unittest

import httpx
import test_memory_operational_views as operational_fixture


class MemoryOperationalHistoryTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = operational_fixture.MemoryOperationalViewsTests.setUp
    create_fixture = operational_fixture.MemoryOperationalViewsTests.create_fixture
    native_module_name = operational_fixture.MemoryOperationalViewsTests.native_module_name
    stop_dashboard = operational_fixture.MemoryOperationalViewsTests.stop_dashboard
    stop_pulse = operational_fixture.MemoryOperationalViewsTests.stop_pulse
    login = operational_fixture.MemoryOperationalViewsTests.login
    original = operational_fixture.MemoryOperationalViewsTests.original
    seed = operational_fixture.MemoryOperationalViewsTests.seed

    def history(self, count, padding=0):
        self.seed()
        early = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        now = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        current = json.dumps({'ts': now, 'op': 'upsert', 'slug': 'synthetic-run',
            'fields': {'progress': '1/2'}, 'note': 'SyntheticQuietOperationalCurve'})
        rows = [current]
        for index in range(count):
            rows.append(json.dumps({'ts': early, 'op': 'upsert', 'slug': 'synthetic-previous-run',
                'fields': {'progress': f'{index % 2}/2'}, 'note': 'SyntheticPreviousOperational' + 'x' * padding}))
        path = self.root / 'LIFEOS/MEMORY/STATE/work-events.jsonl'
        path.write_text('\n'.join(rows) + '\n')
        return path

    def test_more_than_2048_records_preserve_native_climb_for_quiet_current_run(self):
        path = self.history(2050)
        self.assertLess(path.stat().st_size, 1024 * 1024)
        expected = self.original('/api/algorithm')
        self.assertEqual(len(expected['algorithms'][0]['climb']), 1)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm')
            print('Record-growth observation:', json.dumps({'bytes': path.stat().st_size,
                'records': 2051, 'native_climb_points': len(expected['algorithms'][0]['climb']),
                'managed_status': response.status_code}))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), expected)

    def test_multi_megabyte_history_preserves_native_climb_before_any_tail_window(self):
        path = self.history(5000, padding=100)
        self.assertGreater(path.stat().st_size, 1024 * 1024)
        expected = self.original('/api/algorithm')
        self.assertEqual(len(expected['algorithms'][0]['climb']), 1)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm')
            print('Byte-growth observation:', json.dumps({'bytes': path.stat().st_size,
                'records': 5001, 'native_climb_points': len(expected['algorithms'][0]['climb']),
                'managed_status': response.status_code}))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), expected)


if __name__ == '__main__':
    unittest.main()
