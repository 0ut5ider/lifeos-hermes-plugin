# ABOUTME: Verifies private Discord audience admission through an actual local HTTP API fixture.
# ABOUTME: Covers permission overrides, administrators, unbound destinations, and changing readers.
import copy
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from lifeos_hook_bridge.memory_context import host_context


class DiscordAudienceTests(unittest.TestCase):
    def setUp(self):
        self.responses = {
            '/guilds/10': {'id': '10', 'owner_id': '20'},
            '/guilds/10/roles': [{'id': '10', 'permissions': '1024'}, {'id': '50', 'permissions': '8'}],
            '/guilds/10/members?limit=1000': [
                {'user': {'id': '20'}, 'roles': []},
                {'user': {'id': '30'}, 'roles': []},
                {'user': {'id': '40'}, 'roles': []}],
            '/channels/60': {'id': '60', 'guild_id': '10', 'type': 0, 'permission_overwrites': [
                {'id': '10', 'type': 0, 'allow': '0', 'deny': '1024'},
                {'id': '20', 'type': 1, 'allow': '1024', 'deny': '0'},
                {'id': '30', 'type': 1, 'allow': '1024', 'deny': '0'}]},
            '/users/@me': {'id': '30', 'bot': True},
        }
        self.requests = []
        self.deliveries = []
        self.on_delivery = None
        self.redirects = {}
        self.on_request = None
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.deliver()

            def do_PATCH(self):
                self.deliver()

            def deliver(self):
                self.assert_authorization()
                length = int(self.headers.get('Content-Length', '0'))
                data = self.rfile.read(length)
                attachments = []
                if self.headers.get('Content-Type','').startswith('multipart/'):
                    message = BytesParser(policy=default).parsebytes(
                        ('Content-Type: '+self.headers['Content-Type']+'\r\n\r\n').encode()+data)
                    payload = {}
                    for part in message.iter_parts():
                        if part.get_param('name',header='content-disposition') == 'payload_json':
                            payload = json.loads(part.get_payload(decode=True))
                        elif part.get_filename():
                            attachments.append({'id':str(len(attachments)+1),'filename':part.get_filename(),
                                'size':len(part.get_payload(decode=True)), 'url':'https://synthetic.invalid/file',
                                'proxy_url':'https://synthetic.invalid/file'})
                else:
                    payload = json.loads(data)
                fixture.deliveries.append({'method':self.command, 'path':self.path, 'payload':payload})
                body = {'id':str(100000000000000000+len(fixture.deliveries)), 'channel_id':'60',
                    'type':0, 'author':{'id':'30','username':'SyntheticBot','discriminator':'0000',
                        'avatar':None,'bot':True}, 'content':payload.get('content',''), 'mentions':[],
                    'mention_roles':[], 'attachments':attachments, 'embeds':payload.get('embeds',[]),
                    'flags':0,'pinned':False,'tts':False,
                    'timestamp':'2026-10-08T13:00:00+00:00','edited_timestamp':None}
                if fixture.on_delivery is not None:
                    fixture.on_delivery()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def do_GET(self):
                fixture.requests.append(self.path)
                self.assert_authorization()
                if fixture.on_request is not None:
                    fixture.on_request(self.path)
                if self.path in fixture.redirects:
                    self.send_response(302)
                    self.send_header('Location', fixture.redirects[self.path])
                    self.end_headers()
                    return
                body = fixture.responses.get(self.path)
                self.send_response(200 if body is not None else 404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def assert_authorization(self):
                if self.headers.get('Authorization') != 'Bot synthetic-token':
                    raise AssertionError('The API request lacks its bot authentication')

            def log_message(self, *_):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(thread.join, 3)
        self.addCleanup(self.server.shutdown)
        self.origin = 'http://127.0.0.1:' + str(self.server.server_port)
        self.configuration = {'version': 1, 'principal': 'owner', 'accounts': {'discord:20': 'owner'},
            'discord_channels': {'60': {'guild': '10', 'owner': '20', 'bot': '30'}},
            'destinations': {'discord:60': {'visibility': 'private', 'participants': ['owner'],
                'read': ['principal', 'assistant', 'project'], 'write': ['project'], 'model_routes': ['local']}}}
        self.metadata = {'HERMES_SESSION_PLATFORM': 'discord', 'HERMES_SESSION_USER_ID': '20',
            'HERMES_SESSION_CHAT_ID': '60', 'HERMES_SESSION_CHAT_TYPE': 'group',
            'HERMES_SESSION_SCOPE_ID': '10', 'HERMES_SESSION_ID': 'synthetic-session'}

    def context(self):
        from lifeos_hook_bridge.discord_audience import DiscordAPI, resolve_audience
        api = DiscordAPI('synthetic-token', origin=self.origin)
        return host_context(self.configuration, self.metadata, model_route='local', hermes_home='/synthetic/profile',
            audience_lookup=lambda configuration, metadata: resolve_audience(configuration, metadata, api=api))

    def test_only_the_owner_and_selected_bot_can_read_the_channel(self):
        context = self.context()
        self.assertEqual(context.visibility, 'private')
        self.assertEqual(context.participants, ('owner',))
        self.assertEqual(len(self.requests), 5)

    def test_another_member_administrator_or_everyone_reader_refuses_private_memory(self):
        original = copy.deepcopy(self.responses)
        for mode in ('member', 'administrator', 'everyone', 'role'):
            with self.subTest(mode=mode):
                self.responses = copy.deepcopy(original)
                channel = self.responses['/channels/60']
                if mode == 'member':
                    channel['permission_overwrites'].append({'id':'40','type':1,'allow':'1024','deny':'0'})
                elif mode == 'administrator':
                    self.responses['/guilds/10/members?limit=1000'][2]['roles'] = ['50']
                elif mode == 'everyone':
                    channel['permission_overwrites'][0] = {'id':'10','type':0,'allow':'1024','deny':'0'}
                else:
                    channel['permission_overwrites'].append({'id':'50','type':0,'allow':'1024','deny':'0'})
                    self.responses['/guilds/10/roles'][1]['permissions'] = '0'
                    self.responses['/guilds/10/members?limit=1000'][2]['roles'] = ['50']
                self.assertEqual(self.context().visibility, 'unknown')

    def test_permissions_are_read_again_after_a_channel_change(self):
        self.assertEqual(self.context().visibility, 'private')
        self.responses['/channels/60']['permission_overwrites'].append(
            {'id':'40','type':1,'allow':'1024','deny':'0'})
        self.assertEqual(self.context().visibility, 'unknown')
        self.assertEqual(len(self.requests), 10)

    def test_member_view_denial_overrides_a_role_view_allow(self):
        self.responses['/guilds/10/roles'][1]['permissions'] = '0'
        self.responses['/guilds/10/members?limit=1000'][2]['roles'] = ['50']
        self.responses['/channels/60']['permission_overwrites'].extend([
            {'id':'50','type':0,'allow':'1024','deny':'0'},
            {'id':'40','type':1,'allow':'0','deny':'1024'}])
        self.assertEqual(self.context().visibility, 'private')

    def test_all_member_pages_are_checked_and_repeated_members_refuse(self):
        page = self.responses['/guilds/10/members?limit=1000']
        page.extend({'user':{'id':str(identifier)},'roles':[]} for identifier in range(100,1097))
        self.assertEqual(len(page), 1000)
        self.responses['/guilds/10/members?limit=1000&after=1096'] = [
            {'user':{'id':'2000'},'roles':['50']}]
        self.assertEqual(self.context().visibility, 'unknown')
        self.assertIn('/guilds/10/members?limit=1000&after=1096', self.requests)
        self.responses['/guilds/10/members?limit=1000&after=1096'] = [
            {'user':{'id':'20'},'roles':[]}]
        self.assertEqual(self.context().visibility, 'unknown')

    def test_another_guild_author_channel_or_thread_never_borrows_the_binding(self):
        original = dict(self.metadata)
        for field, value in [('HERMES_SESSION_SCOPE_ID','99'), ('HERMES_SESSION_USER_ID','40'),
                ('HERMES_SESSION_CHAT_ID','99'), ('HERMES_SESSION_THREAD_ID','70')]:
            with self.subTest(field=field):
                self.metadata = {**original, field:value}
                self.assertEqual(self.context().visibility, 'unknown')
        self.assertEqual(self.requests, [])

    def test_lost_access_wrong_bot_and_changed_server_owner_refuse(self):
        original = copy.deepcopy(self.responses)
        for path, value in [('/channels/60', None), ('/users/@me', {'id':'99','bot':True}),
                ('/guilds/10', {'id':'10','owner_id':'40'})]:
            with self.subTest(path=path):
                self.responses = copy.deepcopy(original)
                self.responses[path] = value
                self.assertEqual(self.context().visibility, 'unknown')

    def test_bot_requests_refuse_redirects_without_forwarding_the_credential(self):
        self.redirects['/users/@me'] = self.origin + '/redirect-target'
        self.responses['/redirect-target'] = {'id': '30', 'bot': True}
        self.assertEqual(self.context().visibility, 'unknown')
        self.assertEqual(self.requests, ['/users/@me'])

    def test_invalid_channel_bindings_refuse_without_network_requests(self):
        for binding in ([], None, {'owner': '20'}, {'guild':'9' * 5000,'owner':'20','bot':'30'}):
            with self.subTest(binding_type=type(binding).__name__):
                self.configuration['discord_channels']['60'] = binding
                self.assertEqual(self.context().visibility, 'unknown')
        self.assertEqual(self.requests, [])

    def test_binding_validation_bounds_identifiers_before_numeric_conversion(self):
        from lifeos_hook_bridge.discord_audience import validate_bindings
        self.configuration['discord_channels']['9' * 5000] = {'guild':'10','owner':'20','bot':'30'}
        with self.assertRaisesRegex(ValueError, 'numeric guild, owner, and bot'):
            validate_bindings(self.configuration)

    def test_native_process_uses_its_exported_bot_credential_without_importing_hermes(self):
        import lifeos_hook_bridge.discord_audience as module
        source = '''
import importlib.util, os, sys
spec=importlib.util.spec_from_file_location('audience',sys.argv[1])
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
print(module._bot_token() == 'synthetic-token')
'''
        environment = dict(os.environ, DISCORD_BOT_TOKEN='synthetic-token', PYTHONPATH='')
        result = subprocess.run([sys.executable, '-I', '-c', source, module.__file__],
            env=environment, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.stdout, 'True\n')

    @unittest.skipUnless(shutil.which('bun'), 'Native LifeOS tools require Bun')
    def test_resumed_model_and_native_tools_recheck_channel_permissions(self):
        from dataclasses import asdict
        from lifeos_hook_bridge.discord_audience import DiscordAPI, resolve_audience
        from lifeos_hook_bridge.memory_context import route_identity
        from lifeos_hook_bridge.memory_runtime import MemoryRuntime, MemoryAdmissionError
        from lifeos_hook_bridge.memory_service import MemoryConfiguration, MemoryService
        import test_memory_native as native_fixture

        fixture = native_fixture.NativeMemoryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        path = fixture.home / 'hermes/lifeos-memory.json'
        route = dict(provider='synthetic', model='synthetic-model', base_url=self.origin + '/v1',
                     api_mode='chat_completions')
        configuration = copy.deepcopy(self.configuration)
        configuration.update(root=str(fixture.root), ownership_enabled=True, sharing_enabled=False, clients={})
        configuration['destinations']['discord:60'].update(projects=['*'], model_routes=[route_identity(**route)])
        MemoryConfiguration(path).save(configuration)
        markers = fixture.root / 'LIFEOS/USER/CONFIG'
        markers.mkdir(parents=True)
        (markers / 'memory-http.json').write_text('{}')
        api = DiscordAPI('synthetic-token', origin=self.origin)
        lookup = lambda configuration, metadata: resolve_audience(configuration, metadata, api=api)
        runtime = MemoryRuntime(path, audience_lookup=lookup)
        self.addCleanup(runtime.clear)
        runtime.admit(self.metadata, **route, is_first_turn=True)
        context = runtime.context()
        service = MemoryService(MemoryConfiguration(path), audience_lookup=lookup)
        self.assertEqual(service.call_context(context, 'lifeos_memory_search', {'query':'synthetic'})['status'], 'ok')
        def open_channel_after_the_first_permission_snapshot(path):
            if path == '/guilds/10/members?limit=1000':
                self.responses['/channels/60']['permission_overwrites'].append(
                    {'id':'40','type':1,'allow':'1024','deny':'0'})
                self.on_request = None
        self.on_request = open_channel_after_the_first_permission_snapshot
        withheld = service.call_context(context, 'lifeos_memory_search', {'query':'synthetic'})
        self.assertEqual(withheld['status'], 'unavailable')
        self.assertNotIn('results', withheld)
        self.responses['/channels/60']['permission_overwrites'].pop()
        runtime.clear()
        with patch.dict(os.environ, {'LIFEOS_MEMORY_CONTEXT':json.dumps(asdict(context))}):
            runtime.check_call(request={}, **route, session_id=context.session_id, metadata={})
            self.responses['/channels/60']['permission_overwrites'].append(
                {'id':'40','type':1,'allow':'1024','deny':'0'})
            with self.assertRaisesRegex(MemoryAdmissionError, 'Discord channel audience'):
                runtime.check_call(request={}, **route, session_id=context.session_id, metadata={})
        self.assertEqual(service.call_context(context, 'lifeos_memory_search', {'query':'synthetic'})['status'], 'unavailable')
        native = service.native(context, 'prompt_bundle', {'keepOutputFormat':True})
        self.assertFalse(native['ok'])
        self.assertNotIn('bundle', native)


if __name__ == '__main__':
    unittest.main()
