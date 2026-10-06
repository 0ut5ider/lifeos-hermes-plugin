# ABOUTME: Prepares a separate named native store without adopting current profile data.
# ABOUTME: Retains identity originals and leaves ownership, sharing, and services unchanged.
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tomllib
from uuid import uuid4

from .installation_lock import installation_lock,InstallationBusy
from .install_source import install_prepared_lifeos,validate_prepared_lifeos
from .lifeos_installation import account_home
from .memory_access import NativeMemory,MemoryUnavailable,HOT_FILES
from .memory_backup import _directory,_read,ENTRY_LIMIT,TOTAL_LIMIT
from .memory_transaction import publish


IDENTIFIER=re.compile(r'[0-9a-f]{32}')


def _identifier(value):
    if not isinstance(value,str) or not IDENTIFIER.fullmatch(value):
        raise ValueError('A fresh store identifier has 32 lowercase hexadecimal characters')
    return value


IDENTITY_FILES=('CONFIG/LIFEOS_CONFIG.toml','PRINCIPAL/PRINCIPAL_IDENTITY.md',
                'DIGITAL_ASSISTANT/DA_IDENTITY.md')


def _name(value):
    if (not isinstance(value,str) or not value.strip() or value!=value.strip() or len(value)>128
            or any(not (character.isalnum() or character in " .'-()") for character in value)):
        raise ValueError('A fresh display name needs bounded plain text without markup or control characters')
    return value


def _files(root):
    result={}
    total=0
    pending=[root]
    visited=0
    while pending:
        parent=pending.pop()
        _directory(parent)
        for path in sorted(parent.iterdir()):
            visited+=1
            if visited>ENTRY_LIMIT:
                raise MemoryUnavailable('The fresh native tree exceeds its file count limit')
            info=path.lstat()
            if stat.S_ISDIR(info.st_mode):
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                data,metadata=_read(path)
                total+=len(data)
                if total>TOTAL_LIMIT:
                    raise MemoryUnavailable('The fresh native tree exceeds its byte limit')
                result[path.relative_to(root).as_posix()]={'digest':hashlib.sha256(data).hexdigest(),**metadata}
            else:
                raise MemoryUnavailable('The fresh native tree requires physical owner files and directories')
    return result


def _config_names(data,principal,assistant):
    text=data.decode()
    parsed=tomllib.loads(text)
    lines=text.splitlines(keepends=True)
    section=None
    replaced=set()
    fields={('principal','name'):principal,('da','name'):assistant,
            ('da','full_name'):assistant,('da','display_name'):assistant}
    for index,line in enumerate(lines):
        header=re.fullmatch(r'\s*\[([^\[\]]+)\]\s*(?:#.*)?\n?',line)
        if header:section=header[1]
        for (group,key),value in fields.items():
            if section==group and re.match(r'\s*'+key+r'\s*=',line):
                if (group,key) in replaced:
                    raise MemoryUnavailable('The fresh identity configuration has ambiguous fields')
                lines[index]=key+' = '+json.dumps(value,ensure_ascii=False)+'\n'
                replaced.add((group,key))
    if replaced!=set(fields) or not isinstance(parsed.get('principal'),dict) or not isinstance(parsed.get('da'),dict):
        raise MemoryUnavailable('The fresh identity configuration lacks its supported name fields')
    result=''.join(lines).encode()
    checked=tomllib.loads(result.decode())
    if checked['principal']['name']!=principal or checked['da']['name']!=assistant:
        raise MemoryUnavailable('The fresh identity configuration does not retain the selected names')
    return result


def owner_binding(selected,account):
    return selected['root'],selected['principal'],selected.get('accounts',{}).get(account)


