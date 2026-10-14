# ABOUTME: Forgets only the synthetic promotion fact through the authenticated installation owner API.
# ABOUTME: Confirms the exact reference revision and an empty ordinary search without reading memory files.
import json
from pathlib import Path
import httpx

home = Path('/home/lifeos-hermes')
reference = {'id': '8565b850a9ce45a18f4c0540e398b5ee', 'revision': 1}
credentials = json.loads((home / 'install-input/dashboard-access.json').read_bytes())
with httpx.Client(base_url='http://127.0.0.1:18819', timeout=60) as client:
    login = client.post('/auth/password-login', json={'provider': 'basic', **credentials})
    assert login.status_code == 200
    me = client.get('/api/auth/me')
    assert me.status_code == 200 and me.json()['provider'] == 'basic' and me.json()['user_id'] == 'adrian'
    def tool(name, arguments):
        response = client.post('/api/plugins/lifeos-hook-bridge/memory/review',
            headers={'X-Hermes-Profile': 'default'}, json={'tool': name, 'arguments': arguments})
        assert response.status_code == 200
        return response.json()
    before = tool('lifeos_memory_search', {'query': 'D253-042-PROMOTION-1014'})
    assert before['status'] == 'ok' and len(before['results']) == 1
    assert before['results'][0]['reference'] == reference
    result = tool('lifeos_memory_forget', {'reference': reference, 'request_id': 'daily-043-promotion-cleanup-1014'})
    assert result['status'] == 'committed' and result['reference'] == {'id': reference['id'], 'revision': 2}
    after = tool('lifeos_memory_search', {'query': 'D253-042-PROMOTION-1014'})
    assert after == {'status': 'ok', 'results': []}
print(json.dumps({'status': 'PASS', 'authenticated_owner_verified': True,
    'synthetic_reference': result['reference'], 'cleanup_status': 'committed',
    'post_cleanup_search_results': 0, 'only_synthetic_acceptance_fact_targeted': True,
    'personal_data_imported_or_reset': False}, indent=2))
