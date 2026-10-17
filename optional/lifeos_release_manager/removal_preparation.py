# ABOUTME: Prepares a current-state complete removal after an exact verified provider return.
# ABOUTME: Binds retained recovery sources, stock runtime, fixed software targets, and owner review.
from pathlib import Path

from .cli import read_private
from .release_catalog import ReleaseRejected


def returned(profile, identifier, signature, *, owner, source, configuration, installation_lease=None):
    from .memory_workflow import _job
    profile=Path(profile).absolute()
    value=configuration.load();configuration.check_owner(value,owner)
    if value.get('ownership_enabled') is not False:
        raise ReleaseRejected('Return to built-in memory before complete software removal')
    job,request=_job(profile,identifier)
    receipt=read_private(job/'receipt.json');review=read_private(job/'review.json')
    if (request['owner']!=owner or request['selection']['kind']!='return'
            or read_private(job/'status.json')['state']!='verified'
            or receipt.get('state')!='verified' or receipt.get('application_verified') is not True
            or review.get('signature')!=signature or receipt.get('signature')!=signature):
        raise ReleaseRejected('Removal requires the exact verified provider-return workflow')
    from .inplace_services import profile_units
    transition=source.memory_module('memory_transition').MemoryTransition(configuration,
        units=profile_units(profile),installation_lease=installation_lease,operation_id=identifier)
    plan,state=transition._load(signature,owner)
    expected=source.memory_module('memory_import_sources').directory(profile,request['selection']['identifier'])
    if state!='verified' or plan['snapshot']!=str(expected):
        raise ReleaseRejected('The verified provider return changes its current operation binding')
    operation=source.memory_module('memory_return').MemoryReturn(configuration,
        installation_lease=installation_lease,operation_id=identifier)
    inner,phase,_=operation._load(expected,plan['return_signature'],owner)
    if (phase['state']!='configured' or inner['export_signature']!=request['selection']['signature']
            or inner['export_plan_signature']!=request['selection']['plan_signature']):
        raise ReleaseRejected('The provider return loses its reviewed export binding')
    operation._native_current(inner)
    return {'return_identifier':identifier,'return_signature':signature,'native_signature':inner['target_signature']}


def software(profile, installed, generation, native, runtime, generated, *, workspace, pulse, recorded=None):
    from .release_programs import launcher_script,publish
    from .removal_configuration import configuration,environment
    from .removal_consumers import hooks
    profile,installed,generated=map(Path,(profile,installed,generated))
    import json
    hooks(json.loads(native['settings']),profile,installed)
    directories={profile/'plugins'/name:None for name in ('lifeos','lifeos-hook-bridge','lifeos-release-manager')}
    files={**native['files'],pulse:None,generation['bun']:None,
        **{profile/name:None for name in ('lifeos-memory.json','lifeos-installation.json','integration-release.json')}}
    from .release_programs import fingerprint
    expected={path:fingerprint(path,allow_links=path in native['dependencies']) for path in (*directories,*files,*native['dependencies'],
        installed/'settings.json',profile/'config.yaml',profile/'.env',*generation['launchers'])}
    expected.update(native.get('before',{}));expected.update(generation['launchers'])
    if 'bun_identity' in generation:expected[generation['bun']]=generation['bun_identity']
    publish(generated/'settings.json',native['settings']);files[installed/'settings.json']=generated/'settings.json'
    publish(generated/'config.yaml',configuration(_input(profile/'config.yaml',expected),installed,recorded))
    files[profile/'config.yaml']=generated/'config.yaml'
    path=profile/'.env'
    if path.exists() or path.is_symlink():
        publish(generated/'environment',environment(_input(path,expected),profile,workspace))
        files[path]=generated/'environment'
    for path in generation['launchers']:
        name=path.name if path.name in {'hermes','hermes-agent','hermes-acp'} else 'hermes'
        target=Path(runtime)/'bin'/name
        publish(generated/name,launcher_script(str(target)),0o700)
        files[path]=generated/name
    if profile/'.env' not in files:expected.pop(profile/'.env')
    return directories,files,native['dependencies'],expected


def _input(path, expected):
    import hashlib
    from .release_programs import fingerprint
    data=path.read_bytes()
    identity=expected[path]
    if (identity is None or identity['type']!='file' or hashlib.sha256(data).hexdigest()!=identity['sha256']
            or fingerprint(path)!=identity):
        raise ReleaseRejected('A current removal input changes during its transformation')
    return data


