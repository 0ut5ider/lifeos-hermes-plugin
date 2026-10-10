# ABOUTME: Verifies native digest URLs against the actual returned public web tool results.
# ABOUTME: Retains extraction component evidence separately from complete refresh acceptance.
import gzip
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
budget = root / 'local-job-research-public-budget.json'
raw = budget.read_bytes()
value = json.loads(raw)
if 'raw_record' in value:
    raw = gzip.decompress((root / value['raw_record']).read_bytes())
    value = json.loads(raw)
content = '\n'.join(result['content'] for request in value['wire_requests']
    for result in request.get('tool_results', []))
missing = [item['url'] for item in value['item_sources'] if item['url'] not in content]
assert value['status'] == 'PASS' and value['item_sources'] and not missing
prior = root / 'local-job-research-public-after.json.raw.gz'
prior_raw = gzip.decompress(prior.read_bytes())
observation = json.loads(prior_raw)
unique = {result['call_id']: result['content'] for request in observation['wire_requests']
    for result in request.get('tool_results', [])}
extractions = []
for identifier, returned in unique.items():
    if 'source="web_extract"' not in returned:
        continue
    parsed = json.loads(returned[returned.index('\n{') + 1:returned.rindex('}') + 1])
    extractions.append({'call_id': identifier, 'pages': [{'url': page['url'],
        'error': page.get('error'), 'content_characters': len(page.get('content', ''))}
        for page in parsed['results']]})
assert len(extractions) == 2
assert all(page['error'] is None and page['content_characters'] > 0
    for call in extractions for page in call['pages'])
record = {'status': 'PASS', 'refresh_raw_sha256': hashlib.sha256(raw).hexdigest(),
    'published_items': len(value['item_sources']), 'urls_absent_from_returned_tools': missing,
    'extraction_raw_sha256': hashlib.sha256(prior_raw).hexdigest(),
    'extraction_probe_full_refresh_status': observation['status'],
    'extraction_component_only': True, 'actual_extractions': extractions,
    'limits': 'URL presence verifies source retrieval. It does not independently validate every summarized factual claim.'}
(root / 'local-research-returned-sources.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({key: record[key] for key in ('status', 'published_items', 'urls_absent_from_returned_tools')}))
