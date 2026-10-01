     1	# ABOUTME: Previews native source adoption and records approved identities without copying facts.
     2	# ABOUTME: Rejects changed previews and preserves native history and forgotten source exclusions.
     3	from __future__ import annotations
     4	
     5	from datetime import datetime, timezone
     6	import json
     7	from pathlib import Path
     8	import re
     9	from typing import Any
    10	from uuid import uuid4
    11	
    12	from .memory_access import HOT_FILES, MemoryUnavailable, _claim_digest, _claim_words, _digest, _now
    13	from .memory_policy import CATEGORIES, MemoryScope
    14	from .memory_proposals import QUEUE
    15	
    16	
    17	def _owner(scope: MemoryScope) -> bool:
    18	    return bool(scope.principal) and CATEGORIES <= set(scope.read) and CATEGORIES <= set(scope.write) and '*' in scope.projects
    19	
    20	
    21	def _body_source(text: str, discovered: str) -> tuple[int, str]:
    22	    frontmatter = re.match(r'^---\n[\s\S]*?\n---', text)
    23	    start = frontmatter.end() if frontmatter else 0
    24	    raw = text[start:]
    25	    expected = raw.strip() if frontmatter else raw
    26	    if expected != discovered:
    27	        raise MemoryUnavailable('Native discovery changed its source body')
    28	    start += len(raw) - len(raw.lstrip('\r\n'))
    29	    return start, text[start:].rstrip('\r\n')
    30	
    31	
    32	def _sections(text: str, discovered: str) -> list[tuple[int, str]]:
    33	    start, body = _body_source(text, discovered)
    34	    initial = re.match(r'^# [^\n]+\n(?:[ \t]*\n)+', body)
    35	    cursor = initial.end() if initial else 0
    36	    markers = list(re.finditer(r'^## Appended [^\n]+\n<!-- source_session: [^\n]+ -->\n(?:[ \t]*\n)+', body, re.MULTILINE))
    37	    sections = []
    38	    for marker in markers:
    39	        content = body[cursor:marker.start()].strip('\r\n')
    40	        if content.strip():
    41	            offset = body.find(content, cursor, marker.start())
    42	            sections.append((start + offset, content))
    43	        cursor = marker.end()
    44	    content = body[cursor:].strip('\r\n')
    45	    if content.strip():
    46	        sections.append((start + body.find(content, cursor), content))
    47	    return sections
    48	
    49	
    50	def _snapshot(memory, connection, scope: MemoryScope) -> dict[str, Any]:
    51	    records = [dict(row) for row in connection.execute('SELECT * FROM records ORDER BY id')]
    52	    proposals = [dict(row) for row in connection.execute('SELECT * FROM proposals ORDER BY id')]
    53	    paths: dict[str, str] = {}
    54	    candidates, pending, excluded, items = [], [], [], []
    55	
    56	    def add(path: str, position: int, content: str, category: str, kind: str, item: dict[str, Any]) -> None:
    57	        existing = [row for row in records if row['path'] == path and row['digest'] == _digest(content)]
    58	        if existing:
    59	            return
    60	        if memory._blocked(connection,content):
    61	            excluded.append({'path':path,'reason':'This retained claim requires explicit reactivation'})
    62	            return
    63	        timestamp = (datetime.fromtimestamp(memory._path(path).stat().st_mtime,timezone.utc).isoformat()
    64	                     if kind == 'learning' else _now())
    65	        if memory._filter_history(connection,scope,content,timestamp)['excluded']:
    66	            excluded.append({'path':path,'reason':'This source predates a correction or contains a removed claim'})
    67	            return
    68	        candidates.append({'path':path,'position':position,'content':content,'category':category,
    69	                           'source_kind':kind,'project':''})
    70	        items.append(item)
    71	
    72	    for category, relative in HOT_FILES.items():
    73	        path = memory._path(relative)
    74	        if not path.is_file():
    75	            continue
    76	        text = path.read_text()
    77	        paths[relative] = _digest(text)
    78	        native = memory._native('read_hot',path=str(path))
    79	        begin_marker, end_marker = '<!-- BEGIN ENTRIES -->', '<!-- END ENTRIES -->'
    80	        if ('entries' not in native or native.get('dropped_invalid')
    81	                or text.count(begin_marker) != 1 or text.count(end_marker) != 1
    82	                or text.find(begin_marker) >= text.find(end_marker)):
    83	            excluded.append({'path':relative,'reason':'The native hot-memory file needs repair'})
    84	            continue
    85	        start = text.index('<!-- BEGIN ENTRIES -->') + len('<!-- BEGIN ENTRIES -->')
    86	        end = text.index('<!-- END ENTRIES -->',start)
    87	        for content in native['entries']:
    88	            position = text.find(content,start,end)
    89	            if position < 0:
    90	                raise MemoryUnavailable('Native hot-memory entries do not match the source file')
    91	            add(relative,position,content,category,'adopted',{'type':'memory','actor':category,'content':content})
    92	
    93	    for note in memory._native('discover')['notes']:
    94	        if note['noteClass'] == 'memory':
    95	            continue
    96	        relative = Path(note['filePath']).relative_to(memory.root).as_posix()
    97	        if not relative.startswith(('LIFEOS/MEMORY/KNOWLEDGE/','LIFEOS/MEMORY/LEARNING/')):
    98	            raise MemoryUnavailable('Native discovery returned an unsupported source')
    99	        path = memory._path(relative)
   100	        text = path.read_text()
   101	        paths[relative] = _digest(text)
   102	        if not note['body']:
   103	            continue
   104	        kind = 'learning' if note['noteClass'] == 'learning' else 'adopted'
   105	        sections = [_body_source(text,note['body'])] if kind == 'learning' else _sections(text,note['body'])
   106	        for position, content in sections:
   107	            if position < 0:
   108	                raise MemoryUnavailable('Native discovery changed a learning source')
   109	            add(relative,position,content,'project',kind,{'type':'idea','title':'Native source adoption','content':content})
   110	
   111	    if items:
   112	        checked = memory._native('validate_batch',items=items)['results']
   113	        accepted = []
   114	        for candidate, item, result in zip(candidates,items,checked,strict=True):
   115	            if result.get('ok') and result.get('item') == item:
   116	                accepted.append(candidate)
   117	            else:
   118	                excluded.append({'path':candidate['path'],'reason':'Native validation rejected this source text'})
   119	        candidates = accepted
   120	
   121	    queue = memory._path(QUEUE)
   122	    if queue.is_file():
   123	        text = queue.read_text()
   124	        paths[QUEUE] = _digest(text)
   125	        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
   126	        identifiers = set()
   127	        for row in rows:
   128	            identifier = row.get('id')
   129	            if not isinstance(identifier,str) or not identifier or identifier in identifiers or '/' in identifier or '..' in identifier:
   130	                raise MemoryUnavailable('The native queue has invalid or duplicate proposal references')
   131	            identifiers.add(identifier)
   132	            if any(record['id'] == identifier for record in proposals):
   133	                continue
   134	            if row.get('status') not in ('pending','sent'):
   135	                continue
   136	            try:
   137	                item = {key:row[key] for key in ('target_file','edit','confidence','rationale')}
   138	                item.update(type='proposal',target_kind=row.get('target_kind','identity'))
   139	                result = memory._native('validate',item=item)
   140	                if not result.get('ok') or result.get('item') != item:
   141	                    raise ValueError('Native validation rejected this proposal')
   142	                target = Path(row['target_file'])
   143	                if not target.is_absolute():
   144	                    target = memory.root / target
   145	                relative = target.relative_to(memory.root).as_posix()
   146	                target = memory._path(relative)
   147	                if not target.is_file() or memory._blocked(connection,row['edit']):
   148	                    raise ValueError('The proposal target is missing or the claim requires reactivation')
   149	                paths[relative] = _digest(target.read_text())
   150	                pending.append({'reference':{'id':identifier,'revision':1},'row':row,
   151	                                'target':relative,'target_digest':paths[relative]})
   152	            except (KeyError, ValueError, MemoryUnavailable) as error:
   153	                excluded.append({'path':QUEUE,'reference':identifier,'reason':str(error)})
   154	
   155	    signature = _digest(json.dumps({'root':str(memory.root),'principal':scope.principal,
   156	                                     'files':paths,'mtimes':{name:memory._path(name).stat().st_mtime_ns for name in paths},
   157	                                     'records':records,'proposals':proposals,'candidates':candidates,
   158	                                     'pending':pending,'excluded':excluded},sort_keys=True))
   159	    return {'signature':signature,'records':candidates,'proposals':pending,'excluded':excluded,'scanned_files':len(paths)}
   160	
   161	
   162	def preview(memory, scope: MemoryScope) -> dict[str, Any]:
   163	    if not _owner(scope):
   164	        raise MemoryUnavailable('Native source adoption requires an unrestricted owner context')
   165	    with memory._transaction() as connection:
   166	        return _snapshot(memory,connection,scope)
   167	
   168	
   169	def adopt(memory, scope: MemoryScope, signature: str, projects: dict[str,str], request_id: str) -> dict[str, Any]:
   170	    if not _owner(scope):
   171	        return {'status':'rejected','reason':'Native source adoption requires an unrestricted owner context'}
   172	    if (not isinstance(signature,str) or not re.fullmatch(r'[0-9a-f]{64}',signature)
   173	            or not isinstance(projects,dict) or any(not isinstance(path,str) or not isinstance(project,str)
   174	                                                    or not project.strip() or project == '*' for path,project in projects.items())):
   175	        return {'status':'rejected','reason':'An exact native source preview and project assignments are required'}
   176	
   177	    def apply(connection):
   178	        snapshot = _snapshot(memory,connection,scope)
   179	        if snapshot['signature'] != signature:
   180	            return {'status':'conflict','reason':'The native source preview changed. Review a fresh preview before adoption.'}
   181	        eligible = {row['path'] for row in snapshot['records'] if row['category']=='project'}
   182	        if set(projects)-eligible:
   183	            return {'status':'rejected','reason':'Project assignments must name a previewed native archive or learning file'}
   184	        references = []
   185	        for row in snapshot['records']:
   186	            identifier = uuid4().hex
   187	            content = row['content']
   188	            connection.execute('INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(
   189	                identifier,row['path'],row['category'],projects.get(row['path'],''),_digest(content),len(content),
   190	                row['position'],1,'active','native:unattributed','',row['source_kind'],_now(),
   191	                _claim_digest(content),len(_claim_words(content))))
   192	            references.append({'id':identifier,'revision':1})
   193	        for item in snapshot['proposals']:
   194	            row = item['row']
   195	            connection.execute('INSERT INTO proposals VALUES (?,?,?,?,?,?,?,?,?,?)',(
   196	                row['id'],QUEUE,item['target'],item['target_digest'],_digest(json.dumps(row,sort_keys=True)),
   197	                1,'pending','native:unattributed','',_now()))
   198	        return {'status':'committed','facts_adopted':len(references),'proposals_adopted':len(snapshot['proposals']),
   199	                'references':references,'excluded_sources':len(snapshot['excluded']),'native_files_changed':False}
   200	
   201	    return memory._operation(scope,request_id,{'operation':'adopt','signature':signature,'projects':projects},apply)
