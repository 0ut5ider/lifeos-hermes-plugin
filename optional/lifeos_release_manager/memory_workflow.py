# ABOUTME: Queues owner-authorized memory activation and return outside the restarting dashboard.
# ABOUTME: Binds fixed transfer identifiers, reviewed plans, and exact bridge sources to detached jobs.
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

from .cli import profile_directory, read_private
from .inplace_services import profile_units
from .release_accounts import account_home
from .release_programs import fingerprint, publish, sync_directory
from .release_stage import load_bridge


IDENTIFIER=re.compile('[0-9a-f]{32}')
SIGNATURE=re.compile('[0-9a-f]{64}')
ACTIVE={'queued','preparing','applying','recovering','rolling_back','interrupted'}


def selection(value):
    if not isinstance(value,dict) or value.get('kind') not in ('activation','return','removal'):
        raise ValueError('Choose an import activation, reviewed provider return, or complete removal')
    fields={'activation':{'kind','identifier','snapshot_signature','plan_signature'},
        'return':{'kind','identifier','signature','plan_signature','prompt'},
        'removal':{'kind','identifier','signature','disable_discord'}}[value['kind']]
    if set(value)!=fields or not isinstance(value['identifier'],str) or IDENTIFIER.fullmatch(value['identifier']) is None:
        raise ValueError('Use the server-issued transfer identifier and exact reviewed signatures')
    for key in fields & {'snapshot_signature','plan_signature','signature'}:
        if not isinstance(value[key],str) or SIGNATURE.fullmatch(value[key]) is None:
            raise ValueError('Use the exact reviewed transfer signatures')
    if value['kind']=='return' and (not isinstance(value['prompt'],str) or not value['prompt'].strip()
            or len(value['prompt'].encode())>256*1024 or '\x00' in value['prompt']):
        raise ValueError('Review a bounded replacement Hermes prompt')
    if value['kind']=='removal' and value['disable_discord'] is not True:
        raise ValueError('Complete removal requires explicit review of Discord disablement')
    return value


def _encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def _source(profile, *, workflow=None):
    marker=Path(profile)/'.lifeos-removal.json'
    if marker.exists() or marker.is_symlink():
        from .removal_state import retained
        source,configuration,_,_=retained(profile)
        return source,configuration
    if workflow is not None:
        job,request=_job(profile,workflow)
        review_path=job/'review.json'
        if request['selection']['kind']=='removal' and (review_path.exists() or review_path.is_symlink()):
            review=read_private(review_path)
            if review.get('state')=='ready':
                from .removal_state import prepared
                source,configuration,_,_=prepared(profile,job.name,review.get('signature'))
                return source,configuration
            if review.get('state')!='preparation':
                raise ValueError('The removal source requires a completed owner review')
    source=Path(profile)/'plugins/lifeos-hook-bridge'
    module=load_bridge(source)
    configuration=module.memory_module('memory_service').MemoryConfiguration(Path(profile)/'lifeos-memory.json')
    return module,configuration


def _bridge_identity(source):
    return fingerprint(Path(source.__file__).parent)


def _removal_binding(profile, identifier, kind):
    marker=Path(profile)/'.lifeos-removal.json'
    if marker.exists() or marker.is_symlink():
        from .removal_state import retained
        _,_,job,_=retained(profile)
        if identifier!=job.name or kind!='removal':
            raise RuntimeError('Complete or recover the selected software removal first')


def _state(job, state):
    publish(job/'status.json',_encoded({'identifier':job.name,'state':state}))


def _review(job, request):
    if (job/'review.json').exists():return read_private(job/'review.json')
    return {'signature':hashlib.sha256(_encoded(request)).hexdigest(),'state':'preparation',
        'application_verified':False}


def _job(profile, identifier):
    if not isinstance(identifier,str) or IDENTIFIER.fullmatch(identifier) is None:
        raise ValueError('Choose a server-issued memory workflow identifier')
    profile=profile_directory(profile)
    job=profile/'.lifeos-portability'/identifier
    if job.resolve()!=job or not job.is_dir() or job.stat().st_uid!=os.getuid() or job.stat().st_mode & 0o077:
        raise ValueError('The memory workflow requires private profile storage')
    request=read_private(job/'request.json')
    if (set(request)!={'version','identifier','profile','owner','bridge','selection'} or request['version']!=1
            or request['identifier']!=identifier or request['profile']!=str(profile)
            or not isinstance(request['owner'],str) or not request['owner'].startswith('dashboard:')):
        raise ValueError('The memory workflow belongs to another profile')
    selection(request['selection'])
    return job,request


