# ABOUTME: Compares native business overview and revenue selection through actual owner HTTP sessions.
# ABOUTME: Checks bounded company discovery, source labels, retirement, and current authority.
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

import httpx
import test_memory_life_relay as life_fixture


class MemoryLifeBusinessTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = life_fixture.MemoryLifeRelayTests.setUp
    create_fixture = life_fixture.MemoryLifeRelayTests.create_fixture
    native_module_name = life_fixture.MemoryLifeRelayTests.native_module_name
    stop_dashboard = life_fixture.MemoryLifeRelayTests.stop_dashboard
    stop_pulse = life_fixture.MemoryLifeRelayTests.stop_pulse
    login = life_fixture.MemoryLifeRelayTests.login
    original = life_fixture.MemoryLifeRelayTests.original

    def seed(self):
        directory = self.root / 'LIFEOS/USER/WORK/YOUR_COMPANIES'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'README.md').write_text('## Businesses\nSyntheticBusinessOverview\n')
        (directory / 'synthetic-empty').mkdir(exist_ok=True)
        company = directory / 'synthetic-company'
        revenue = company / 'REVENUE'
        revenue.mkdir(parents=True, exist_ok=True)
        (company / 'README.md').write_text('## Company\nSyntheticCompanyOverview\n')
        (revenue / '2026-09.md').write_text('## Summary\nSyntheticOlderRevenue\n')
        (revenue / '2026-10.md').write_text('## Summary\nSyntheticCurrentRevenue\n## Product revenue\nSyntheticProductRevenue\n')
        return directory, company, revenue

    def get(self, client): return client.get(self.native + '/api/life/business')

    def test_company_preference_and_latest_report_match_native(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/business'))
            self.assertEqual(response.json()['latestRevenueReport'], '2026-10.md')
            self.assertIn('SyntheticCurrentRevenue', response.text)
            self.assertIn('SyntheticCompanyOverview', response.text)

    def test_empty_and_no_revenue_company_match_native(self):
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/business'))
        directory = self.root / 'LIFEOS/USER/WORK/YOUR_COMPANIES/synthetic-no-revenue'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'README.md').write_text('## Company\nSyntheticCompanyWithoutRevenue\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/business'))

    def test_anonymous_revoked_and_missing_connector_refuse_business(self):
        self.seed()
        self.assertEqual(httpx.get(self.native + '/api/life/business').status_code, 401)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            self.assertEqual(self.get(client).status_code, 403)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            self.assertEqual(self.get(client).status_code, 503)

    def test_private_company_and_report_body_or_name_do_not_publish(self):
        _, company, revenue = self.seed()
        (company / 'README.md').write_text('## Company\n<private>SyntheticPrivateCompany</private>\n')
        (revenue / '2026-10.md').write_text('## Summary\n<private>SyntheticPrivateRevenue</private>\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticPrivate', response.text)
            self.assertNotIn('2026-10.md', response.text)
            self.assertIn('SyntheticBusinessOverview', response.text)

    def test_current_retired_report_filename_stays_excluded(self):
        _, company, revenue = self.seed()
        filename = '2026-11-SyntheticRetiredReport.md'
        (revenue / filename).write_text('## Summary\nSynthetic retained report\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.assertIn(filename, self.get(client).text)
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(life_fixture.OWNER, category='principal', content='RULE: SyntheticRetiredReport',
            title='', project='', request_id='synthetic-business-retire-source')
        memory.forget(life_fixture.OWNER, saved['reference'], 'synthetic-business-retire')
        os.utime(company, ns=(time.time_ns(), time.time_ns()))
        for source in revenue.iterdir(): os.utime(source, ns=(time.time_ns(), time.time_ns()))
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn(filename, response.text)
            self.assertIn('SyntheticCurrentRevenue', response.text)
        self.assertTrue((revenue / filename).exists())

    def test_multiple_companies_without_revenue_preserve_native_enumeration(self):
        directory = self.root / 'LIFEOS/USER/WORK/YOUR_COMPANIES'
        for name in ('synthetic-zebra', 'synthetic-alpha', 'synthetic-middle'):
            company = directory / name
            company.mkdir(parents=True, exist_ok=True)
            (company / 'README.md').write_text('## Company\n' + name + '\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/business'))

    def test_redirected_revenue_directory_refuses(self):
        _, company, revenue = self.seed()
        external = self.fixture.home / 'synthetic-external-revenue'
        revenue.rename(external)
        revenue.symlink_to(external, target_is_directory=True)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.assertEqual(self.get(client).status_code, 503)

    def test_hardlinked_or_oversize_report_refuses(self):
        _, _, revenue = self.seed()
        path = revenue / '2026-10.md'
        alias = self.fixture.home / 'synthetic-report-alias.md'
        os.link(path, alias)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.assertEqual(self.get(client).status_code, 503)
            alias.unlink()
            path.write_text('SyntheticOversizeRevenue' * 14000)
            self.assertEqual(self.get(client).status_code, 503)

    def test_report_directory_or_authority_changes_withhold_rendered_response(self):
        self.seed()
        for mode in ('source', 'report', 'authority'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_life_process.py')),
                    str(self.fixture.configuration.path), mode, '/api/life/business'], capture_output=True, text=True,
                    timeout=40, env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_discovery_has_a_fixed_entry_limit(self):
        directory, _, _ = self.seed()
        for number in range(2050): (directory / ('synthetic-entry-' + str(number))).touch()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.assertEqual(self.get(client).status_code, 503)

    def test_retired_company_label_excludes_child_sources(self):
        directory, company, _ = self.seed()
        label = 'SyntheticRetiredCompany'
        renamed = directory / label
        company.rename(renamed)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.assertIn('SyntheticCurrentRevenue', self.get(client).text)
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(life_fixture.OWNER, category='principal', content='RULE: ' + label,
            title='', project='', request_id='synthetic-company-label-source')
        memory.forget(life_fixture.OWNER, saved['reference'], 'synthetic-company-label-forget')
        for path in (renamed, directory / 'README.md', renamed / 'README.md', *list((renamed / 'REVENUE').iterdir())):
            os.utime(path, ns=(time.time_ns(), time.time_ns()))
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['ulOverview'], [])
            self.assertEqual(response.json()['latestRevenueReport'], '')
            self.assertNotIn('SyntheticCurrentRevenue', response.text)
            self.assertIn('SyntheticBusinessOverview', response.text)
        self.assertTrue((renamed / 'REVENUE/2026-10.md').is_file())

    def test_foreign_origin_bearer_selectors_and_nonget_refuse(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            for method, suffix, headers, status in (
                ('GET', '', {'Origin': 'https://outside.invalid'}, 403),
                ('GET', '', {'Authorization': 'Bearer synthetic-invalid'}, 401),
                ('GET', '?company=other', {}, 400),
                ('POST', '', {}, 405),
            ):
                with self.subTest(method=method, suffix=suffix, headers=headers):
                    response = client.request(method, self.native + '/api/life/business' + suffix, headers=headers)
                    self.assertEqual(response.status_code, status, response.text)
                    self.assertNotIn('SyntheticCurrentRevenue', response.text)


if __name__ == '__main__':
    unittest.main()
