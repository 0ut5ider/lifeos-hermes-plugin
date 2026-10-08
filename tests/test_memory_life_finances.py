# ABOUTME: Exercises native finance views through actual authenticated owner HTTP sessions.
# ABOUTME: Compares complete responses and checks decoded structured source admission and current authority.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
import test_memory_life_relay as life_fixture


class MemoryLifeFinanceTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = life_fixture.MemoryLifeRelayTests.setUp
    create_fixture = life_fixture.MemoryLifeRelayTests.create_fixture
    native_module_name = life_fixture.MemoryLifeRelayTests.native_module_name
    stop_dashboard = life_fixture.MemoryLifeRelayTests.stop_dashboard
    stop_pulse = life_fixture.MemoryLifeRelayTests.stop_pulse
    login = life_fixture.MemoryLifeRelayTests.login
    original = life_fixture.MemoryLifeRelayTests.original

    def seed(self):
        directory = self.root / 'LIFEOS/USER/FINANCES'
        directory.mkdir(parents=True, exist_ok=True)
        texts = {
            'INCOME.md': '## Income\n| Source | Annual |\n|---|---|\n| SyntheticMembership | $12000 |\n',
            'EXPENSES.md': '## Expenses\n| Category | Annual |\n|---|---|\n| SyntheticTravel | $1200 |\n',
            'ACCOUNTS.md': '## Accounts\nSyntheticAccount current\n',
            'INVESTMENTS.md': '## Investments\nSyntheticInvestment current\n',
            'TAXES.md': '## Taxes\nEffective tax rate: 20%\n',
            'PLAN.md': '## Flywheel\n1. **SyntheticStage** - Synthetic action\n## Targets\n| Goal | Target |\n|---|---|\n| SyntheticGoal | 100 |\n',
            'GOALS.md': '## Goals\nSyntheticFinanceGoal current\n',
            'FINANCES.md': '## Finances\nSyntheticFinanceOverview current\n',
            'state.json': json.dumps({'last_run': '2026-10-08', 'note': 'SyntheticStateNote'}),
            'vendors.yaml': 'vendors:\n  - id: synthetic_vendor\n    name: SyntheticVendor\n    manual_monthly_usd: 12\n    scope: business\n',
            'obligations.yaml': 'obligations:\n  - vendor: SyntheticRent\n    amount: "$120"\n    frequency: monthly\n    scope: business\n',
        }
        for name, text in texts.items(): (directory / name).write_text(text)
        observation = self.root / 'LIFEOS/MEMORY/OBSERVABILITY'
        observation.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        (observation / 'vendor-costs.jsonl').write_text(json.dumps({
            'vendor': 'synthetic_vendor', 'cost_usd': 19, 'captured_at': now}) + '\n')
        self.record = {'merchant': 'synthetic_statement', 'display': 'SyntheticStatement', 'scope': 'personal',
            'tags': [], 'accounts': [], 'transaction_count': 2, 'charge_count': 2, 'credit_count': 0,
            'gross_charges_usd': 30, 'gross_credits_usd': 0, 'net_usd': 30,
            'first_seen': '2026-09-01', 'last_seen': '2026-10-01', 'active_months': 2,
            'cadence': 'monthly_recurring', 'monthly_avg_usd': 15, 'annualized_usd': 180}
        self.statement = observation / 'statement-spend.jsonl'
        self.statement.write_text(json.dumps({'schema': 'pulse.statement_spend.v1', 'generated_at': now}) + '\n'
            + json.dumps(self.record) + '\n')
        return directory

    def get(self, client): return client.get(self.native + '/api/life/finances')

    def test_populated_view_matches_all_native_fields(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/finances'))
            self.assertEqual(response.json()['outbound']['vendors'][0]['source'], 'collector')
            self.assertEqual(response.json()['insights']['statement_spend']['record_count'], 1)

    def test_empty_view_matches_native_defaults(self):
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/finances'))

    def test_currency_and_missing_key_match_native_config_defaults(self):
        self.seed()
        config = self.root / 'LIFEOS/USER/CONFIG/LIFEOS_CONFIG.toml'
        config.write_text('[principal]\nname="SyntheticOwner"\ntimezone="UTC"\ncurrency="CAD"\n'
            '[da]\nname="SyntheticAssistant"\n[da.voices.main]\nvoice_id="synthetic-voice"\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            for currency in ('CAD', '', '17'):
                with self.subTest(currency=currency):
                    text = config.read_text()
                    text = '\n'.join(line for line in text.splitlines() if not line.startswith('currency='))
                    if currency: text = text.replace('[da]', 'currency=' + (currency if currency == '17' else '"CAD"') + '\n[da]')
                    config.write_text(text)
                    response = self.get(client)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json(), self.original('/api/life/finances'))

    def test_anonymous_and_revoked_accounts_cannot_read_finances(self):
        self.seed()
        response = httpx.get(self.native + '/api/life/finances')
        self.assertEqual(response.status_code, 401, response.text)
        self.assertNotIn('SyntheticAccount', response.text)
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.fixture.configuration.update(lambda value: value['accounts'].pop('dashboard:basic:synthetic-owner'))
            response = self.get(client)
            self.assertEqual(response.status_code, 403, response.text)
            self.assertNotIn('SyntheticAccount', response.text)

    def test_private_sources_and_decoded_jsonl_rows_do_not_publish(self):
        directory = self.seed()
        (directory / 'ACCOUNTS.md').write_text('## Accounts\n<private>SyntheticPrivateAccount</private>\n')
        (directory / 'state.json').write_text('{"note":"\\u003cprivate\\u003eSyntheticPrivateState\\u003c/private\\u003e"}')
        (directory / 'vendors.yaml').write_text('vendors:\n  - id: synthetic_private\n    name: "\\x3cprivate>SyntheticPrivateVendor\\x3c/private>"\n')
        private = {**self.record, 'merchant': 'synthetic_private', 'display': '<private>SyntheticPrivateStatement</private>'}
        with self.statement.open('a') as stream: stream.write(json.dumps(private).replace('<', '\\u003c') + '\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticPrivate', response.text)
            self.assertIn('SyntheticStatement', response.text)
            self.assertIn('SyntheticRent', response.text)
            self.assertEqual(response.json()['insights']['statement_spend']['record_count'], 1)

    def test_forgotten_decoded_yaml_and_statement_rows_stay_retired(self):
        directory = self.seed()
        (directory / 'vendors.yaml').write_text('vendors:\n  - id: synthetic_retired\n    name: "Synthetic\\x52etiredVendor"\n    manual_monthly_usd: 12\n')
        retired = {**self.record, 'merchant': 'synthetic_retired', 'display': 'SyntheticRetiredStatement'}
        with self.statement.open('a') as stream: stream.write(json.dumps(retired).replace('Retired', '\\u0052etired') + '\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            before = self.get(client)
            self.assertIn('SyntheticRetiredVendor', before.text)
            self.assertIn('SyntheticRetiredStatement', before.text)
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        for label in ('SyntheticRetiredVendor', 'SyntheticRetiredStatement'):
            saved = memory.remember(life_fixture.OWNER, category='principal', content='RULE: ' + label,
                title='', project='', request_id='synthetic-finance-' + label)
            memory.forget(life_fixture.OWNER, saved['reference'], 'synthetic-finance-forget-' + label)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticRetired', response.text)
            self.assertEqual(response.json()['insights']['statement_spend']['record_count'], 0)
        # Unknown retained sources predating retirement need current source evidence or an owner review.
        for path in (*directory.iterdir(), *self.statement.parent.iterdir()):
            os.utime(path, None)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticRetired', response.text)
            self.assertIn('SyntheticStatement', response.text)
            self.assertEqual(response.json()['insights']['statement_spend']['record_count'], 1)
        self.assertIn('Synthetic\\x52etiredVendor', (directory / 'vendors.yaml').read_text())
        self.assertIn('\\u0052etiredStatement', self.statement.read_text())

    def test_connector_loss_does_not_restore_raw_reads(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            response = self.get(client)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticStatement', response.text)

    def test_redirected_or_hardlinked_source_refuses(self):
        directory = self.seed()
        path = directory / 'ACCOUNTS.md'
        outside = self.fixture.home / 'synthetic-finance-outside.md'
        os.link(path, outside)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            self.assertEqual(self.get(client).status_code, 503)
            outside.unlink()
            path.rename(outside)
            path.symlink_to(outside)
            self.assertEqual(self.get(client).status_code, 503)

    def test_oversize_source_refuses(self):
        directory = self.seed()
        (directory / 'state.json').write_text(json.dumps({'note': 'SyntheticOversizeState' * 15000}))
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 503, response.text)
            self.assertNotIn('SyntheticOversizeState', response.text)

    def test_source_or_authority_change_after_render_withholds_response(self):
        self.seed()
        for mode in ('source', 'authority'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_life_process.py')),
                    str(self.fixture.configuration.path), mode, '/api/life/finances'], capture_output=True, text=True,
                    timeout=40, env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_jsonl_malformed_first_line_keeps_native_header_position(self):
        self.seed()
        self.statement.write_text('synthetic malformed json\n' + self.statement.read_text() + '{bad json\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/life/finances'))
            self.assertIsNone(response.json()['insights']['statement_spend']['generated_at'])

    def test_foreign_origin_invalid_bearer_selector_and_method_refuse(self):
        self.seed()
        with httpx.Client(timeout=25) as client:
            self.login(client)
            for method, suffix, headers, status in (
                ('GET', '', {'Origin': 'https://outside.invalid'}, 403),
                ('GET', '', {'Authorization': 'Bearer synthetic-invalid'}, 401),
                ('GET', '?source=other', {}, 400),
                ('POST', '', {}, 405),
            ):
                with self.subTest(method=method, suffix=suffix, headers=headers):
                    response = client.request(method, self.native + '/api/life/finances' + suffix, headers=headers)
                    self.assertEqual(response.status_code, status, response.text)
                    self.assertNotIn('SyntheticAccount', response.text)

    def test_decoded_private_currency_cannot_return_from_configuration(self):
        self.seed()
        config = self.root / 'LIFEOS/USER/CONFIG/LIFEOS_CONFIG.toml'
        config.write_text('[principal]\nname="SyntheticOwner"\ntimezone="UTC"\n'
            'currency="\\u003cprivate\\u003eSyntheticPrivateCurrency\\u003c/private\\u003e"\n'
            '[da]\nname="SyntheticAssistant"\n[da.voices.main]\nvoice_id="synthetic-voice"\n')
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticPrivateCurrency', response.text)
            self.assertEqual(response.json()['currency'], 'USD')

    def test_fixed_transaction_record_count_refuses_excess(self):
        self.seed()
        self.statement.write_text('{}\n' * 2050)
        with httpx.Client(timeout=25) as client:
            self.login(client)
            response = self.get(client)
            self.assertEqual(response.status_code, 503, response.text)


if __name__ == '__main__':
    unittest.main()