def status(profile, *, owner):
    profile=profile_directory(profile)
    source,configuration=_source(profile)
    configuration.check_owner(configuration.load(),owner)
    root=profile/'.lifeos-portability'
    if not root.exists():return {'operations':[]}
    source.memory_module('memory_backup')._directory(root,private=True)
    operations=[]
    for path in sorted(root.iterdir()):
        job,request=_job(profile,path.name)
        if request['owner']!=owner:continue
        value=read_private(job/'status.json')
        value={**value,'kind':request['selection']['kind']}
        value['review']=_review(job,request)
        if (job/'receipt.json').exists():value['receipt']=read_private(job/'receipt.json')
        operations.append(value)
    return {'operations':operations}


def queue(profile, value, *, owner, launch):
    value=selection(value);profile=profile_directory(profile)
    source,configuration=_source(profile)
    configuration.check_owner(configuration.load(),owner)
    with source.memory_module('installation_lock').installation_lock(profile):
        _removal_binding(profile,None,value['kind'])
        if any(operation['state'] in ACTIVE for operation in status(profile,owner=owner)['operations']):
            raise RuntimeError('Complete or recover the pending memory workflow first')
        root=profile/'.lifeos-portability';root.mkdir(mode=0o700,exist_ok=True)
        source.memory_module('memory_backup')._directory(root,private=True)
        preparing=profile/'.lifeos-portability-preparations';preparing.mkdir(mode=0o700,exist_ok=True)
        source.memory_module('memory_backup')._directory(preparing,private=True)
        identifier=uuid4().hex;job=preparing/identifier;job.mkdir(mode=0o700)
        request={'version':1,'identifier':identifier,'profile':str(profile),'owner':owner,
            'bridge':fingerprint(profile/'plugins/lifeos-hook-bridge'),'selection':value}
        publish(job/'request.json',_encoded(request));_state(job,'queued')
        os.rename(job,root/identifier);sync_directory(root);sync_directory(preparing)
    return admit(profile,identifier,'prepare',None,owner=owner,launch=launch)


def admit(profile, identifier, action, signature, *, owner, launch):
    if action not in {'prepare','apply','recover','rollback'}:raise ValueError('Choose a reviewed memory workflow action')
    profile=profile_directory(profile);source,configuration=_source(profile)
    with source.memory_module('installation_lock').installation_lock(profile):
        job,request=_job(profile,identifier)
        configuration.check_owner(configuration.load(),owner)
        _removal_binding(profile,identifier,request['selection']['kind'])
        if request['owner']!=owner or _bridge_identity(source)!=request['bridge']:
            raise PermissionError('The memory workflow owner or reviewed program source changes')
        current=read_private(job/'status.json')['state']
        if action=='prepare':
            if current!='queued':raise ValueError('The memory workflow is already prepared')
        else:
            review=_review(job,request)
            if signature!=review.get('signature'):raise ValueError('Use the exact reviewed memory workflow signature')
            if review['state']=='preparation' and action=='apply':
                raise ValueError('The memory workflow has no completed review to apply')
            permitted={'apply':{'ready'},'recover':{'queued','interrupted'},
                'rollback':{'queued','ready','configured','verified','verification_required','interrupted'}}
            if current not in permitted[action] and current not in {'preparing','applying','recovering','rolling_back'}:
                raise ValueError('The memory workflow state does not admit this action')
            if current in {'preparing','applying','recovering','rolling_back'}:
                # A live unit remains responsible for the admitted action.
                launched=read_private(job/'launch.json')
                metadata=subprocess.run(['systemctl','--user','show',launched['unit'],'--property=ActiveState','--value'],
                    capture_output=True,text=True,timeout=30)
                if metadata.returncode or metadata.stdout.strip() not in {'inactive','failed',''}:
                    raise RuntimeError('The detached memory workflow is still running')
        binding={'action':action,'workflow':identifier,'request':hashlib.sha256(_encoded(request)).hexdigest(),'signature':signature}
        administration=source.memory_administration()
        previous=read_private(job/'admission.json') if (job/'admission.json').exists() else None
        grant=administration.issue(configuration,owner,ttl=3600,binding=binding,purpose='transition')
        unit='lifeos-memory-'+identifier+'-'+uuid4().hex[:8]
        publish(job/'admission.json',_encoded({'binding':binding,'authorization':str(grant)}))
        if previous is not None:administration.revoke(configuration,previous['authorization'])
        publish(job/'launch.json',_encoded({'unit':unit}))
        _state(job,{'prepare':'preparing','apply':'applying','recover':'recovering','rollback':'rolling_back'}[action])
        try:launch(job,unit,action)
        except BaseException:
            administration.revoke(configuration,grant);_state(job,'interrupted');raise
        return {'identifier':identifier,'state':'queued','action':action}


