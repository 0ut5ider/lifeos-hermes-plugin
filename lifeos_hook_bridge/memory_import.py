# ABOUTME: Builds authenticated import reviews from one Hermes profile and governed native memory.
# ABOUTME: Preserves original bytes and source occurrences in private immutable review snapshots.
from contextlib import contextmanager, ExitStack
from dataclasses import replace
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import stat
import tempfile

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .installation_lock import installation_lock
from .memory_access import NativeMemory, MemoryUnavailable, MemoryConflict, HOT_FILES, _digest, _now
from .memory_backup import _directory, _read
from .memory_source_review import _retirement_digest
from .memory_preferences import MemoryPreferences
from .memory_policy import MemoryPolicy
from .memory_transaction import publish


SOURCE_NAMES = ('MEMORY.md', 'USER.md')
DELIMITER = '\n§\n'
SOURCE_LIMIT = 1024 * 1024
CHUNK_LIMIT = 10_000


def _encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode()


def _chunks(name, data):
    try:
        text = data.decode('utf-8-sig')
    except UnicodeError:
        return {'status':'invalid_encoding', 'byte_order_mark':False, 'chunks':[]}
    bom = data.startswith(b'\xef\xbb\xbf')
    offset = 3 if bom else 0
    pieces = re.split(r'((?:\r\n|\r|\n)§(?:\r\n|\r|\n))', text)
    parts = pieces[::2]
    separators = pieces[1::2]
    if len(parts) > CHUNK_LIMIT:
        raise MemoryUnavailable('The Hermes source exceeds its review occurrence limit')
    chunks, seen = [], {}
    source_digest = hashlib.sha256(data).hexdigest()
    for index, raw in enumerate(parts):
        normalized = raw.replace('\r\n', '\n').replace('\r', '\n')
        content = normalized.strip()
        separator = separators[index] if index < len(separators) else ''
        identifier = _digest(json.dumps([name, source_digest, index]))
        chunks.append({'id':identifier, 'ordinal':index, 'byte_start':offset,
            'byte_end':offset + len(raw.encode()), 'raw':raw, 'content':content,
            'separator_after':separator, 'disposition':'review' if content else 'empty',
            'normalization':'normalize line endings and strip surrounding whitespace' if raw != content else 'none',
            'exact_duplicate_occurrence':seen.get(content) if content else None,
            'exact_native_matches':[], 'retired_claim':False})
        if content:seen.setdefault(content, identifier)
        offset += len((raw + separator).encode())
    if offset != len(data):
        raise MemoryUnavailable('The Hermes source does not have complete byte accounting')
    return {'status':'present', 'byte_order_mark':bom, 'chunks':chunks}


