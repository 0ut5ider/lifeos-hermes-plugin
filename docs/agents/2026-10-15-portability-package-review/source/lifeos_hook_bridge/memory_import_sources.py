# ABOUTME: Stages authenticated Hermes source uploads in fixed private profile storage.
# ABOUTME: Preserves original bytes without accepting client-selected filesystem paths.
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

from .lifeos_installation import state_home
from .memory_backup import _directory
from .memory_import import SOURCE_NAMES, SOURCE_LIMIT, BUNDLE_LIMIT, CHUNK_LIMIT, _encoded
from .memory_transaction import publish


def directory(profile, identifier, *, source=False):
    if not isinstance(identifier,str) or re.fullmatch('[0-9a-f]{32}',identifier) is None:
        raise ValueError('Choose a server-issued memory transfer identifier')
    profile=Path(profile).absolute()
    identity=hashlib.sha256(str(profile).encode()).hexdigest()[:24]
    root=state_home(profile)/'.local/state/lifeos-hook-bridge/imports'/identity
    return root/'sources'/identifier if source else root/identifier


def upload(profile, request):
    if (not isinstance(request,dict) or set(request)!={'label','files'}
            or not isinstance(request['label'],str) or not request['label'].strip() or len(request['label'])>256
            or not isinstance(request['files'],dict) or not request['files']
            or set(request['files'])-set(SOURCE_NAMES)):
        raise ValueError('Provide a source label and supported Hermes memory files')
    files={}
    for name,encoded in request['files'].items():
        if not isinstance(encoded,str) or len(encoded)>4*((SOURCE_LIMIT+2)//3):
            raise ValueError('A source file exceeds its import byte limit')
        try:data=base64.b64decode(encoded,validate=True)
        except (ValueError,binascii.Error) as error:
            raise ValueError('Source files require exact base64-encoded original bytes') from error
        if len(data)>SOURCE_LIMIT:raise ValueError('A source file exceeds its import byte limit')
        files[name]=data
    identifier=uuid4().hex
    target=directory(profile,identifier,source=True)
    target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    _directory(target.parent,private=True)
    target.mkdir(mode=0o700)
    for name,data in files.items():publish(target/name,data)
    publish(target/'source.json',_encoded({'kind':'hermes-files','label':request['label']}))
    return {'identifier':identifier,'state':'staged','files':[{'name':name,'size':len(data),
        'sha256':hashlib.sha256(data).hexdigest()} for name,data in files.items()]}


def portable_chunks(data):
    try:bundle=json.loads(data)
    except (ValueError,UnicodeError,RecursionError) as error:
        raise ValueError('The portable memory bundle is not valid JSON') from error
    if (not isinstance(bundle,dict) or set(bundle)!={'format','version','source','items','hermes_files','ready_for_return'}
            or bundle['format']!='lifeos-portable-memory' or type(bundle['version']) is not int or bundle['version']!=1
            or not isinstance(bundle['items'],list) or len(bundle['items'])>CHUNK_LIMIT):
        raise ValueError('Choose a supported portable memory bundle')
    chunks=[];seen={};digest=hashlib.sha256(data).hexdigest()
    for index,item in enumerate(bundle['items']):
        if not isinstance(item,dict) or item.get('action') not in ('export','retain','exclude') or not isinstance(item.get('source'),dict):
            raise ValueError('A portable source item has unsupported metadata')
        source=item['source']
        content=item.get('content') if item['action']=='export' else source.get('content')
        reference=source.get('reference')
        if (not isinstance(content,str) or not content.strip() or len(content.encode())>SOURCE_LIMIT
                or source.get('category') not in ('principal','assistant','project')
                or not isinstance(source.get('project'),str) or len(source['project'])>256
                or not isinstance(source.get('origin'),dict) or len(_encoded(source['origin']))>16384
                or type(source.get('retired_claim')) is not bool or type(source.get('quarantined')) is not bool
                or reference is not None and (not isinstance(reference,dict) or set(reference)!={'id','revision'}
                    or not isinstance(reference['id'],str) or not 1<=len(reference['id'])<=256
                    or type(reference['revision']) is not int or reference['revision']<1)):
            raise ValueError('A portable source fact has invalid content or provenance')
        normalized=content.replace('\r\n','\n').replace('\r','\n').strip()
        identifier=hashlib.sha256(_encoded(['portable-memory.json',digest,index])).hexdigest()
        quarantined=source['quarantined'] or source['retired_claim'] or item['action']=='exclude'
        chunks.append({'id':identifier,'ordinal':index,'raw':content,'content':normalized,'separator_after':'',
            'normalization':'normalize line endings and strip surrounding whitespace' if content!=normalized else 'none',
            'disposition':'quarantined' if quarantined else 'review','retired_claim':source['retired_claim'],
            'source_retired_claim':source['retired_claim'],'source_reference':reference,'source_origin':source['origin'],
            'source_category':source['category'],'source_project':source['project'],'source_action':item['action'],
            'exact_native_matches':[],'exact_duplicate_occurrence':seen.get(normalized)})
        seen.setdefault(normalized,identifier)
    return {'status':'present','byte_order_mark':False,'chunks':chunks}


def upload_bundle(profile, request):
    if (not isinstance(request,dict) or set(request) not in ({'label','bundle'},{'label','bundle_bytes'}) or not isinstance(request['label'],str)
            or not request['label'].strip() or len(request['label'])>256):
        raise ValueError('Provide a bounded source label and portable memory bundle')
    if 'bundle_bytes' in request:
        encoded=request['bundle_bytes']
        if not isinstance(encoded,str) or len(encoded)>4*((BUNDLE_LIMIT+2)//3):
            raise ValueError('The portable source exceeds its import byte limit')
        try:data=base64.b64decode(encoded,validate=True)
        except (ValueError,binascii.Error) as error:
            raise ValueError('Portable source bytes require valid base64 encoding') from error
    else:data=_encoded(request['bundle'])
    if len(data)>BUNDLE_LIMIT:raise ValueError('The portable source exceeds its import byte limit')
    portable_chunks(data)
    identifier=uuid4().hex
    target=directory(profile,identifier,source=True)
    target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    _directory(target.parent,private=True)
    target.mkdir(mode=0o700)
    publish(target/'portable-memory.json',data)
    publish(target/'source.json',_encoded({'kind':'lifeos-portable-memory','label':request['label']}))
    return {'identifier':identifier,'state':'staged','files':[{'name':'portable-memory.json','size':len(data),
        'sha256':hashlib.sha256(data).hexdigest()}]}