def _encoded(value):
    import json
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def _consumers(profile, installed, services, *, workflow=None, source=None):
    from . import removal_consumers
    admitted=services._admission()
    known=set()
    for role in services.units:
        values,_=services._inspect(role)
        known.update([Path(values['FragmentPath']),*map(Path,values['DropInPaths'].split())])
    coordinator=removal_consumers.coordinator(profile,workflow) if workflow is not None else None
    groups={item['control_group'] for item in admitted['services'].values() if item['control_group']}
    if coordinator is not None:
        known.add(coordinator['fragment']);known.update(coordinator['dropins']);groups.add(coordinator['group'])
    removal_consumers.unit_files(profile,installed,known=known,coordinator=coordinator)
    removal_consumers.processes(profile,installed,groups=groups)
    if source is not None:
        # An in-place removal changes the Hermes source, so every process that runs it must be a stopped unit.
        from .consumer_scan import source_consumers
        from .inplace_preparation import state_directory
        found=source_consumers(source,state_directory(source),excluded_groups=groups)
        if found:
            raise ReleaseRejected('Close these Hermes processes before removal: '+', '.join(
                item['command']+' ('+str(item['pid'])+')' for item in found))
    if workflow is not None and removal_consumers.coordinator(profile,workflow)!=coordinator:
        raise ReleaseRejected('The admitted removal coordinator changes during consumer inspection')