class MemoryImport:
    def __init__(self, configuration):
        self.configuration = configuration
        self.profile = configuration.path.parent.absolute()
        if configuration.path.absolute() != self.profile / 'lifeos-memory.json':
            raise MemoryUnavailable('Import review requires the fixed Hermes profile configuration')
        selected = configuration.load()
        self.installed = Path(selected['root']).absolute()
        self.physical_root = self.installed.resolve(strict=True)
        self.principal = selected['principal']
        self.memory = NativeMemory(self.installed)

    def _owner(self, account):
        if not isinstance(account, str) or not account.startswith('dashboard:'):
            raise PermissionError('An authenticated installation owner must review memory import')
        config = self.configuration.load()
        self.configuration.check_owner(config, account)
        if (config['root'] != str(self.installed) or config['principal'] != self.principal
                or self.installed.resolve() != self.physical_root):
            raise MemoryUnavailable('The selected import installation changes during review')
        return config

    @contextmanager
    def _locks(self, account):
        with installation_lock(self.profile), self.configuration._lock(), ExitStack() as stack:
            selected = self._owner(account)
            _directory(self.profile)
            directory = self.profile / 'memories'
            if directory.exists() or directory.is_symlink():
                _directory(directory)
                for name in SOURCE_NAMES:
                    descriptor = os.open(directory / (name + '.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
                    stack.callback(os.close, descriptor)
                    info = os.fstat(descriptor)
                    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                        raise MemoryUnavailable('Hermes source locks require private owner files')
                    fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield selected

    def _sources(self):
        sources, originals = [], {}
        for name in SOURCE_NAMES:
            path = self.profile / 'memories' / name
            try:
                path.lstat()
            except FileNotFoundError:
                sources.append({'path':'memories/' + name, 'status':'missing', 'chunks':[]})
                continue
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise MemoryUnavailable('A Hermes import source requires a regular owner file')
            try:
                data, metadata = _read(path)
            except OSError as error:
                raise MemoryUnavailable('A Hermes import source cannot be read') from error
            if len(data) > SOURCE_LIMIT:
                raise MemoryUnavailable('The Hermes source exceeds its private review byte limit')
            originals['sources/' + name] = data
            info = path.lstat()
            sources.append({'path':'memories/' + name, 'size':len(data),
                'digest':hashlib.sha256(data).hexdigest(), 'identity':[info.st_dev, info.st_ino],
                **metadata, **_chunks(name, data)})
        return sources, originals

    def _settings(self):
        data, metadata = _read(self.profile / 'config.yaml')
        try:
            settings = YAML(typ='safe').load(data.decode())
        except (YAMLError, UnicodeError) as error:
            raise MemoryUnavailable('The selected Hermes configuration is unreadable or ambiguous') from error
        if not isinstance(settings, dict) or not isinstance(settings.get('memory', {}), dict):
            raise MemoryUnavailable('Import review requires supported Hermes memory settings')
        memory = settings.get('memory', {})
        if memory.get('provider', 'builtin') not in ('builtin', None):
            raise MemoryUnavailable('This import source does not select the supported built-in Hermes provider')
        limits = {key:memory.get(key, default) for key, default in (('memory_char_limit',2200),('user_char_limit',1375))}
        flags = {key:memory.get(key, True) for key in ('memory_enabled','user_profile_enabled')}
        if any(type(value) is not int or value < 1 for value in limits.values()) or any(type(value) is not bool for value in flags.values()):
            raise MemoryUnavailable('The selected Hermes memory settings have unsupported limits or flags')
        return {'provider':memory.get('provider') or 'builtin', **limits, **flags,
            'config_digest':hashlib.sha256(data).hexdigest(), 'config_mode':metadata['mode']}, data

    def _review(self, selected):
        settings, hermes = self._settings()
        sources, originals = self._sources()
        scope = MemoryPreferences._owner_scope(selected)
        with self.memory._transaction() as connection:
            active = connection.execute("SELECT * FROM records WHERE status='active' ORDER BY id").fetchall()
            matches = {}
            target = []
            content_cache = {}
            for row in active:
                content = self.memory._content(row, content_cache)
                reference = {'id':row['id'], 'revision':row['revision']}
                matches.setdefault(content, []).append(reference)
                target.append({'reference':reference,'digest':row['digest'],'category':row['category'],
                    'project':row['project'],'path':row['path']})
            hot = {category:self.memory._hot_snapshot(connection, category) for category in ('assistant','principal')}
            retired = _retirement_digest(connection)
            target_signature = self._target_signature(connection)
            for source in sources:
                for chunk in source['chunks']:
                    if chunk['content']:
                        chunk['exact_native_matches'] = matches.get(chunk['content'], [])
                        chunk['retired_claim'] = self.memory._blocked(connection, chunk['content']) or self.memory._filter_history(
                            connection, scope, chunk['content'], _now(), reviewed=True)['excluded']
            chunks = [chunk for source in sources for chunk in source['chunks'] if chunk['content']]
            if chunks:
                accepted = self.memory._native('validate_source_batch', contents=[chunk['raw'] for chunk in chunks])['accepted']
                for chunk, permitted in zip(chunks, accepted, strict=True):
                    if not permitted:
                        chunk['disposition'] = 'quarantined'
                        chunk['reason'] = 'Native retained-source validation rejects this original source text'
        original_configuration, _ = _read(self.configuration.path, private=True)
        originals.update({'configuration/config.yaml':hermes, 'configuration/lifeos-memory.json':original_configuration})
        review = {'version':1, 'profile':str(self.profile), 'installed':str(self.installed),
            'installed_physical':str(self.physical_root), 'principal':self.principal,
            'configuration_digest':_digest(json.dumps(selected,sort_keys=True)),
            'ownership_enabled':selected.get('ownership_enabled',False),
            'settings':settings, 'sources':sources, 'target':target, 'hot_snapshots':hot,
            'retirement_digest':retired, 'target_signature':target_signature,
            'readers':{'destinations':selected.get('destinations',{}),'clients':selected.get('clients',{}),
                'sharing_enabled':selected.get('sharing_enabled',False)},
            'ready_for_item_review':all(source['status'] in ('present','missing') for source in sources),
            'semantic_conflicts_incomplete':True, 'automatic_publication':False}
        review['signature'] = hashlib.sha256(_encoded(review)).hexdigest()
        return review, originals

    def preview(self, *, account=None):
        with self._locks(account) as selected:
            review, _ = self._review(selected)
            if self._owner(account) != selected:
                raise MemoryUnavailable('The import configuration changes during review')
            return review

    def prepare(self, destination, signature, *, account=None):
        destination = Path(destination).absolute()
        with self._locks(account) as selected:
            review, originals = self._review(selected)
            if signature != review['signature']:
                raise MemoryUnavailable('Import snapshot requires the exact current source and target review')
            user = self.installed.parent / '.config/LIFEOS/USER'
            if any(destination.resolve().is_relative_to(path.resolve()) for path in (self.profile,self.installed,user)):
                raise MemoryUnavailable('An import snapshot must remain outside live program and data trees')
            if destination.exists() or destination.is_symlink():
                raise MemoryUnavailable('An existing import snapshot cannot be replaced')
            if destination.parent.resolve() != destination.parent:
                raise MemoryUnavailable('The import snapshot parent changes its physical path')
            destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            _directory(destination.parent)
            stage = Path(tempfile.mkdtemp(prefix='.import-review-',dir=destination.parent))
            try:
                copies = []
                for name, data in originals.items():
                    publish(stage / name, data)
                    copies.append({'path':name,'size':len(data),'digest':hashlib.sha256(data).hexdigest()})
                document = {'version':1,'review':review,'files':copies}
                data = _encoded(document)
                publish(stage / 'manifest.json',data)
                snapshot_signature = hashlib.sha256(data).hexdigest()
                current, current_originals = self._review(self._owner(account))
                if current != review or current_originals != originals:
                    raise MemoryUnavailable('The selected import sources or targets change during snapshot creation')
                _directory(destination.parent)
                if destination.exists() or destination.is_symlink():
                    raise MemoryUnavailable('An existing import snapshot cannot be replaced')
                os.rename(stage,destination)
                descriptor=os.open(destination.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:os.fsync(descriptor)
                finally:os.close(descriptor)
                return {'state':'review','snapshot':str(destination),'snapshot_signature':snapshot_signature,
                    'review_signature':review['signature'],'ownership_enabled':selected.get('ownership_enabled',False)}
            finally:
                if stage.exists():shutil.rmtree(stage)

    def inspect(self, destination, signature, *, account=None):
        selected=self._owner(account)
        destination=Path(destination).absolute()
        _directory(destination,private=True)
        data,_=_read(destination/'manifest.json',private=True)
        if not isinstance(signature,str) or hashlib.sha256(data).hexdigest()!=signature:
            raise MemoryUnavailable('The private import snapshot changes after review')
        try:document=json.loads(data)
        except (ValueError,UnicodeError,RecursionError) as error:
            raise MemoryUnavailable('The private import snapshot has invalid metadata') from error
        if not isinstance(document,dict) or set(document)!={'version','review','files'} or type(document['version']) is not int or document['version']!=1:
            raise MemoryUnavailable('The private import snapshot has unsupported metadata')
        review=document['review']
        if (not isinstance(review,dict) or review.get('profile')!=str(self.profile)
                or review.get('installed')!=selected['root'] or review.get('installed_physical')!=str(self.physical_root)
                or review.get('principal')!=selected['principal']):
            raise MemoryUnavailable('The private import snapshot belongs to another profile or native store')
        checked=dict(review)
        review_signature=checked.pop('signature',None)
        if not isinstance(review_signature,str) or hashlib.sha256(_encoded(checked)).hexdigest()!=review_signature:
            raise MemoryUnavailable('The private import review has inconsistent metadata')
        if not isinstance(document['files'],list) or not 2<=len(document['files'])<=4:
            raise MemoryUnavailable('The private import snapshot has invalid source copies')
        allowed={'sources/'+name for name in SOURCE_NAMES}|{'configuration/config.yaml','configuration/lifeos-memory.json'}
        seen=set()
        preserved={}
        for copy in document['files']:
            if (not isinstance(copy,dict) or set(copy)!={'path','size','digest'}
                    or not isinstance(copy['path'],str) or copy['path'] not in allowed or copy['path'] in seen
                    or type(copy['size']) is not int or not 0<=copy['size']<=SOURCE_LIMIT
                    or not isinstance(copy['digest'],str)):
                raise MemoryUnavailable('The private import snapshot has invalid source copies')
            seen.add(copy['path'])
            _directory((destination/copy['path']).parent,private=True)
            content,_=_read(destination/copy['path'],private=True)
            if len(content)!=copy['size'] or hashlib.sha256(content).hexdigest()!=copy['digest']:
                raise MemoryUnavailable('A private import snapshot copy changes after review')
            preserved[copy['path']]=content
        if not {'configuration/config.yaml','configuration/lifeos-memory.json'}<=seen:
            raise MemoryUnavailable('The private import snapshot lacks its configuration copies')
        sources=review.get('sources')
        if not isinstance(sources,list) or len(sources)!=len(SOURCE_NAMES):
            raise MemoryUnavailable('The private import review has invalid source accounting')
        for name,source in zip(SOURCE_NAMES,sources,strict=True):
            if not isinstance(source,dict) or source.get('path')!='memories/'+name:
                raise MemoryUnavailable('The private import review has invalid source accounting')
            content=preserved.get('sources/'+name)
            if content is None:
                if source!={'path':'memories/'+name,'status':'missing','chunks':[]}:
                    raise MemoryUnavailable('The private import review does not account for a missing source')
                continue
            parsed=_chunks(name,content)
            if (source.get('digest')!=hashlib.sha256(content).hexdigest() or type(source.get('size')) is not int
                    or source['size']!=len(content) or source.get('status')!=parsed['status']
                    or type(source.get('byte_order_mark')) is not bool or source['byte_order_mark']!=parsed['byte_order_mark']
                    or not isinstance(source.get('chunks'),list) or len(source['chunks'])!=len(parsed['chunks'])):
                raise MemoryUnavailable('The private import review does not account for the preserved source bytes')
            annotations={'disposition','exact_native_matches','retired_claim','reason'}
            for actual,expected in zip(source['chunks'],parsed['chunks'],strict=True):
                if (not isinstance(actual,dict) or {key:value for key,value in actual.items() if key not in annotations}
                        !={key:value for key,value in expected.items() if key not in annotations}):
                    raise MemoryUnavailable('A private import occurrence does not match its preserved source bytes')
        return document

    def _target_signature(self, connection):
        rows=[dict(row) for row in connection.execute('SELECT * FROM records ORDER BY id')]
        paths={row['path'] for row in rows if row['status']=='active'} | set(HOT_FILES.values())
        files=[]
        for name in sorted(paths):
            path=self.memory._path(name)
            data,metadata=_read(path)
            files.append({'path':name,'digest':hashlib.sha256(data).hexdigest(),'mode':metadata['mode']})
        return hashlib.sha256(_encoded({'records':rows,'files':files,'retirement':_retirement_digest(connection)})).hexdigest()

    def _source_current(self, review, account):
        selected=self._owner(account)
        settings,_=self._settings()
        sources,_=self._sources()
        fields={'path','status','size','digest','identity','mode','mtime_ns','byte_order_mark'}
        source_binding=lambda rows:[{key:value for key,value in row.items() if key in fields} for row in rows]
        if (settings!=review['settings'] or source_binding(sources)!=source_binding(review['sources'])
                or _digest(json.dumps(selected,sort_keys=True))!=review['configuration_digest']):
            raise MemoryConflict('The selected Hermes source or import permissions change after review')
        return selected

    @staticmethod
    def _registry(connection):
        connection.execute("""CREATE TABLE IF NOT EXISTS imports (
            plan TEXT NOT NULL, item TEXT NOT NULL, sequence INTEGER NOT NULL,
            writer TEXT NOT NULL, request_id TEXT NOT NULL, receipt TEXT NOT NULL,
            target_signature TEXT NOT NULL, PRIMARY KEY(plan,item))""")

    def plan(self, destination, snapshot_signature, decisions, *, account=None):
        destination=Path(destination).absolute()
        with self._locks(account) as selected:
            document=self.inspect(destination,snapshot_signature,account=account)
            review=document['review']
            self._source_current(review,account)
            chunks={chunk['id']:(source,chunk) for source in review['sources'] for chunk in source['chunks'] if chunk['content']}
            if (not review['ready_for_item_review'] or not isinstance(decisions,list)
                    or any(not isinstance(item,dict) or not isinstance(item.get('id'),str) for item in decisions)
                    or len(decisions)!=len(chunks) or {item['id'] for item in decisions}!=set(chunks)):
                raise ValueError('Review each nonempty source occurrence exactly once')
            scope=replace(MemoryPreferences._owner_scope(selected),writer=account,signature=MemoryPolicy(selected).revision)
            items=[]
            with self.memory._transaction() as connection:
                if self._target_signature(connection)!=review['target_signature']:
                    raise MemoryConflict('The native import target changes after source review')
                hot={category:self.memory._hot_snapshot(connection,category) for category in HOT_FILES}
                desired={category:list(snapshot['entries']) for category,snapshot in hot.items()}
                for decision in decisions:
                    source,chunk=chunks[decision['id']]
                    action=decision.get('action')
                    fields={'id','action','required','reason'} if action in ('exclude','pending') else {'id','action','required','category','content','title','project'}
                    if (set(decision)!=fields or type(decision.get('required')) is not bool
                            or action not in ('import','exclude','pending')):
                        raise ValueError('An import decision requires exact fields and an explicit required-item choice')
                    item=dict(decision)
                    item['provenance']={'kind':'hermes-import','session':'','path':str(self.profile/source['path']),
                        'digest':source['digest'],'occurrence':chunk['id'],'original_author':'unknown','original_date':'unknown'}
                    if action in ('exclude','pending'):
                        if not isinstance(item['reason'],str) or not item['reason'].strip() or len(item['reason'])>4096:
                            raise ValueError('A pending or excluded source occurrence needs a bounded review reason')
                        items.append(item)
                        continue
                    if (chunk['disposition']=='quarantined' or chunk['retired_claim']
                            or item['category'] not in ('principal','assistant','project')
                            or any(not isinstance(item[key],str) for key in ('content','title','project'))
                            or not item['content'].strip() or len(item['content'])>65536
                            or len(item['title'])>1024 or len(item['project'])>256):
                        raise ValueError('The selected source or native import destination is not eligible for publication')
                    content=item['content'].strip()
                    if item['category']!='project':
                        item['project']=''
                        if not re.match(r'^(NAME|ROLE|RELATION|PREFERENCE|RULE): ',content):
                            content=('PREFERENCE: ' if item['category']=='principal' else 'RULE: ')+content
                    elif not item['project'].strip():
                        raise ValueError('Imported project facts require an explicit project assignment')
                    item['content']=content
                    typed=({'type':'knowledge','entity_type':'research','name':item['title'],'content':content,'source_session':'none'}
                        if item['category']=='project' else {'type':'memory','actor':item['category'],'content':content})
                    invalid=self.memory._validate(typed,content,item['category'])
                    retired = self.memory._blocked(connection, content) or self.memory._filter_history(
                        connection, scope, content, _now(), reviewed=True)['excluded']
                    if invalid or retired:
                        raise ValueError(invalid or 'The imported fact requires explicit reactivation after retirement')
                    target=Path(self.memory._native('route',item=typed)['path']).relative_to(self.installed).as_posix()
                    item['destination']=target
                    item['native_item']=typed
                    item['transformation']={'original':chunk['content'],'published':content}
                    duplicate=self.memory._duplicate(connection,scope,content,item['category'],item['project'],target)
                    item['exact_native_reference']=({'id':duplicate['id'],'revision':duplicate['revision']} if duplicate else None)
                    if item['category'] in desired and content not in desired[item['category']]:
                        desired[item['category']].append(content)
                    items.append(item)
                for category,entries in desired.items():
                    if len(entries)>hot[category]['cap_entries']:
                        raise ValueError('The complete imported hot-memory snapshot exceeds its native entry capacity')
                self._source_current(review,account)
            plan={'version':1,'snapshot_signature':snapshot_signature,'review_signature':review['signature'],
                'writer':account,'items':items,'hot_entries':desired,'ownership_switch':False}
            plan['signature']=hashlib.sha256(_encoded(plan)).hexdigest()
            path=destination/'plan.json'
            if path.exists() or path.is_symlink():
                previous,_=_read(path,private=True)
                if previous!=_encoded(plan):
                    raise MemoryUnavailable('An existing import plan cannot be replaced; prepare a new review snapshot')
            else:publish(path,_encoded(plan))
            return plan

    def _plan(self, destination, signature, snapshot_signature, account):
        data,_=_read(destination/'plan.json',private=True)
        try:plan=json.loads(data)
        except (ValueError,UnicodeError,RecursionError) as error:
            raise MemoryUnavailable('The private import plan has invalid metadata') from error
        if (not isinstance(plan,dict) or set(plan)!={'version','snapshot_signature','review_signature','writer','items','hot_entries','ownership_switch','signature'}
                or plan.get('signature')!=signature or plan.get('snapshot_signature')!=snapshot_signature
                or plan.get('writer')!=account or plan.get('ownership_switch') is not False
                or type(plan.get('version')) is not int or plan['version']!=1):
            raise MemoryUnavailable('The private import plan does not match the reviewed owner and snapshot')
        checked=dict(plan);checked.pop('signature')
        if hashlib.sha256(_encoded(checked)).hexdigest()!=signature:
            raise MemoryUnavailable('The private import plan changes after review')
        return plan

    @staticmethod
    def _request(plan, item):
        return 'hermes-import:'+plan['signature']+':'+item['id']

    def apply(self, destination, snapshot_signature, plan_signature, *, account=None):
        destination=Path(destination).absolute()
        with self._locks(account) as selected:
            document=self.inspect(destination,snapshot_signature,account=account)
            review=document['review']
            plan=self._plan(destination,plan_signature,snapshot_signature,account)
            if plan['review_signature']!=review['signature']:
                raise MemoryUnavailable('The import plan names another source review')
            scope=replace(MemoryPreferences._owner_scope(selected),writer=account,signature=MemoryPolicy(selected).revision)
            failure=None
            for item in plan['items']:
                if item['action']!='import':continue
                try:
                    self._source_current(review,account)
                except MemoryConflict as error:
                    failure={'state':'conflict','reason':str(error)}
                    break
                def check(connection):
                    self._registry(connection)
                    latest=connection.execute('SELECT target_signature FROM imports WHERE plan=? ORDER BY sequence DESC LIMIT 1',(plan_signature,)).fetchone()
                    expected=latest['target_signature'] if latest else review['target_signature']
                    if self._target_signature(connection)!=expected:
                        raise MemoryConflict('The native import target changes outside this reviewed publication')
                    self._source_current(review,account)
                    target=Path(self.memory._native('route',item=item['native_item'])['path']).relative_to(self.installed).as_posix()
                    if target!=item['destination']:
                        raise MemoryConflict('The native import destination changes after review')
                def record(connection, receipt):
                    if receipt['status'] not in ('committed','unchanged'):return
                    self._registry(connection)
                    sequence=connection.execute('SELECT COUNT(*) FROM imports WHERE plan=?',(plan_signature,)).fetchone()[0]
                    connection.execute('INSERT INTO imports VALUES (?,?,?,?,?,?,?)',
                        (plan_signature,item['id'],sequence,account,self._request(plan,item),json.dumps(receipt),self._target_signature(connection)))
                receipt=self.memory.remember(scope,category=item['category'],content=item['content'],title=item['title'],project=item['project'],
                    request_id=self._request(plan,item),source=item['provenance'],check_current=check,record_result=record)
                if receipt['status'] not in ('committed','unchanged'):
                    failure={'state':'conflict' if receipt['status']=='conflict' else 'partial','reason':receipt.get('reason','An imported item did not commit')}
                    break
            output=[]
            content_cache={}
            with self.memory._transaction() as connection:
                self._registry(connection)
                receipts={row['item']:json.loads(row['receipt']) for row in connection.execute('SELECT item,receipt FROM imports WHERE plan=?',(plan_signature,))}
                for item in plan['items']:
                    row=dict(item)
                    row['receipt']=receipts.get(item['id'])
                    if row['receipt'] is not None:
                        receipt=row['receipt']
                        current=connection.execute('SELECT * FROM records WHERE id=?',(receipt['reference']['id'],)).fetchone()
                        row['verified']=bool(current is not None and current['status']=='active' and current['revision']==receipt['reference']['revision']
                            and current['category']==item['category'] and current['project']==item['project'] and self.memory._content(current, content_cache)==item['content'])
                    else:row['verified']=False
                    output.append(row)
                latest=connection.execute('SELECT target_signature FROM imports WHERE plan=? ORDER BY sequence DESC LIMIT 1',(plan_signature,)).fetchone()
                expected=latest['target_signature'] if latest else review['target_signature']
                if self._target_signature(connection)!=expected:
                    failure={'state':'conflict','reason':'The native import target changes outside this reviewed publication'}
            try:
                self._source_current(review,account)
            except MemoryConflict as error:
                failure={'state':'conflict','reason':str(error)}
            required=all(row['verified'] for row in output if row['required'])
            committed=all(row['verified'] for row in output if row['action']=='import')
            result={'state':failure['state'] if failure else 'published' if required and committed else 'partial',
                'reason':failure['reason'] if failure else None,'items':output,'required_items_verified':required,
                'ownership_enabled':selected.get('ownership_enabled',False),'ownership_switch':False,
                'plan_signature':plan_signature,'snapshot_signature':snapshot_signature}
            publish(destination/'publication.json',_encoded(result))
            return result
