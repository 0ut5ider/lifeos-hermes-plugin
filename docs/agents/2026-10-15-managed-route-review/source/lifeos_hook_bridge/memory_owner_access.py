# ABOUTME: Binds reviewed local owner access to the actual selected Hermes model route.
# ABOUTME: Preserves other grants and refuses conflicting local identities or restricted destinations.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from .memory_access import MemoryUnavailable
from .memory_context import route_identity
from .memory_policy import CATEGORIES


def _route(profile, expected):
    import hermes_constants
    from hermes_cli import _launchers
    host=Path(hermes_constants.__file__).resolve().parent
    code='''import contextlib,hashlib,io,json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
path=Path(sys.argv[2])/'config.yaml'
def unchanged():
 if hashlib.sha256(path.read_bytes()).hexdigest()!=sys.argv[3]:raise RuntimeError('Configuration changes')
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
 unchanged()
 from dotenv import load_dotenv
 load_dotenv(path.parent/'.env',override=False)
 from hermes_cli.config import load_config_readonly
 from hermes_cli.runtime_provider import resolve_runtime_provider
 config=load_config_readonly();model=config.get('model',{})
 model={'default':model} if isinstance(model,str) else model
 if not isinstance(model,dict) or not isinstance(model.get('default'),str) or not model['default']:
  raise RuntimeError('Select a model before ownership activation')
 runtime=resolve_runtime_provider(requested=model.get('provider'),target_model=model['default'],
  explicit_api_key=model.get('api_key'),explicit_base_url=model.get('base_url'))
 unchanged()
 result={key:runtime.get(key) for key in ('provider','base_url','api_mode')}
 result['model']=model['default']
print(json.dumps(result))
'''
    environment=dict(os.environ,HERMES_HOME=str(profile))
    try:
        command=_launchers.runtime_command(host,[str(host),str(profile),hashlib.sha256(expected).hexdigest()],
            code=code,python=sys.executable,home=profile)
        command.insert(1,'-B')
        result=subprocess.run(command,env=environment,capture_output=True,text=True,timeout=45)
        if result.returncode or result.stderr or len(result.stdout)>16384:raise ValueError('Unavailable route')
        route=json.loads(result.stdout)
        if (not isinstance(route,dict) or set(route)!={'provider','model','base_url','api_mode'}
                or any(not isinstance(value,str) or not value or len(value)>4096 for value in route.values())):
            raise ValueError('Invalid route')
        identity=route_identity(**route)
        if identity=='unknown':raise ValueError('Unknown route')
    except (ValueError,OSError,subprocess.TimeoutExpired):
        raise MemoryUnavailable('Ownership activation requires an available current Hermes model route') from None
    return {**route,'model_route':identity}


def reviewed(configuration, profile, expected):
    route=_route(profile,expected)
    selected=json.loads(json.dumps(configuration));principal=selected['principal']
    account='terminal:'+str(os.getuid());destination='terminal:'+str(profile)
    accounts=selected.setdefault('accounts',{});destinations=selected.setdefault('destinations',{})
    if accounts.get(account,principal)!=principal:
        raise MemoryUnavailable('The local Hermes account belongs to another principal')
    grant=destinations.get(destination)
    if grant is not None and (grant.get('visibility')!='private' or grant.get('participants')!=[principal]
            or set(grant.get('read',[]))!=CATEGORIES or set(grant.get('write',[]))!=CATEGORIES
            or '*' not in grant.get('projects',[])):
        raise MemoryUnavailable('Review the existing restricted local memory grant before ownership activation')
    if grant is None:
        grant={'visibility':'private','participants':[principal],'read':sorted(CATEGORIES),
            'write':sorted(CATEGORIES),'projects':['*'],'model_routes':[]}
        destinations[destination]=grant
    accounts[account]=principal
    grant['model_routes']=sorted(set([*grant.get('model_routes',[]),route['model_route']]))
    selected['ownership_enabled']=True
    review={'account':account,'destination':destination,
        **{key:route[key] for key in ('provider','model','model_route')}}
    return selected,review
