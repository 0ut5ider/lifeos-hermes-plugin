# ABOUTME: Review probe that checks whether a refused Discord redirect response stays open.
# ABOUTME: Uses a real local HTTP server and the PR34 audience client.
import gc, http.server, sys, threading, warnings
sys.path.insert(0, '/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
from lifeos_hook_bridge import discord_audience
from lifeos_hook_bridge.discord_audience import DiscordAPI

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(302); self.send_header('Location', '/elsewhere')
        self.send_header('Content-Length', '0'); self.end_headers()
    def log_message(self, *a): pass

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
seen = []
original = discord_audience._RefuseRedirects.redirect_request
def spy(self, request, response, *rest):
    seen.append(response)
    return original(self, request, response, *rest)
discord_audience._RefuseRedirects.redirect_request = spy
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    try:
        DiscordAPI('synthetic-token', origin=f'http://127.0.0.1:{server.server_port}').get('/users/@me')
    except Exception as error:
        print('raised', type(error).__name__, error)
    print('redirect response closed before GC:', seen[0].fp is None or seen[0].fp.closed if seen else 'n/a')
    del seen[:]; gc.collect()
print('resource warnings:', [str(w.message)[:120] for w in caught if issubclass(w.category, ResourceWarning)])
server.shutdown(); server.server_close()
