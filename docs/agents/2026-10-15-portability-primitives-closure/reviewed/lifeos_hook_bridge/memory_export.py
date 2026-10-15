# ABOUTME: Prepares owner-reviewed portable facts and bounded built-in Hermes memory files.
# ABOUTME: Retains overflow and source provenance without changing the active memory provider.
import hashlib
import json
from pathlib import Path
import re

from .memory_access import MemoryConflict, MemoryUnavailable, _now
from .memory_backup import _directory, _read
from .memory_import import MemoryImport, SOURCE_NAMES, SOURCE_LIMIT, BUNDLE_LIMIT, CHUNK_LIMIT, DELIMITER, _encoded
from .memory_preferences import MemoryPreferences
from .memory_transaction import publish


def _signature(value):
    return hashlib.sha256(_encoded(value)).hexdigest()


class MemoryExport:
    def __init__(self, configuration, *, installation_lease=None):
        self.configuration=configuration
        self.importer=MemoryImport(configuration,installation_lease=installation_lease)
        self.profile=self.importer.profile
        self.memory=self.importer.memory

    def preview(self, *, account=None):
        with self.importer._locks(account) as selected:
            base,_=self.importer._review(selected)
            if not base['ready_for_item_review']:
                raise MemoryUnavailable('Resolve unreadable built-in memory before reverse export')
            items=[]
            for source in base['sources']:
                for chunk in source['chunks']:
                    if not chunk['content']:continue
                    items.append({'id':'hermes:'+chunk['id'],'content':chunk['content'],
                        'category':'principal' if source['path'].endswith('USER.md') else 'project',
                        'project':'','reference':None,'origin':{'kind':'hermes','path':source['path'],
                            'digest':source['digest'],'occurrence':chunk['id'],'original_author':'unknown','original_date':'unknown'},
                        'retired_claim':bool(chunk['retired_claim']),
                        'quarantined':chunk['disposition']=='quarantined'})
            scope=MemoryPreferences._owner_scope(selected)
            with self.memory._transaction() as connection:
                if self.importer._target_signature(connection)!=base['target_signature']:
                    raise MemoryConflict('The export source changes during review')
                cache={}
                for row in connection.execute("SELECT * FROM records WHERE status='active' ORDER BY id"):
                    if not self.memory._allowed(scope,row):continue
                    content=self.memory._content(row,cache)
                    blocked=bool(self.memory._blocked(connection,content) or self.memory._filter_history(
                        connection,scope,content,_now(),reviewed=True)['excluded'])
                    items.append({'id':'lifeos:'+row['id'],'content':content,'category':row['category'],
                        'project':row['project'],'reference':{'id':row['id'],'revision':row['revision']},
                        'origin':{'kind':row['source_kind'],'session':row['source_session'],'writer':row['writer'],
                            'record_updated':row['updated'],'path':row['path'],
                            'original_author':'unknown','original_date':'unknown'},
                        'retired_claim':blocked,'quarantined':False})
                if len(items)>CHUNK_LIMIT or sum(len(item['content'].encode()) for item in items)>2*SOURCE_LIMIT:
                    raise MemoryUnavailable('The reverse export exceeds its bounded review capacity')
            current,_=self.importer._review(self.importer._owner(account))
            if current!=base:
                raise MemoryConflict('The export source changes during review')
            review={'version':1,'profile':str(self.profile),'root':selected['root'],'principal':selected['principal'],
                'source_review_signature':base['signature'],'target_signature':base['target_signature'],
                'settings':base['settings'],'readers':base['readers'],'items':items,
                'semantic_conflicts_incomplete':True,'provider_switch':False}
            return {**review,'signature':_signature(review)}

    def prepare(self, destination, signature, *, account=None):
        review=self.preview(account=account)
        if signature!=review['signature']:
            raise MemoryConflict('Reverse export requires the current source review')
        saved=self.importer.prepare(destination,review['source_review_signature'],account=account)
        document={'version':1,'snapshot_signature':saved['snapshot_signature'],'review':review}
        data=_encoded(document)
        publish(Path(destination)/'export-review.json',data)
        return {'state':'review','snapshot':str(Path(destination).absolute()),
            'signature':hashlib.sha256(data).hexdigest(),'snapshot_signature':saved['snapshot_signature']}

    def inspect(self, destination, signature, *, account=None):
        destination=Path(destination).absolute()
        self.importer._owner(account)
        _directory(destination,private=True)
        data,_=_read(destination/'export-review.json',private=True)
        if not isinstance(signature,str) or hashlib.sha256(data).hexdigest()!=signature:
            raise MemoryUnavailable('The private reverse export review changes')
        try: document=json.loads(data)
        except (ValueError,UnicodeError,RecursionError) as error:
            raise MemoryUnavailable('The reverse export review has invalid metadata') from error
        if (not isinstance(document,dict) or set(document)!={'version','snapshot_signature','review'}
                or type(document['version']) is not int or document['version']!=1):
            raise MemoryUnavailable('The reverse export review has unsupported metadata')
        captured=self.importer.inspect(destination,document['snapshot_signature'],account=account)['review']
        review=document['review']
        if (not isinstance(review,dict) or review.get('profile')!=str(self.profile)
                or review.get('root')!=str(self.importer.installed) or review.get('principal')!=self.importer.principal
                or review.get('source_review_signature')!=captured['signature']
                or review.get('target_signature')!=captured['target_signature']
                or not isinstance(review.get('items'),list)):
            raise MemoryUnavailable('The reverse export review belongs to another installation')
        checked=dict(review);review_signature=checked.pop('signature',None)
        if _signature(checked)!=review_signature:
            raise MemoryUnavailable('The reverse export review has inconsistent metadata')
        return document,captured

    def _current(self, captured, account):
        self.importer._source_current(captured,account)
        with self.memory._transaction() as connection:
            if self.importer._target_signature(connection)!=captured['target_signature']:
                raise MemoryConflict('The LifeOS export source changes after review')

    def plan(self, destination, signature, decisions, *, account=None):
        destination=Path(destination).absolute()
        with self.importer._locks(account):
            document,captured=self.inspect(destination,signature,account=account)
            self._current(captured,account)
            items={item['id']:item for item in document['review']['items']}
            if (not isinstance(decisions,list) or len(decisions)!=len(items)
                    or any(not isinstance(item,dict) or not isinstance(item.get('id'),str) for item in decisions)
                    or {item['id'] for item in decisions}!=set(items)):
                raise ValueError('Review each current fact and preserved Hermes occurrence exactly once')
            planned=[];entries={name:[] for name in SOURCE_NAMES}
            scope=MemoryPreferences._owner_scope(self.importer._owner(account))
            from tools.memory_tool_store import _scan_memory_content
            for decision in decisions:
                action=decision.get('action')
                fields={'id','action','required','file','content'} if action=='export' else {'id','action','required','reason'}
                if (set(decision)!=fields or action not in ('export','retain','exclude')
                        or type(decision.get('required')) is not bool):
                    raise ValueError('Each export decision requires exact fields and a required-item choice')
                source=items[decision['id']]
                item={**decision,'source':source}
                if action=='export':
                    content=decision['content']
                    if (not isinstance(content,str) or not content.strip() or content!=content.strip()
                            or len(content.encode())>SOURCE_LIMIT or '\r' in content
                            or re.search(r'(?:^|\n)§(?:\n|$)',content)
                            or decision['file'] not in SOURCE_NAMES
                            or source['retired_claim'] or source['quarantined']):
                        raise ValueError('The selected export text or Hermes destination is not eligible')
                    if _scan_memory_content(content):
                        raise ValueError('Hermes memory validation rejects this export text')
                    with self.memory._transaction() as connection:
                        if (self.memory._blocked(connection,content) or self.memory._filter_history(
                                connection,scope,content,_now(),reviewed=True)['excluded']):
                            raise ValueError('The export text matches a known retired claim')
                    valid=self.memory._native('validate_source_batch',contents=[content])['accepted']
                    if valid!=[True]:raise ValueError('Native source validation rejects this export text')
                    item['transformation']={'original':source['content'],'published':content}
                    item['exact_duplicate']=content in entries[decision['file']]
                    if not item['exact_duplicate']:entries[decision['file']].append(content)
                elif (not isinstance(decision['reason'],str) or not decision['reason'].strip()
                        or len(decision['reason'])>4096):
                    raise ValueError('Retained and excluded export items require a bounded reason')
                planned.append(item)
            files={name:DELIMITER.join(entries[name]) for name in SOURCE_NAMES}
            limits={'MEMORY.md':captured['settings']['memory_char_limit'],'USER.md':captured['settings']['user_char_limit']}
            for name,content in files.items():
                if len(content)>limits[name]:
                    raise ValueError('The reviewed Hermes memory exceeds its character capacity')
            self._current(captured,account)
            plan={'version':1,'review_signature':signature,'writer':account,'items':planned,'files':files,'limits':limits,
                'ready_for_return':all(item['action']=='export' for item in planned if item['required']),
                'provider_switch':False}
            if len(self._bundle(document,plan))>BUNDLE_LIMIT:
                raise ValueError('The complete portable bundle exceeds its import byte capacity')
            plan['signature']=_signature(plan)
            path=destination/'export-plan.json'
            if path.exists() or path.is_symlink():
                previous,_=_read(path,private=True)
                if previous!=_encoded(plan):raise MemoryUnavailable('Prepare a new reverse export review to change the plan')
            else:publish(path,_encoded(plan))
            return plan

    def _plan(self, destination, signature, plan_signature, account):
        data,_=_read(destination/'export-plan.json',private=True)
        try: plan=json.loads(data)
        except (ValueError,UnicodeError,RecursionError) as error:
            raise MemoryUnavailable('The reverse export plan has invalid metadata') from error
        if (not isinstance(plan,dict) or set(plan)!={'version','review_signature','writer','items','files','limits','ready_for_return','provider_switch','signature'}
                or plan.get('review_signature')!=signature or plan.get('writer')!=account
                or plan.get('signature')!=plan_signature or plan.get('provider_switch') is not False):
            raise MemoryUnavailable('The reverse export plan does not match the reviewed owner and source')
        checked=dict(plan);checked.pop('signature')
        if _signature(checked)!=plan_signature:raise MemoryUnavailable('The reverse export plan changes after review')
        return plan

    @staticmethod
    def _bundle(document, plan):
        return _encoded({'format':'lifeos-portable-memory','version':1,'source':document['review'],
            'items':plan['items'],'hermes_files':plan['files'],'ready_for_return':plan['ready_for_return']})

    def apply(self, destination, signature, plan_signature, *, account=None):
        destination=Path(destination).absolute()
        with self.importer._locks(account):
            document,captured=self.inspect(destination,signature,account=account)
            plan=self._plan(destination,signature,plan_signature,account)
            self._current(captured,account)
            targets={destination/'hermes'/name:content.encode() for name,content in plan['files'].items()}
            targets[destination/'portable-memory.json']=self._bundle(document,plan)
            if (destination/'hermes').exists():_directory(destination/'hermes',private=True)
            before={}
            for path,data in targets.items():
                if path.exists() or path.is_symlink():
                    previous,metadata=_read(path,private=True)
                    if previous!=data:raise MemoryConflict('The reverse export preserves a later output edit')
                    before[path]=(previous,metadata)
                else:before[path]=(None,None)
            for path,data in targets.items():
                self._current(captured,account)
                actual=_read(path,private=True) if path.exists() or path.is_symlink() else (None,None)
                if actual!=before[path]:raise MemoryConflict('The reverse export preserves an output edit during publication')
                if actual[0]!=data:publish(path,data)
            self._current(captured,account)
            for path,data in targets.items():
                actual,_=_read(path,private=True)
                if actual!=data:raise MemoryConflict('A reverse export output changes during verification')
            result={'state':'exported','signature':signature,'plan_signature':plan_signature,
                'ready_for_return':plan['ready_for_return'],'provider_switch':False,
                'files':[{'path':str(path),'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for path,data in targets.items()]}
            publish(destination/'export-receipt.json',_encoded(result))
            return result

    def status(self, destination, signature, *, account=None):
        destination=Path(destination).absolute()
        with self.importer._locks(account):
            document,captured=self.inspect(destination,signature,account=account)
            plan=None;receipt=None
            if (destination/'export-plan.json').exists() or (destination/'export-plan.json').is_symlink():
                data,_=_read(destination/'export-plan.json',private=True)
                try: plan_signature=json.loads(data)['signature']
                except (ValueError,KeyError,TypeError) as error:
                    raise MemoryUnavailable('The reverse export plan has invalid metadata') from error
                plan=self._plan(destination,signature,plan_signature,account)
            if (destination/'export-receipt.json').exists() or (destination/'export-receipt.json').is_symlink():
                data,_=_read(destination/'export-receipt.json',private=True)
                try: receipt=json.loads(data)
                except ValueError as error:
                    raise MemoryUnavailable('The reverse export receipt has invalid metadata') from error
                if not isinstance(receipt,dict) or plan is None or receipt.get('plan_signature')!=plan['signature'] or receipt.get('signature')!=signature:
                    raise MemoryUnavailable('The reverse export receipt belongs to another review')
            try:
                self._current(captured,account)
                current=True
            except MemoryConflict:
                current=False
            return {'review':document['review'],'plan':plan,'receipt':receipt,'source_current':current}

    def download(self, destination, signature, *, account=None):
        destination=Path(destination).absolute()
        with self.importer._locks(account):
            document,captured=self.inspect(destination,signature,account=account)
            self._current(captured,account)
            data,_=_read(destination/'export-plan.json',private=True)
            try: plan_signature=json.loads(data)['signature']
            except (ValueError,KeyError,TypeError) as error:
                raise MemoryUnavailable('The reverse export plan has invalid metadata') from error
            plan=self._plan(destination,signature,plan_signature,account)
            bundle,_=_read(destination/'portable-memory.json',private=True)
            if bundle!=self._bundle(document,plan):raise MemoryUnavailable('The portable export changes after publication')
            for name,content in plan['files'].items():
                actual,_=_read(destination/'hermes'/name,private=True)
                if actual!=content.encode():raise MemoryUnavailable('A Hermes export changes after publication')
            self._current(captured,account)
            return bundle