def prepare(profile, job, selected, *, owner, source, configuration, installation_lease=None):
    import hashlib
    import shutil
    from .cli import profile_directory
    from .release_catalog import _directory
    from .release_programs import ProgramTransaction,fingerprint,publish
    from .release_stage import prepare_runtime,runtime_source_fingerprint,sha,validate_files
    from . import inplace_removal,removal_generation,removal_inventory,removal_ownership
    from .host_record import record_path
    from .inplace_services import profile_units
    from .removal_recovery import basic_settings
    from .removal_services import RemovalServices
    from .removal_runtime import identity as runtime_identity,launchers
    if selected.get('disable_discord') is not True:
        raise ReleaseRejected('Complete removal requires explicit review of Discord disablement')
    profile=profile_directory(profile);job=_directory(job)
    if job.parent!=profile/'.lifeos-portability':raise ReleaseRejected('Removal preparation requires its fixed profile workflow')
    lock=source.memory_module('installation_lock').installation_lock
    with lock(profile,lease=installation_lease) as lease:
        binding=returned(profile,selected['identifier'],selected['signature'],owner=owner,
            source=source,configuration=configuration,installation_lease=lease)
        policy=configuration.load();installed=Path(policy['root'])
        # A LifeOS host record selects the in-place removal, which restores the patched host in place.
        inplace=record_path(profile).exists() or record_path(profile).is_symlink()
        generation=(inplace_removal.selected if inplace else removal_generation.selected)(profile,installed,bridge=source)
        host=generation['record']['source'] if inplace else None
        settings=basic_settings(profile)
        if owner!='dashboard:basic:'+settings['username']:
            raise ReleaseRejected('The current dashboard password account must own standalone removal recovery')
        root=profile/'.lifeos-releases'
        for sibling in root.iterdir():
            if not sibling.is_dir() or not (sibling/'status.json').is_file():continue
            state=read_private(sibling/'status.json')['state']
            if state.startswith('queued-') or state in {'preparing','applying','recovering','restoring','recovery_required'}:
                raise ReleaseRejected('Finish or recover the pending complete release before removal')
        units=profile_units(profile) if inplace else None
        services=source.memory_module('profile_services').ProfileServices(profile,installed,units=units,
            roles=None if units is None else tuple(units),installation_lease=lease)
        _consumers(profile,installed,services,workflow=job,source=host)
        removal_ownership.guard(profile,installed,bridge=source)
        pulse=removal_ownership.pulse(profile,installed)
        package=generation['package']
        if not inplace:
            dashboard=generation['job']/'download/hermes-dashboard.tgz'
            if sha(dashboard)!=generation['request']['certificate'].get('hermes_dashboard_sha256'):
                raise ReleaseRejected('The stock dashboard differs from the qualified release asset')
            if 'stock_hermes' not in generation['manifest']:
                raise ReleaseRejected('Install a complete release with qualified stock removal support first')
        stage=job/'removal';stage.mkdir(mode=0o700)
        runtime_root=None
        if not inplace:
            runtime_root=job/'stock-runtime';runtime_root.mkdir(mode=0o700)
            runtime=prepare_runtime(runtime_root,package,dashboard,profile,stock=True)
            launchers(runtime_root)
        for name,files,origin in (('recovery-bridge',generation['bridge_files'],profile/'plugins/lifeos-hook-bridge'),
                ('recovery-manager',generation['manager_files'],profile/'plugins/lifeos-release-manager')):
            validate_files(origin,files)
            shutil.copytree(origin,stage/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            validate_files(stage/name,files,forbid_bytecode=True)
        binding=returned(profile,selected['identifier'],selected['signature'],owner=owner,
            source=source,configuration=configuration,installation_lease=lease)
        _consumers(profile,installed,services,workflow=job,source=host)
        guard_identity=removal_ownership.guard(profile,installed,bridge=source)
        pulse_identity=fingerprint(pulse)
        if removal_ownership.pulse(profile,installed)!=pulse:
            raise ReleaseRejected('The current Pulse ownership changes during preparation')
        native=removal_inventory.native(installed,generation['native_source'],generation['reference'],bridge=source)
        workspace=source.memory_module('lifeos_installation').selection(profile).workspace
        generated=stage/'generated';generated.mkdir(mode=0o700)
        mount=source.memory_module('mount_transaction')
        for name in ('config.yaml','.env'):
            data,metadata=mount._read(profile/name)
            if data is not None and metadata['mode'] & 0o077:
                raise ReleaseRejected('The current configuration and environment require private owner permissions')
        recorded=inplace_removal.recorded_configuration(profile) if inplace else None
        directories,files,dependencies,expected=software(profile,installed,generation,native,runtime_root,generated,
            workspace=workspace,pulse=pulse,recorded=recorded)
        if inplace:
            host_directories,host_files,host_expected=inplace_removal.host_plan(profile,generation['record'],
                generation['originals'],stage)
            directories.update(host_directories);files.update(host_files);expected.update(host_expected)
        programs=ProgramTransaction(stage/'programs')
        expected[profile/'plugins/lifeos']=guard_identity;expected[pulse]=pulse_identity
        for name in ('lifeos-hook-bridge','lifeos-release-manager'):
            retained=stage/('recovery-bridge' if name=='lifeos-hook-bridge' else 'recovery-manager')
            expected[profile/'plugins'/name]=fingerprint(retained)
        programs.prepare(directories=directories,files=files,dependencies=dependencies,expected_before=expected)
        service_signature=RemovalServices(services,stage/'services.json').prepare(removed=[pulse])
        policy=configuration.load();configuration.check_owner(policy,owner)
        encoded_policy=_encoded(policy);publish(stage/'owner-policy.json',encoded_policy)
        plan={'format':1,'profile':str(profile),'root':str(installed),'identifier':job.name,'owner':owner,
            'workspace':str(workspace),'bridge_files':generation['bridge_files'],'manager_files':generation['manager_files'],
            'owner_policy_sha256':hashlib.sha256(encoded_policy).hexdigest(),'program_entries_sha256':programs.entries_digest(),
            'service_signature':service_signature,'generation':generation['job'].name,'disable_discord':True,**binding}
        if inplace:
            record=generation['record']
            plan.update(host={'source':record['source'],'commit':record['commit'],'label':record['label'],
                'operation':record['operation']},service_units=units)
            runtime=inplace_removal.runtime(plan)
            stock_commit=record['commit']
            if recorded is not None:
                from ruamel.yaml import YAML
                from .host_configuration import restore
                _,retained_keys=restore(YAML(typ='safe').load((profile/'config.yaml').read_text()) or {},recorded)
                plan['configuration_retained']=retained_keys
        else:
            plan.update(stock_runtime=runtime,stock_runtime_source=runtime_source_fingerprint(runtime_root/'hermes'),
                stock_runtime_manifest_sha256=sha(runtime_root/'manifest.json'),
                stock_runtime_execution=runtime_identity(runtime_root))
            stock_commit=runtime['stock_source']['commit']
        recovery=_recovery_command(profile,job,runtime)
        publish(stage/'recover',recovery,0o700)
        plan['recovery_command_sha256']=hashlib.sha256(recovery).hexdigest()
        signature=hashlib.sha256(_encoded(plan)).hexdigest()
        # The helper reads the bound plan signature from the private marker after owner application.
        publish(stage/'plan.json',_encoded(plan));publish(stage/'operation.json',_encoded({'signature':signature,'state':'ready'}))
        programs.check_prepared()
        from .removal_state import prepared
        prepared(profile,job.name,signature)
        return {'state':'ready','signature':signature,'kind':'removal','application_verified':False,
            'native_data_retained':True,'builtin_memory_retained':True,'discord_disabled':True,
            'stock_commit':stock_commit,'stock_patches':0,
            'program_targets':len(programs.entries()),'recovery_command':str(stage/'recover'),
            'configuration_retained':plan.get('configuration_retained',[])}


def _recovery_command(profile, job, runtime):
    import shlex
    from hermes_cli import _launchers
    code=Path(__file__).with_name('removal_bootstrap.py').read_text()+('\n'
        'selected=validate(sys.argv[1],sys.argv[2])\n'
        'sys.argv=[selected["worker"],*sys.argv[1:],selected["signature"]]\n'
        'runpy.run_path(selected["worker"],run_name="__main__")\n')
    if runtime.get('kind')=='host':
        from .inplace_removal import command as host_command
        command=host_command(runtime,[profile,job.name],code=code)
    else:
        command=_launchers.runtime_command(Path(runtime['source']),[str(profile),job.name],
            code=code,python=runtime['python'])
        from .removal_runtime import command as stock_command
        command=stock_command(command,runtime)
    return ('#!/bin/sh\nexec '+shlex.join(command)+' "$@"\n').encode()