def launch(job, unit, action):
    from hermes_cli import _launchers
    host=Path(_launchers.__file__).resolve().parents[1]
    worker=Path(__file__).with_name('memory_workflow_worker.py')
    python=sys.executable
    runtime=None
    request=read_private(job/'request.json')
    if request['selection']['kind']=='removal' and (job/'review.json').exists():
        from .removal_workflow import launch_sources
        review=read_private(job/'review.json')
        worker,runtime=launch_sources(job.parent.parent,job,review['signature'])
        # An in-place host has no fixed interpreter: Hermes selects the environment when the command starts.
        host=Path(runtime['source']);python=runtime.get('python')
    code="worker=sys.argv.pop(1)\nsys.argv[0]=worker\nrunpy.run_path(worker,run_name='__main__')\n"
    command=_launchers.runtime_command(host,[str(worker),str(job),action],
        code=code,python=python)
    command.insert(1,'-B')
    if runtime is not None and runtime.get('kind')!='host':
        from .removal_runtime import command as stock_command
        command=stock_command(command,runtime)
    profile=job.parent.parent
    environment={'HOME':str(account_home(profile)),'HERMES_HOME':str(profile),'PATH':os.environ.get('PATH',os.defpath),
        'PYTHONDONTWRITEBYTECODE':'1'}
    result=subprocess.run(['systemd-run','--user','--collect','--unit='+unit,'--property=UMask=0077',
        *['--setenv='+key+'='+value for key,value in environment.items()],*command],capture_output=True,text=True,timeout=30)
    if result.returncode:raise RuntimeError('The owner service manager cannot start the memory workflow')


