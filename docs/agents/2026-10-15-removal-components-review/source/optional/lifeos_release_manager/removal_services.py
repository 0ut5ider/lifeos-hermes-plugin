# ABOUTME: Binds original and removed service definitions during complete software removal.
# ABOUTME: Verifies actual empty control groups and resumes only the reviewed Hermes services.
import hashlib
import json
import os
from pathlib import Path

from .cli import read_private
from .release_catalog import ReleaseRejected
from .release_programs import fingerprint, publish


PROPERTIES=('Id','LoadState','ActiveState','MainPID','ControlGroup','FragmentPath','DropInPaths',
    'WorkingDirectory','RootDirectory','RootImage','KillMode','NeedDaemonReload','UnitFileState')


class RemovalServices:
    def __init__(self, services, journal):
        self.services=services
        self.journal=Path(journal)

    @staticmethod
    def _digest(value):
        return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def _run(self,*arguments):
        from importlib import import_module
        return import_module(type(self.services).__module__)._run(*arguments)

    def _identity(self, path):
        from importlib import import_module
        declared=Path(path)
        if not declared.exists() and not declared.is_symlink():return None
        value=import_module(type(self.services).__module__)._definition_file(path)
        info=Path(value['physical']).stat()
        return {**value,'mode':info.st_mode,'uid':info.st_uid}

    def _properties(self, role):
        output=self._run('show',self.services.units[role],'--property='+','.join(PROPERTIES),'--no-pager')
        values=dict(line.split('=',1) for line in output.splitlines())
        if (set(values)!=set(PROPERTIES) or values['Id']!=self.services.units[role]
                or not values['MainPID'].isdigit() or values['RootDirectory'] or values['RootImage']):
            raise ReleaseRejected('The removal service changes its process identity')
        self.services._group(values['ControlGroup'])
        return values

    def prepare(self, *, removed):
        with self.services._lock():
            if self.journal.exists() or self.journal.is_symlink():
                raise ReleaseRejected('Use the existing removal service review')
            admitted=self.services._admission()
            pulse=self._properties('pulse')
            if pulse['ActiveState']!='inactive' or pulse['MainPID']!='0' or pulse['UnitFileState'] not in {'disabled','static'}:
                raise ReleaseRejected('Return to Hermes and disable Pulse before software removal')
            removed={str(Path(path).absolute()) for path in removed}
            roles={};known=set()
            for role in self.services.units:
                values=self._properties(role)
                paths=[values['FragmentPath'],*values['DropInPaths'].split()]
                identities={path:self._identity(path) for path in paths}
                if any(value is None for value in identities.values()):
                    raise ReleaseRejected('Removal requires bound trusted service definition files')
                known.update(paths)
                roles[role]={'unit':self.services.units[role],'files':identities,'fragment':values['FragmentPath'],
                    'drop_ins':values['DropInPaths'].split(),'active':admitted['services'][role]['active'],
                    'control_group':values['ControlGroup']}
            if not removed<=known or roles['pulse']['fragment'] not in removed:
                raise ReleaseRejected('Removal must identify the exact owned Pulse fragment and overrides')
            if any(item['fragment'] in removed for role,item in roles.items() if role!='pulse'):
                raise ReleaseRejected('The Hermes service definitions must remain installed')
            for path in removed:
                identity=fingerprint(path)
                if identity is None or identity['type']!='file' or Path(path).resolve()!=Path(path):
                    raise ReleaseRejected('Only regular account-owned definitions can be removed')
            document={'format':1,'profile':str(self.services.profile),'installed':str(self.services.installed),
                'units':self.services.units,'services':roles,'removed':sorted(removed)}
            publish(self.journal,(json.dumps(document,sort_keys=True)+'\n').encode())
            return self._digest(document)

    def _load(self, signature):
        value=read_private(self.journal)
        if (self._digest(value)!=signature or set(value)!={'format','profile','installed','units','services','removed'}
                or value['format']!=1 or value['profile']!=str(self.services.profile)
                or value['installed']!=str(self.services.installed) or value['units']!=self.services.units
                or set(value['services'])!=set(self.services.units)):
            raise ReleaseRejected('The removal services differ from their exact review')
        return value

    def _files(self, document, *, side=None):
        for item in document['services'].values():
            for path,before in item['files'].items():
                after=None if path in document['removed'] else before
                actual=self._identity(path)
                accepted=(before,after) if side is None else ((before,) if side=='before' else (after,))
                if actual not in accepted:raise ReleaseRejected('A reviewed removal service definition changes')

    def _bound(self, document, role, *, reload_required=False):
        value=self._properties(role);item=document['services'][role]
        if value['LoadState']=='not-found':
            if role!='pulse' or Path(item['fragment']).exists() or value['FragmentPath'] or value['DropInPaths']:
                raise ReleaseRejected('An unreviewed profile service disappears during removal')
        else:
            if (value['LoadState']!='loaded' or value['FragmentPath']!=item['fragment']
                    or value['KillMode'] not in {'mixed','control-group'}):
                raise ReleaseRejected('The removal service changes its definition binding')
            expected={path for path in item['drop_ins'] if Path(path).exists()}
            if set(value['DropInPaths'].split())!=expected:
                raise ReleaseRejected('The removal service loads an unreviewed override')
            working=value['WorkingDirectory'].removeprefix('!')
            if working=='~':working=str(self.services.installed.parent)
            expected_directory=self.services.directories[role]
            if not Path(working).is_absolute() or Path(working).resolve()!=expected_directory:
                raise ReleaseRejected('The removal service changes its working directory')
        if reload_required and value['NeedDaemonReload']!='no':
            raise ReleaseRejected('The service manager does not load the reviewed removal definitions')
        return value

    def _empty(self, document, role):
        values=self._bound(document,role,reload_required=True)
        if values['ActiveState'] not in {'inactive','failed'} or values['MainPID']!='0':
            raise ReleaseRejected('A removal service still has a writer process')
        for name in {values['ControlGroup'],document['services'][role]['control_group']}:
            group=self.services._group(name)
            if group is None:continue
            try:content=(group/'cgroup.events').read_text()
            except FileNotFoundError:
                if group.exists():raise ReleaseRejected('A removal control group has no verifiable state')
                continue
            if 'populated 0' not in content.splitlines():
                raise ReleaseRejected('A removal service still has child writers')

    def stop(self, signature):
        document=self._load(signature);self._files(document)
        self._run('daemon-reload')
        for role in self.services.stop_order:
            value=self._bound(document,role,reload_required=True)
            if value['ActiveState'] not in {'inactive','failed'} or value['MainPID']!='0':
                self._run('stop',self.services.units[role])
            self._empty(document,role)
        self.verify_stopped(signature)

    def verify_stopped(self, signature):
        document=self._load(signature);self._files(document)
        for role in self.services.units:self._empty(document,role)

    def resume(self, signature, *, restored=False):
        document=self._load(signature);self._files(document,side='before' if restored else 'after')
        self._run('daemon-reload')
        self.verify_stopped(signature)
        for role in self.services.start_order:
            if role!='pulse' and document['services'][role]['active']:
                self._run('start',self.services.units[role])
        self.verify(signature,restored=restored)

    def verify(self, signature, *, restored=False):
        document=self._load(signature);self._files(document,side='before' if restored else 'after')
        for role in self.services.units:
            values=self._bound(document,role,reload_required=True)
            active=role!='pulse' and document['services'][role]['active']
            if active:
                if values['ActiveState']!='active' or int(values['MainPID'])<=0:
                    raise ReleaseRejected('The reviewed Hermes service does not become active')
            else:self._empty(document,role)
        pulse=self._properties('pulse')
        if not restored and pulse['LoadState']!='not-found':
            raise ReleaseRejected('The LifeOS service remains installed after removal')
        return {'hermes_services_verified':True,'pulse_stopped':True,'pulse_definition_removed':not restored}
