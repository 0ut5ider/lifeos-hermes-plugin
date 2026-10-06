# ABOUTME: Provides a real HTTP document corpus through Hermes's web provider interface.
# ABOUTME: Runs actual web tools and a private-model conversation with installed hook middleware.

from html.parser import HTMLParser
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

from agent.web_search_provider import WebSearchProvider


class TextPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


class DocumentProvider(WebSearchProvider):
    name = 'fixture-documents'

    def is_available(self):
        return bool(os.environ.get('PAIR_DOCUMENT_URL'))

    def supports_extract(self):
        return True

    def search(self, query, limit=5):
        with urlopen(os.environ['PAIR_DOCUMENT_URL'] + '/search?' + urlencode({'q': query}), timeout=5) as response:
            documents = json.load(response)
        return {'success': True, 'data': {'web': documents[:limit]}}

    def extract(self, urls, **kwargs):
        data = []
        for url in urls:
            with urlopen(url, timeout=5) as response:
                html = response.read().decode()
            parser = TextPage()
            parser.feed(html)
            data.append({'url': url, 'title': 'Fixture document', 'content': '\n'.join(parser.parts),
                         'raw_content': html})
        return data


if __name__ == '__main__':
    from hermes_cli.plugins import discover_plugins, unload_plugins
    from agent.web_search_registry import register_provider
    from hermes_cli.lifecycle import finalize_session
    from run_agent import AIAgent

    profile = Path(os.environ['HERMES_HOME'])
    configuration = json.loads((profile / 'config.yaml').read_text())
    configuration['web'] = {'backend': 'fixture-documents', 'keyless_fallback': False}
    (profile / 'config.yaml').write_text(json.dumps(configuration))
    discover_plugins()
    register_provider(DocumentProvider())
    model = configuration['model']
    agent = AIAgent(api_key=model['api_key'], base_url=model['base_url'], provider='custom',
                    api_mode='chat_completions', model=model['default'], enabled_toolsets=['web'],
                    quiet_mode=True, platform='cli', max_iterations=4, skip_memory=True,
                    skip_background_review=True, ephemeral_system_prompt=os.environ['HERMES_EPHEMERAL_SYSTEM_PROMPT'])
    try:
        result = agent.run_conversation(sys.argv[1])
        for message in result.get('messages', []):
            if message.get('role') == 'tool':
                print(json.dumps({'type': 'fixture-tool-result', 'content': message.get('content')}))
        print(json.dumps({'type': 'result', 'text': result.get('final_response', '')}))
    finally:
        finalize_session(session_id=agent.session_id, reason='prompt_input_exit', platform='cli')
        agent.close()
        unload_plugins()
