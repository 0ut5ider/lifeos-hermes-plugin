     1	# ABOUTME: Publishes native LifeOS proposals with distinct creation and approval permissions.
     2	# ABOUTME: Reports queued and diverted outcomes without treating a proposal as a saved current fact.
     3	from __future__ import annotations
     4	
     5	import json
     6	from pathlib import Path
     7	from typing import Any
     8	
     9	from .memory_access import MemoryUnavailable, _digest, _now
    10	from .memory_policy import CATEGORIES, MemoryScope
    11	
    12	QUEUE = 'LIFEOS/MEMORY/OBSERVABILITY/pending-proposals.jsonl'
    13	UPGRADES = 'LIFEOS/MEMORY/UPGRADES/records'
    14	
    15	
    16	def enqueue(memory, scope: MemoryScope, item: dict[str, Any], request_id: str,
    17	            source_session: str) -> dict[str, Any]:
    18	    if 'create' not in scope.proposals or not CATEGORIES <= set(scope.read) or '*' not in scope.projects:
    19	        return {'ok':False, 'code':'EINVAL_ITEM', 'message':'This context has no complete proposal creation grant'}
    20	    checked = memory._native('validate', item=item)
    21	    if not checked.get('ok') or checked.get('item') != item:
    22	        return {'ok':False, 'code':'EINVAL_ITEM', 'message':checked.get('message', 'Native validation changed the proposal')}
    23	
    24	    def save(connection):
    25	        if memory._blocked(connection, item["edit"]):
    26	            return {"status":"rejected", "reason":"This proposal needs explicit reactivation after correction or forgetting"}
    27	        result = memory._native('add', item=item)
    28	        if not result.get('ok'):
    29	            return {'status':'rejected', 'reason':result.get('message', 'Native proposal creation failed')}
    30	        identifier = result.get('detail', {}).get('id')
    31	        if not isinstance(identifier, str) or not identifier or '/' in identifier or '..' in identifier:
    32	            raise MemoryUnavailable('Native proposal creation did not return a bounded reference')
    33	        queue = memory._path(QUEUE)
    34	        rows = [json.loads(line) for line in queue.read_text().splitlines() if line.strip()] if queue.exists() else []
    35	        matches = [row for row in rows if row.get('id') == identifier]
    36	        if len(matches) == 1:
    37	            row = matches[0]
    38	            if row.get('edit') != item['edit'] or row.get('status') != 'pending':
    39	                raise MemoryUnavailable('Native proposal did not queue the requested pending edit')
    40	            target = Path(row['target_file'])
    41	            if not target.is_absolute():
    42	                target = memory.root / target
    43	            relative = target.relative_to(memory.root).as_posix()
    44	            memory._path(relative)
    45	            connection.execute('INSERT INTO proposals VALUES (?,?,?,?,?,?,?,?,?,?)',
    46	                               (identifier, QUEUE, relative, _digest(memory._path(relative).read_text()) if memory._path(relative).is_file() else '',
    47	                                _digest(json.dumps(row, sort_keys=True)),
    48	                                1, 'pending', scope.writer, source_session, _now()))
    49	            return {'status':'pending', 'proposal_reference':{'id':identifier, 'revision':1},
    50	                    'destination':str(queue), 'source':{'kind':'native-proposal', 'session':source_session},
    51	                    'detail':result['detail']}
    52	        if matches:
    53	            raise MemoryUnavailable('The native proposal reference is ambiguous')
    54	        destination = memory._path(UPGRADES + '/' + identifier + '.md')
    55	        if not destination.is_file():
    56	            raise MemoryUnavailable('Native proposal has neither a queued row nor an upgrade record')
    57	        text = destination.read_text()
    58	        claim = item['edit'].strip()[:1000]
    59	        if '\n## Claim\n\n' + claim + '\n' not in text:
    60	            raise MemoryUnavailable('Native upgrade diversion did not preserve the requested claim')
    61	        return {'status':'diverted', 'destination':str(destination), 'upgrade_id':identifier,
    62	                'source':{'kind':'native-proposal', 'session':source_session},
    63	                'reason':'Native LifeOS routed this change to an upgrade record; it is not a queued memory edit'}
    64	
    65	    receipt = memory._operation(scope, request_id, {'operation':'native_proposal', 'item':item,
    66	                                                   'source_session':source_session}, save)
    67	    if receipt['status'] not in ('pending', 'diverted'):
    68	        return {'ok':False, 'code':'EWRITE_FAILED', 'message':receipt.get('reason', 'Proposal did not publish'), 'receipt':receipt}
    69	    return {'ok':True, 'type':'proposal', 'path':receipt['destination'],
    70	            'detail':receipt.get('detail', {'id':receipt.get('upgrade_id'), 'status':'diverted'}), 'receipt':receipt}
    71	
    72	
    73	def _permitted(scope: MemoryScope, permission: str) -> bool:
    74	    return permission in scope.proposals and CATEGORIES <= set(scope.read) and '*' in scope.projects
    75	
    76	
    77	def _current_row(memory, record) -> dict[str, Any]:
    78	    path = memory._path(record['path'])
    79	    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    80	    matches = [row for row in rows if row.get('id') == record['id']]
    81	    if len(matches) != 1 or _digest(json.dumps(matches[0], sort_keys=True)) != record['digest']:
    82	        from .memory_access import MemoryConflict
    83	        raise MemoryConflict('The native proposal changed outside its recorded revision')
    84	    return matches[0]
    85	
    86	
    87	def review(memory, scope: MemoryScope, *, include_resolved: bool = False) -> list[dict[str, Any]]:
    88	    if not _permitted(scope, 'review'):
    89	        return []
    90	    with memory._transaction() as connection:
    91	        rows = connection.execute("SELECT * FROM proposals ORDER BY updated" if include_resolved else
    92	                                  "SELECT * FROM proposals WHERE status='pending' ORDER BY updated")
    93	        return [{**_current_row(memory, row), 'reference':{'id':row['id'], 'revision':row['revision']},
    94	                 'writer':row['writer'], 'source_session':row['source_session']}
    95	                for row in rows]
    96	
    97	
    98	def decision_row(memory, scope: MemoryScope, reference: dict[str, Any]) -> dict[str, Any]:
    99	    if not (_permitted(scope, 'approve') or _permitted(scope, 'auto_apply')):
   100	        raise MemoryUnavailable('This context cannot read a native proposal decision')
   101	    with memory._transaction() as connection:
   102	        record = connection.execute('SELECT * FROM proposals WHERE id=?', (reference['id'],)).fetchone()
   103	        if record is None or record['revision'] != reference['revision'] or record['status'] == 'pending':
   104	            raise MemoryUnavailable('The resolved native proposal revision is unavailable')
   105	        return _current_row(memory, record)
   106	
   107	
   108	def decide(memory, scope: MemoryScope, reference: dict[str, Any], decision: str,
   109	           request_id: str, *, content: str = "", note: str = "",
   110	           confidence_threshold: float | None = None) -> dict[str, Any]:
   111	    permission = 'auto_apply' if decision == 'auto_apply' else 'approve'
   112	    if not _permitted(scope, permission):
   113	        return {'status':'rejected', 'reason':'This context has no proposal approval grant'}
   114	    if (decision not in ('accept', 'reject', 'edit', 'applied_elsewhere', 'auto_apply') or not isinstance(reference, dict)
   115	            or set(reference) != {'id', 'revision'} or not isinstance(reference['id'], str)
   116	            or type(reference['revision']) is not int or reference['revision'] < 1):
   117	        return {'status':'rejected', 'reason':'An exact pending proposal reference and supported native decision are required'}
   118	
   119	    if (not isinstance(content, str) or not isinstance(note, str) or len(content) > 65536 or len(note) > 65536
   120	            or (decision == 'edit' and not content.strip()) or (decision == 'applied_elsewhere' and not note.strip())
   121	            or (decision != 'edit' and content) or (decision != 'applied_elsewhere' and note)
   122	            or (decision == 'auto_apply' and (type(confidence_threshold) not in (int, float) or not 0 <= confidence_threshold <= 1))
   123	            or (decision != 'auto_apply' and confidence_threshold is not None)):
   124	        return {'status':'rejected', 'reason':'The native proposal decision arguments are invalid'}
   125	
   126	    if note:
   127	        note_item = {'type':'idea', 'title':'Proposal resolution', 'content':note}
   128	        checked = memory._native('validate', item=note_item)
   129	        if not checked.get('ok') or checked.get('item') != note_item:
   130	            return {'status':'rejected', 'reason':'Native validation rejected the resolution note'}
   131	
   132	    def resolve(connection):
   133	        record = connection.execute('SELECT * FROM proposals WHERE id=?', (reference['id'],)).fetchone()
   134	        if record is None or record['status'] != 'pending' or record['revision'] != reference['revision']:
   135	            return {'status':'conflict', 'reason':'The proposal reference is no longer pending at this revision'}
   136	        row = _current_row(memory, record)
   137	        if decision in ('accept', 'edit', 'auto_apply'):
   138	            target = memory._path(record['target'])
   139	            if not target.is_file() or _digest(target.read_text()) != record['target_digest']:
   140	                return {'status':'conflict', 'reason':'The proposal target changed before approval'}
   141	            item = {'type':'proposal', 'target_file':row['target_file'], 'target_kind':row.get('target_kind', 'identity'),
   142	                    'edit':content if decision == 'edit' else row['edit'], 'confidence':row['confidence'], 'rationale':row['rationale']}
   143	            checked = memory._native('validate', item=item)
   144	            if not checked.get('ok') or checked.get('item') != item:
   145	                return {'status':'rejected', 'reason':'Native validation rejected the pending proposal'}
   146	            if memory._blocked(connection, item['edit']):
   147	                return {'status':'rejected', 'reason':'This proposal needs explicit reactivation after correction or forgetting'}
   148	        result = memory._native('proposal_decision', identifier=reference['id'], decision=decision, content=content,
   149	                                note=note, confidence_threshold=confidence_threshold)
   150	        if not result.get('ok'):
   151	            return {'status':'rejected', 'reason':result.get('reason', 'Native proposal decision failed')}
   152	        row = result['row']
   153	        expected = {'accept':'accepted', 'reject':'rejected', 'edit':'edited',
   154	                    'applied_elsewhere':'applied-elsewhere', 'auto_apply':'auto-applied'}[decision]
   155	        if row.get('status') != expected:
   156	            raise MemoryUnavailable('Native proposal decision returned a different lifecycle outcome')
   157	        connection.execute('UPDATE proposals SET digest=?,revision=revision+1,status=?,updated=? WHERE id=?',
   158	                           (_digest(json.dumps(row, sort_keys=True)), expected, _now(), record['id']))
   159	        return {'status':'committed', 'proposal_status':expected,
   160	                'proposal_reference':{'id':record['id'], 'revision':record['revision'] + 1},
   161	                'destination':str(memory._path(record['target'])), 'creator':record['writer']}
   162	
   163	    return memory._operation(scope, request_id, {'operation':'proposal_decision', 'reference':reference,
   164	                                                'decision':decision, 'content':content, 'note':note,
   165	                                                'confidence_threshold':confidence_threshold}, resolve)
