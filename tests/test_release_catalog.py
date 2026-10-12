# ABOUTME: Exercises published integration selection and bounded archive extraction.
# ABOUTME: Uses real HTTP responses and archives to test failure before installation changes.
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import tarfile
import tempfile
from threading import Thread
import unittest

from optional.lifeos_release_manager.release_catalog import ReleaseCatalog, ReleaseRejected, extract_package


class ReleaseCatalogTests(unittest.TestCase):
    def setUp(self):
        self.payloads = {}
        payloads = self.payloads
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                data = payloads.get(self.path)
                if data is None:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = Thread(target=self.server.serve_forever)
        self.thread.start()
        self.origin = 'http://127.0.0.1:' + str(self.server.server_port)
        self.catalog = ReleaseCatalog(api_origin=self.origin, asset_origin=self.origin)

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def release(self, **changes):
        archive = b'synthetic package'
        certificate = {'format': 1, 'status': 'QUALIFIED', 'version': '0.4.0',
            'program_commit': 'a' * 40, 'archive_sha256': hashlib.sha256(archive).hexdigest(),
            'archive_bytes': len(archive), 'hermes_dashboard_sha256': hashlib.sha256(b'dashboard').hexdigest()}
        def asset(name, data):
            path = '/0ut5ider/lifeos-hermes-plugin/releases/download/v0.4.0/' + name
            self.payloads[path] = data
            return {'name': name, 'size': len(data), 'digest': 'sha256:' + hashlib.sha256(data).hexdigest(),
                    'browser_download_url': self.origin + path}
        value = {'tag_name': 'v0.4.0', 'draft': False, 'prerelease': False, 'assets': [
            asset('0.4.0-aaaaaaaa.tgz', archive),
            asset('RELEASE-CERTIFICATE.json', json.dumps(certificate).encode()),
            asset('hermes-dashboard.tgz', b'dashboard')]}
        value.update(changes)
        self.payloads['/repos/0ut5ider/lifeos-hermes-plugin/releases/latest'] = json.dumps(value).encode()
        return value

    def test_qualified_release_downloads_exact_assets_without_selection(self):
        self.release()
        with tempfile.TemporaryDirectory() as temp:
            result = self.catalog.download(Path(temp) / 'download')
            self.assertEqual(result['certificate']['version'], '0.4.0')
            self.assertEqual(Path(result['archive']).read_bytes(), b'synthetic package')
            self.assertEqual(Path(result['dashboard']).read_bytes(), b'dashboard')
            self.assertFalse((Path(temp) / 'config.yaml').exists())

    def test_unqualified_or_ambiguous_release_refuses(self):
        value = self.release(draft=True)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ReleaseRejected):
                self.catalog.download(Path(temp) / 'draft')
            value['draft'] = False
            value['assets'].append(value['assets'][0])
            self.payloads['/repos/0ut5ider/lifeos-hermes-plugin/releases/latest'] = json.dumps(value).encode()
            with self.assertRaises(ReleaseRejected):
                self.catalog.download(Path(temp) / 'duplicate')

    def test_asset_corruption_refuses_and_does_not_publish_partial_asset(self):
        self.release()
        path = '/0ut5ider/lifeos-hermes-plugin/releases/download/v0.4.0/0.4.0-aaaaaaaa.tgz'
        self.payloads[path] = b'changed'
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ReleaseRejected):
                self.catalog.download(Path(temp) / 'corrupt')
            self.assertFalse((Path(temp) / 'corrupt/0.4.0-aaaaaaaa.tgz').exists())

    def test_foreign_asset_origin_and_repository_refuse(self):
        for url in ('https://evil.example/archive.tgz',
                    self.origin + '/another/repository/releases/download/v0.4.0/archive.tgz'):
            value = self.release()
            value['assets'][0]['browser_download_url'] = url
            self.payloads['/repos/0ut5ider/lifeos-hermes-plugin/releases/latest'] = json.dumps(value).encode()
            with tempfile.TemporaryDirectory() as temp, self.assertRaises(ReleaseRejected):
                self.catalog.download(Path(temp) / 'foreign')

    def test_extraction_rejects_traversal_links_duplicates_and_size_limit(self):
        for names, kind, limit in [(['../escaped'], tarfile.REGTYPE, 1024),
                                  (['link'], tarfile.SYMTYPE, 1024),
                                  (['a', 'a'], tarfile.REGTYPE, 1024),
                                  (['a'], tarfile.REGTYPE, 1)]:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                archive = root / 'package.tgz'
                with tarfile.open(archive, 'w:gz') as output:
                    for name in names:
                        item = tarfile.TarInfo(name)
                        item.type = kind
                        item.size = 2 if kind == tarfile.REGTYPE else 0
                        item.linkname = '/etc/passwd' if kind == tarfile.SYMTYPE else ''
                        output.addfile(item, io.BytesIO(b'ok') if item.size else None)
                with self.assertRaises(ReleaseRejected):
                    extract_package(archive, root / 'package', max_bytes=limit)
                self.assertFalse((root / 'package').exists())
                self.assertFalse((root / 'escaped').exists())

    def test_extraction_publishes_regular_files_with_executable_modes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / 'package.tgz'
            with tarfile.open(archive, 'w:gz') as output:
                item = tarfile.TarInfo('bin/run')
                item.size = 2
                item.mode = 0o755
                output.addfile(item, io.BytesIO(b'ok'))
            extract_package(archive, root / 'package')
            self.assertEqual((root / 'package/bin/run').read_bytes(), b'ok')
            self.assertEqual((root / 'package/bin/run').stat().st_mode & 0o777, 0o700)