def _probe(profile, source, expected, *, runtime=None):
    from hermes_cli import _launchers
    host=Path(_launchers.__file__).resolve().parents[1]
    code=('import importlib,json,types\n'
        'package=types.ModuleType("lifeos_memory_return_probe")\n'
        'package.__path__=[sys.argv[1]]\nsys.modules[package.__name__]=package\n'
        'probe=importlib.import_module(package.__name__+".memory_transition_probe")\n'
        'print(json.dumps(probe.verify_builtin(json.load(sys.stdin))))\n')
    host=host if runtime is None else Path(runtime['source'])
    python=sys.executable if runtime is None else runtime.get('python')
    command=_launchers.runtime_command(host,[str(Path(source.__file__).parent)],code=code,python=python)
    if runtime is not None and runtime.get('kind')!='host':
        from .removal_runtime import command as stock_command
        command=stock_command(command,runtime)
    environment=dict(os.environ,HERMES_HOME=str(profile),HOME=str(account_home(profile)),PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run(command,input=json.dumps(expected),text=True,capture_output=True,timeout=120,env=environment)
    if result.returncode or result.stderr:raise RuntimeError('The actual fresh Hermes agent does not verify the reviewed memory')
    return json.loads(result.stdout)


def _cancel_preparation(source, configuration, job, request, lease):
    owner=request['owner'];selected=request['selection'];profile=configuration.path.parent.absolute()
    if selected['kind']=='removal':
        marker=profile/'.lifeos-removal.json'
        if marker.exists() or marker.is_symlink():raise RuntimeError('Recover the admitted software removal')
        return {'state':'cancelled','application_verified':False,'native_data_retained':True}
    if selected['kind']=='activation':
        activation=source.memory_module('memory_activation').MemoryActivation(configuration,
            units=profile_units(profile),installation_lease=lease,operation_id=job.name)
        if activation.owns_operation(account=owner):return activation.recover(account=owner)
    else:
        snapshot=source.memory_module('memory_import_sources').directory(profile,selected['identifier'])
        returned=source.memory_module('memory_return').MemoryReturn(configuration,
            installation_lease=lease,operation_id=job.name)
        transition=source.memory_module('memory_transition').MemoryTransition(configuration,
            units=profile_units(profile),installation_lease=lease,operation_id=job.name)
        own_inner=returned.owns_operation(snapshot,account=owner)
        own_outer=transition.owns_operation(account=owner)
        if own_outer and not own_inner:raise RuntimeError('The transition loses its bound return preparation')
        inner_signature=None
        if own_inner:
            data,_=source.memory_module('memory_backup')._read(snapshot/'return/plan.json',private=True)
            inner_signature=hashlib.sha256(data).hexdigest()
            inner,state,copies=returned._load(snapshot,inner_signature,owner)
            if (state['state'] not in {'ready','cancelled'} or inner['export_signature']!=selected['signature']
                    or inner['export_plan_signature']!=selected['plan_signature']
                    or copies[('SOUL.md','after')]!=selected['prompt'].encode()):
                raise RuntimeError('The return preparation differs from this admitted workflow')
        if own_outer:
            data,_=source.memory_module('memory_backup')._read(transition.directory/'plan.json',private=True)
            signature=hashlib.sha256(data).hexdigest()
            plan,state=transition._load(signature,owner)
            if plan['snapshot']!=str(snapshot) or plan['return_signature']!=inner_signature or state not in {'ready','rolled_back'}:
                raise RuntimeError('This workflow cannot cancel an applied or unrelated provider transition')
            transition.cancel_preparation(signature,account=owner)
        if own_inner:returned.cancel_preparation(snapshot,inner_signature,account=owner)
    return {'state':'cancelled','application_verified':False}


def execute(profile, identifier, action):
    profile=profile_directory(profile);source,configuration=_source(profile,workflow=identifier)
    lock=source.memory_module('installation_lock').installation_lock
    with lock(profile,wait=True) as lease:
        job,request=_job(profile,identifier)
        _removal_binding(profile,identifier,request['selection']['kind'])
        if _bridge_identity(source)!=request['bridge']:
            raise PermissionError('The reviewed memory workflow code changes before execution')
        admission=read_private(job/'admission.json')
        review=None if action=='prepare' else _review(job,request)
        signature=None if review is None else review['signature']
        binding={'action':action,'workflow':identifier,'request':hashlib.sha256(_encoded(request)).hexdigest(),'signature':signature}
        administration=source.memory_administration()
        _,scope=administration.validate(configuration,admission['authorization'],binding=binding,check_binding=True,purpose='transition')
        if scope.writer!=request['owner']:raise PermissionError('The detached memory workflow belongs to another owner')
        try:
            selected=request['selection'];owner=request['owner']
            paths=source.memory_module('memory_import_sources')
            snapshot=paths.directory(profile,selected['identifier']) if selected['kind']!='removal' else None
            if review is not None and review['state']=='preparation':
                result=_cancel_preparation(source,configuration,job,request,lease)
            elif selected['kind']=='removal':
                from .removal_workflow import execute as remove
                result=remove(profile,job,selected,action,signature,owner=owner,source=source,
                    configuration=configuration,installation_lease=lease)
            elif selected['kind']=='activation':
                activation=source.memory_module('memory_activation').MemoryActivation(configuration,
                    units=profile_units(profile),installation_lease=lease,operation_id=identifier)
                if action=='prepare':
                    selected_source=read_private(snapshot/'source-binding.json')['source_identifier']
                    source_directory=paths.directory(profile,selected_source,source=True) if selected_source is not None else None
                    backup=paths.directory(profile,identifier)/'activation-backup'
                    result=activation.prepare(snapshot,selected['snapshot_signature'],selected['plan_signature'],backup,
                        account=owner,source_directory=source_directory)
                elif action=='apply':result=activation.apply(signature,account=owner)
                else:result=activation.recover(account=owner)
            else:
                transition=source.memory_module('memory_transition').MemoryTransition(configuration,
                    units=profile_units(profile),installation_lease=lease,operation_id=identifier)
                if action=='prepare':
                    returned=source.memory_module('memory_return').MemoryReturn(configuration,
                        installation_lease=lease,operation_id=identifier)
                    review=returned.prepare(snapshot,selected['signature'],selected['plan_signature'],prompt=selected['prompt'],account=owner)
                    result={**transition.prepare_return(snapshot,review['signature'],account=owner),'prompt':review['prompt']}
                elif action=='rollback':result=transition.rollback(signature,account=owner)
                else:
                    result=transition.apply(signature,account=owner)
                    result=transition.verify(signature,lambda expected:_probe(profile,source,expected),account=owner)
            if action=='prepare':publish(job/'review.json',_encoded(result))
            publish(job/'receipt.json',_encoded(result));_state(job,result['state'])
            return result
        finally:administration.revoke(configuration,admission['authorization'])