class FreshStore:
    def __init__(self,configuration):
        self.configuration=configuration
        self.profile=configuration.path.parent.absolute()
        if configuration.path.absolute()!=self.profile/'lifeos-memory.json':
            raise MemoryUnavailable('Fresh store preparation requires the fixed profile configuration')
        selected=configuration.load()
        self.installed=Path(selected['root']).absolute()
        self.physical_root=self.installed.resolve(strict=True)
        self.principal=selected['principal']

    def _owner(self,account):
        if not isinstance(account,str) or not account.startswith('dashboard:'):
            raise PermissionError('An authenticated installation owner must prepare a fresh store')
        with self.configuration._lock():
            selected=self.configuration.load()
        self.configuration.check_owner(selected,account)
        if (selected['root']!=str(self.installed) or selected['principal']!=self.principal
                or self.installed.resolve()!=self.physical_root):
            raise MemoryUnavailable('The selected installation changes during fresh store preparation')
        return selected

    def _base(self):
        identity=hashlib.sha256(str(self.profile).encode()).hexdigest()[:24]
        return account_home(self.profile)/'.local/state/lifeos-hook-bridge/fresh-stores'/identity

    def _store(self,folder,running):
        info=folder.lstat()
        if not stat.S_ISDIR(info.st_mode) or not re.fullmatch(r'[0-9a-f]{32}',folder.name):
            raise MemoryUnavailable('The fresh store listing requires physical prepared directories')
        _directory(folder,private=True)
        unfinished={'identifier':folder.name,'state':'preparing' if running else 'interrupted'}
        review=folder/'review.json'
        if not review.exists() and not review.is_symlink():
            return info.st_mtime_ns,unfinished
        data,metadata=_read(review)
        invalid=metadata['mtime_ns'],{'identifier':folder.name,'state':'invalid'}
        try:
            document=json.loads(data)
        except ValueError:
            return invalid
        names=document.get('names') if isinstance(document,dict) else None
        if (not isinstance(names,dict) or set(names)!={'principal','assistant'}
                or document.get('profile')!=str(self.profile)):
            return invalid
        try:
            for value in names.values():_name(value)
        except ValueError:
            return invalid
        if document.get('state')=='preparing':
            return metadata['mtime_ns'],{**unfinished,'names':names}
        if document.get('state')=='failed':
            reason=document.get('reason')
            if not isinstance(reason,str) or not 1<=len(reason)<=300:
                return invalid
            return metadata['mtime_ns'],{'identifier':folder.name,'state':'failed','names':names,'reason':reason}
        unsigned={key:value for key,value in document.items() if key!='signature'}
        signature=hashlib.sha256((json.dumps(unsigned,sort_keys=True,indent=2)+'\n').encode()).hexdigest()
        if document.get('state')!='review' or document.get('signature')!=signature:
            return invalid
        return metadata['mtime_ns'],{'identifier':folder.name,'state':'review','names':names,
            **{key:document.get(key) for key in ('active_facts','activation_ready','source','retained_installation')}}

    def status(self,*,account=None):
        selected=self._owner(account)
        base=self._base()
        try:
            with installation_lock(self.profile):
                busy=False
        except InstallationBusy:
            busy=True
        stores=[]
        if base.exists() or base.is_symlink():
            _directory(base,private=True)
            stores=[self._store(folder,busy) for folder in base.iterdir()]
        if owner_binding(self._owner(account),account)!=owner_binding(selected,account):
            raise MemoryUnavailable('The installation owner changes during the fresh store listing')
        stores.sort(key=lambda row:(-row[0],row[1]['identifier']))
        return {'busy':busy,'stores':[row for _,row in stores]}

    def _ensure_base(self):
        base=self._base()
        if base.resolve()!=base:
            raise MemoryUnavailable('The fresh store destination changes its physical path')
        base.mkdir(parents=True,exist_ok=True,mode=0o700)
        _directory(base,private=True)
        return base

    def record_failure(self,identifier,*,principal_name,assistant_name,reason):
        # A detached preparation records its outcome, so the listing does not show it as interrupted.
        identifier=_identifier(identifier)
        names={'principal':_name(principal_name),'assistant':_name(assistant_name)}
        if not isinstance(reason,str) or not 1<=len(reason)<=300:
            raise ValueError('A fresh store failure needs a short reason')
        destination=self._ensure_base()/identifier
        if destination.is_symlink():
            raise MemoryUnavailable('The fresh store listing requires physical prepared directories')
        destination.mkdir(mode=0o700,exist_ok=True)
        _directory(destination,private=True)
        document={'version':1,'state':'failed','profile':str(self.profile),'names':names,'reason':reason}
        publish(destination/'review.json',(json.dumps(document,sort_keys=True,indent=2)+'\n').encode())

    def review_home(self,identifier,*,account=None):
        """Return the LifeOS home and review record of one reviewed store."""
        identifier=_identifier(identifier)
        self._owner(account)
        folder=self._base()/identifier
        if folder.is_symlink() or not folder.is_dir():
            raise MemoryUnavailable('The fresh store does not exist')
        _,row=self._store(folder,False)
        if row['state']!='review':
            raise MemoryUnavailable('Only a reviewed fresh store can be selected')
        return folder/'home',row

    def remove(self,identifier,*,account=None):
        identifier=_identifier(identifier)
        try:
            with installation_lock(self.profile):
                selected=self._owner(account)
                folder=self._base()/identifier
                if folder.is_symlink() or not folder.is_dir():
                    raise MemoryUnavailable('The fresh store does not exist')
                _directory(folder,private=True)
                if Path(selected['root']).absolute().is_relative_to(folder):
                    raise MemoryUnavailable('The selected installation cannot be removed')
                shutil.rmtree(folder)
                return {'identifier':identifier,'removed':True}
        except InstallationBusy as error:
            raise MemoryUnavailable('Another installation operation is running') from error

    def prepare(self,candidate,*,principal_name,assistant_name,account=None,identifier=None):
        candidate=Path(candidate).absolute()
        identifier=uuid4().hex if identifier is None else _identifier(identifier)
        with installation_lock(self.profile):
            selected=self._owner(account)
            principal=_name(principal_name);assistant=_name(assistant_name)
            source=validate_prepared_lifeos(candidate)
            destination=self._ensure_base()/identifier
            destination.mkdir(mode=0o700)
            document={'version':1,'state':'preparing','profile':str(self.profile),
                'retained_installation':str(self.installed),'source':source,
                'names':{'principal':principal,'assistant':assistant},'ownership_enabled':False,
                'sharing_enabled':False,'services_started':False}
            status=destination/'review.json'
            publish(status,(json.dumps(document,sort_keys=True,indent=2)+'\n').encode())
            home=destination/'home';home.mkdir(mode=0o700)
            installed=home/'.claude'
            installation=install_prepared_lifeos(candidate,installed,destination/'failed-install')
            user=home/'.config/LIFEOS/USER'
            if (installed/'LIFEOS/USER').resolve()!=user:
                raise MemoryUnavailable('The fresh native installation selects another user store')
            templates=_files(candidate/'LifeOS/install/USER')
            originals=_files(user)
            if {key:value['digest'] for key,value in originals.items()}!={key:value['digest'] for key,value in templates.items()}:
                raise MemoryUnavailable('The fresh native user tree differs from its shipped templates')
            memory=NativeMemory(installed)
            for name in HOT_FILES.values():
                if memory._native('read_hot',path=str(installed/name))['entries']:
                    raise MemoryUnavailable('The fresh native template contains active memory entries')
            scaffold=installed/'LIFEOS/MEMORY'
            _files(scaffold)
            target=user/'MEMORY'
            if target.exists() or target.is_symlink():
                raise MemoryUnavailable('The fresh native user tree already contains a memory store')
            os.rename(scaffold,target)
            scaffold.symlink_to(target,target_is_directory=True)
            for name in IDENTITY_FILES:
                data,_=_read(user/name)
                publish(destination/'identity-originals'/name,data)
                if name=='CONFIG/LIFEOS_CONFIG.toml':
                    rendered=_config_names(data,principal,assistant)
                elif name.startswith('PRINCIPAL/'):
                    rendered=re.sub(r'\bUser\b',lambda _:principal,data.decode()).encode()
                else:
                    rendered=data.decode().replace('LifeOS Assistant',assistant).replace('LifeOS',assistant)
                    rendered=re.sub(r'\bUser\b',lambda _:principal,rendered).encode()
                publish(user/name,rendered)
            for path in user.rglob('*'):
                info=path.lstat()
                os.chmod(path,stat.S_IMODE(info.st_mode)&0o700,follow_symlinks=False)
            os.chmod(user,0o700)
            with memory._transaction() as connection:
                active=connection.execute("SELECT COUNT(*) FROM records WHERE status='active'").fetchone()[0]
                if active or connection.execute('SELECT COUNT(*) FROM operations').fetchone()[0]:
                    raise MemoryUnavailable('The fresh native store contains unexpected fact operations')
            if (owner_binding(self._owner(account),account)!=owner_binding(selected,account)
                    or validate_prepared_lifeos(candidate)!=source):
                raise MemoryUnavailable('The reviewed source or owner changes during fresh store preparation')
            document.update(state='review',installed=str(installed),data=str(user),
                retained_hermes_files=['memories/MEMORY.md','memories/USER.md'],installation=installation,
                active_facts=active,source_template_files=len(templates),files=_files(user),
                activation_ready=False,return_installation=str(self.installed))
            document['signature']=hashlib.sha256((json.dumps(document,sort_keys=True,indent=2)+'\n').encode()).hexdigest()
            publish(status,(json.dumps(document,sort_keys=True,indent=2)+'\n').encode())
            return document
