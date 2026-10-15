# ABOUTME: Resolves fixed private recovery sources after the active LifeOS plugins and policy are removed.
# ABOUTME: Retains the original profile grant boundary and honors live installation owner revocations.
import copy
import hashlib
import json
from pathlib import Path
import re

from .cli import profile_directory,read_private
from .release_catalog import ReleaseRejected,_directory
from .release_stage import load_bridge,validate_files


IDENTIFIER=re.compile('[0-9a-f]{32}')
SIGNATURE=re.compile('[0-9a-f]{64}')


def retained(profile):
    profile=profile_directory(profile)
    marker=read_private(profile/'.lifeos-removal.json',limit=1024)
    if (not isinstance(marker,dict) or set(marker)!={'format','workflow','signature'} or marker['format']!=1
            or not isinstance(marker['workflow'],str) or IDENTIFIER.fullmatch(marker['workflow']) is None
            or not isinstance(marker['signature'],str) or SIGNATURE.fullmatch(marker['signature']) is None):
        raise ReleaseRejected('The removal recovery selection has invalid private metadata')
    job=profile/'.lifeos-portability'/marker['workflow'];_directory(job)
    stage=job/'removal';_directory(stage)
    plan=read_private(stage/'plan.json')
    data=json.dumps(plan,sort_keys=True,separators=(',',':')).encode()
    if (hashlib.sha256(data).hexdigest()!=marker['signature'] or not isinstance(plan,dict)
            or plan.get('format')!=1 or plan.get('profile')!=str(profile) or plan.get('identifier')!=job.name
            or not isinstance(plan.get('owner'),str) or not plan['owner'].startswith('dashboard:')
            or not isinstance(plan.get('root'),str) or not Path(plan['root']).is_absolute()):
        raise ReleaseRejected('The retained removal plan differs from its exact owner review')
    validate_files(stage/'recovery-bridge',plan['bridge_files'],forbid_bytecode=True)
    validate_files(stage/'recovery-manager',plan['manager_files'],forbid_bytecode=True)
    policy_path=stage/'owner-policy.json'
    policy=read_private(policy_path)
    if hashlib.sha256(json.dumps(policy,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=plan['owner_policy_sha256']:
        raise ReleaseRejected('The retained recovery owner policy changes')
    source=load_bridge(stage/'recovery-bridge')
    original=source.memory_module('memory_service').MemoryConfiguration
    original.validate(policy)
    original.check_owner(policy,plan['owner'])
    if policy['root']!=plan['root'] or policy.get('ownership_enabled') is not False:
        raise ReleaseRejected('The retained policy does not prove a returned installation')
    class RecoveryConfiguration(original):
        def load(self):
            if self.path.exists() or self.path.is_symlink():
                value=super().load()
                if value['root']!=plan['root']:
                    raise ReleaseRejected('The live owner policy selects another installation')
                return value
            current=read_private(policy_path)
            if hashlib.sha256(json.dumps(current,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=plan['owner_policy_sha256']:
                raise ReleaseRejected('The retained recovery owner policy changes')
            self.validate(current)
            return copy.deepcopy(current)

        def save(self,value):
            raise ReleaseRejected('Retained removal authority cannot publish native configuration')

        def update(self,change):
            raise ReleaseRejected('Retained removal authority cannot publish native configuration')

    return source,RecoveryConfiguration(profile/'lifeos-memory.json'),job,{**plan,'signature':marker['signature']}
