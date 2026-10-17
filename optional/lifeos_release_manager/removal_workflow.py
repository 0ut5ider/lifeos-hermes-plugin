# ABOUTME: Selects and recovers the exact owner-reviewed complete software removal.
# ABOUTME: Uses retained manager sources with stock Hermes, or with the restored in-place host, after removal.
import json
import os
from pathlib import Path

from .cli import read_private
from .release_catalog import ReleaseRejected
from .release_programs import ProgramTransaction,publish,sync_directory
from .removal_state import prepared,retained


def _encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def launch_sources(profile, job, signature):
    source,configuration,selected,plan=prepared(profile,job.name,signature)
    if selected!=job:raise ReleaseRejected('Removal launch changes its fixed workflow directory')
    return job/'removal/recovery-manager/memory_workflow_worker.py',_runtime(job,plan)


def _runtime(job, plan):
    if 'host' in plan:
        from .inplace_removal import runtime
        return runtime(plan)
    return _stock(job,plan)


def _stock(job, plan):
    from .release_stage import runtime_source_fingerprint,sha
    from .removal_runtime import identity
    root=job/'stock-runtime';runtime=plan.get('stock_runtime',{})
    for key,path in {'python':root/'python-environment/bin/python','source':root/'hermes','hermes':root/'bin/hermes'}.items():
        if runtime.get(key)!=str(path):raise ReleaseRejected('Removal changes its prepared stock runtime paths')
    if (runtime.get('integration') is not False or runtime_source_fingerprint(root/'hermes')!=plan.get('stock_runtime_source')
            or sha(root/'manifest.json')!=plan.get('stock_runtime_manifest_sha256')
            or identity(root)!=plan.get('stock_runtime_execution')):
        raise ReleaseRejected('The prepared stock runtime differs from the exact owner review')
    return runtime


def _archive_marker(profile, job, signature):
    marker=profile/'.lifeos-removal.json'
    if not marker.exists() and not marker.is_symlink():return
    _,_,selected,plan=retained(profile)
    if selected!=job or plan['signature']!=signature:
        raise ReleaseRejected('The current removal marker belongs to another owner review')
    history=profile/'.lifeos-removal-history';history.mkdir(mode=0o700,exist_ok=True)
    from .release_catalog import _directory
    _directory(history)
    target=history/(job.name+'.json')
    if target.exists() or target.is_symlink():raise ReleaseRejected('The retained removal history already contains this selection')
    os.rename(marker,target);sync_directory(history);sync_directory(profile)


def execute(profile, job, selected, action, signature, *, owner, source, configuration, installation_lease):
    from .removal_preparation import prepare,returned,_consumers
    from .removal_publication import RemovalPublication
    profile,job=Path(profile),Path(job)
    if action=='prepare':
        return prepare(profile,job,selected,owner=owner,source=source,configuration=configuration,
            installation_lease=installation_lease)
    retained_source,retained_configuration,fixed,plan=prepared(profile,job.name,signature)
    retained_configuration.check_owner(retained_configuration.load(),owner)
    if (fixed!=job or plan['owner']!=owner or plan.get('return_identifier')!=selected['identifier']
            or plan.get('return_signature')!=selected['signature'] or plan.get('disable_discord') is not True):
        raise ReleaseRejected('Removal loses its exact owner and provider-return selection')
    operation=read_private(job/'removal/operation.json')
    if operation.get('signature')!=signature:raise ReleaseRejected('Removal loses its reviewed publication state')
    marker=profile/'.lifeos-removal.json'
    selected_live=marker.exists() or marker.is_symlink()
    if operation['state']=='rolled_back':
        _archive_marker(profile,job,signature)
        return {'signature':signature,'state':'rolled_back','application_verified':False,
            'builtin_memory_retained':True,'native_data_retained':True}
    if not selected_live and action=='rollback':
        if operation['state']!='ready':raise ReleaseRejected('The interrupted removal loses its live selection')
        return {'signature':signature,'state':'cancelled','application_verified':False,'native_data_retained':True}
    if not selected_live and action=='recover':
        if operation['state']!='ready':raise ReleaseRejected('The interrupted removal loses its owner marker')
        return {**read_private(job/'review.json'),'state':'ready','application_verified':False}
    runtime=_runtime(job,plan)
    host=plan['host']['source'] if 'host' in plan else None
    units=plan.get('service_units')
    if not selected_live:
        if operation['state']!='ready':raise ReleaseRejected('The interrupted removal loses its owner marker')
        returned(profile,selected['identifier'],selected['signature'],owner=owner,source=source,
            configuration=configuration,installation_lease=installation_lease)
        services=source.memory_module('profile_services').ProfileServices(profile,Path(plan['root']),units=units,
            roles=None if units is None else tuple(units),installation_lease=installation_lease)
        _consumers(profile,Path(plan['root']),services,workflow=job,source=host)
        ProgramTransaction(job/'removal/programs',expected_entries_sha256=plan['program_entries_sha256']).check_prepared()
        publish(marker,_encoded({'format':1,'workflow':job.name,'signature':signature}))
    else:
        _,_,current,current_plan=retained(profile)
        if current!=job or current_plan['signature']!=signature:raise ReleaseRejected('Another removal owns the live selection')
    publication=RemovalPublication(profile,signature,installation_lease=installation_lease)
    if action=='rollback':
        result=publication.rollback(account=owner);_archive_marker(profile,job,signature)
        return result
    publication.apply(account=owner)
    from .memory_workflow import _probe
    def probe(expected):
        _runtime(job,plan)
        proof=_probe(profile,publication.source,expected,runtime=runtime,output=job/'probe-output.txt')
        _runtime(job,plan)
        return proof
    result=publication.verify(probe,account=owner)
    commit=plan['host']['commit'] if host is not None else runtime['stock_source']['commit']
    if host is not None:
        result['dependencies']=read_private(job/'removal/dependency-removal-packages.json')
    return {**result,'stock_commit':commit,'stock_patches':0,
        'recovery_command':str(job/'removal/recover'),'discord_disabled':True}
