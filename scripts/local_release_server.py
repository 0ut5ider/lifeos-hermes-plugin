# ABOUTME: Serves one locally built integration release through a loopback imitation of the GitHub release API.
# ABOUTME: Lets qualification exercise the real catalog download path before anything is published.
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path

# Qualification copies this script to a test host without the plugin package, so it keeps its own copy;
# tests/test_local_release_server.py requires it to equal release_catalog.REPOSITORY.
REPOSITORY = '0ut5ider/lifeos-hermes-plugin'


def payloads(directory, tag, origin):
    """Return the URL path to response bytes map for the release in ``directory``."""
    assets, served = [], {}
    for path in sorted(Path(directory).iterdir()):
        if not path.is_file():
            continue
        data = path.read_bytes()
        route = '/' + REPOSITORY + '/releases/download/' + tag + '/' + path.name
        served[route] = data
        assets.append({'name': path.name, 'size': len(data), 'digest': 'sha256:' + hashlib.sha256(data).hexdigest(),
                       'browser_download_url': origin + route})
    release = json.dumps({'tag_name': tag, 'draft': False, 'prerelease': False, 'assets': assets}).encode()
    served['/repos/' + REPOSITORY + '/releases/latest'] = release
    served['/repos/' + REPOSITORY + '/releases/tags/' + tag] = release
    return served


def main():
    parser = argparse.ArgumentParser(description='Serve one local integration release through a loopback imitation of the GitHub release API.')
    parser.add_argument('--directory', type=Path, required=True, help='Directory with the certificate and archive.')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--port', type=int, default=8765)
    arguments = parser.parse_args()
    origin = 'http://127.0.0.1:' + str(arguments.port)
    served = payloads(arguments.directory, arguments.tag, origin)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            data = served.get(self.path)
            if data is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    ThreadingHTTPServer(('127.0.0.1', arguments.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
