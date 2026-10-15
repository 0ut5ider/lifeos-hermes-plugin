# ABOUTME: Restores the exact reviewed environment of one failed disposable removal before rollback.
# ABOUTME: Requires actual owner authentication and the measured single-newline difference without touching memory.
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import types

home=Path('/home/lifeos-hermes');profile=home/'.hermes'
if os.getuid()!=1000 or Path.home()!=home:raise RuntimeError('Use the disposable guest owner')
os.umask(0o077)
identifier='4bf8386002c3402a8f0ffb933fb8484c'
signature='1623c1663530c78ba46cea52121c6f62563e03f56728a8eb5f159177b3a02cb2'
job=profile/'.lifeos-portability'/identifier
package=types.ModuleType('portability_environment_repair')
package.__path__=[str(job/'removal/recovery-manager')];sys.modules[package.__name__]=package
state=importlib.import_module(package.__name__+'.removal_state')
source,configuration,selected,plan=state.retained(profile)
if selected!=job or plan['signature']!=signature:raise RuntimeError('The reviewed disposable removal changes')
credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
owner=importlib.import_module(package.__name__+'.removal_recovery').authenticate(
    profile,credentials['username'],credentials['password'],plan['owner'])
del credentials
programs=importlib.import_module(package.__name__+'.release_programs')
receipt={'workflow':identifier,'operator_repair':True,'unaided_recovery':False,'daily_changed':False,
    'owner_authenticated':True,'change':'Restore the exact reviewed environment after measured stock final-LF normalization.'}
with source.memory_module('installation_lock').installation_lock(profile) as lease:
    publication=importlib.import_module(package.__name__+'.removal_publication').RemovalPublication(profile,signature,installation_lease=lease)
    publication._owner(owner)
    if publication._load()!='verification_required':raise RuntimeError('The removal is not the measured failed publication')
    if json.loads((job/'status.json').read_bytes())['state']!='interrupted':raise RuntimeError('A workflow worker is active')
    if any((profile/'plugins'/name).exists() for name in ('lifeos','lifeos-hook-bridge','lifeos-release-manager')):
        raise RuntimeError('The reviewed active software is not removed')
    expected_memory={'MEMORY.md':'2f01494c8ea26fbc74cd7144a14ec493b80c936461338d5d12b362802a114129',
        'USER.md':'7d9e0df1fd2bcba72f3bdcb2b73782bcf15318ed79c923c2e999014710f0c2db'}
    def memory_hashes():return {name:hashlib.sha256((profile/'memories'/name).read_bytes()).hexdigest() for name in expected_memory}
    if memory_hashes()!=expected_memory:raise RuntimeError('Current memory differs from the measured retained files')
    target=profile/'.env';prepared=job/'removal/generated/environment'
    entry=next(item for item in publication.programs._load()['entries'] if item['target']==str(target))
    original=target.read_bytes();reviewed=prepared.read_bytes()
    if original!=reviewed+b'\n' or programs.fingerprint(prepared)!=entry['after']:
        raise RuntimeError('The current environment differs beyond the measured single final LF')
    changed=[item['target'] for item in publication.programs._load()['entries']
        if programs.fingerprint(item['target'],allow_links=item['allow_links'])!=item['after']]
    if changed!=[str(target)]:raise RuntimeError('Another reviewed program target changes')
    folder=home/'install-input/environment-operator-repair';folder.mkdir(mode=0o700)
    programs.publish(folder/'before.env',original,0o600)
    publication.services.stop(plan['service_signature'])
    if target.read_bytes()!=original:raise RuntimeError('The environment changes during service drain')
    programs.publish(target,reviewed,entry['after']['mode'])
    publication.programs.check_applied()
    if memory_hashes()!=expected_memory:raise RuntimeError('Memory changes during environment repair')
    receipt.update(exact_reviewed_targets_restored=True,services_drained=True,builtin_memory_unchanged=True,
        before_bytes=len(original),after_bytes=len(reviewed))
    programs.publish(folder/'receipt.json',(json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps(receipt))
