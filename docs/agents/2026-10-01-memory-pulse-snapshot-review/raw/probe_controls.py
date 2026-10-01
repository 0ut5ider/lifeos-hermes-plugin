import hashlib,json,os,time
from test_memory_pulse import MemoryPulseTests
from test_memory_native import OWNER,READER
from lifeos_hook_bridge.memory_pulse import snapshot

def fixture():
    c=MemoryPulseTests();c.setUp();return c

c=fixture()
try:
    path=c.obs/'review-state.json';os.mkfifo(path)
    start=time.monotonic()
    try:snapshot(c.fixture.fixture.fixture.memory,READER,'state')
    except RuntimeError as e:print(json.dumps({'control':'restricted-before-FIFO-read','seconds':time.monotonic()-start,'error':str(e)}))
    else:raise AssertionError('restricted scope admitted')
finally:c.doCleanups()

c=fixture()
try:
    f=c.fixture.fixture.fixture
    marker='Synthetic retired pulse output'
    saved=f.remember('RULE: '+marker,'controls-old','principal')
    f.memory.forget(OWNER,saved['reference'],'controls-forget')
    now='2026-10-01T02:03:04.000Z'
    escaped=json.dumps({'content':marker}).replace('Synthetic','\\u0053ynthetic')
    (c.obs/'review-state.json').write_text(json.dumps({'turn_count_since_last_review':4,'last_review_at':now,'last_message_at':now,'pending_review':True,'error':{'ts':marker,'content':escaped}}))
    (c.obs/'memory-health.jsonl').write_text(json.dumps({'ts':now,'overall':'critical','counts':{'critical':2},'findings':[{'severity':'critical','message':escaped}]})+'\n')
    (c.obs/'reviewer-fires.jsonl').write_text(''.join(json.dumps({'ts':now,'reason':marker,'n':i})+'\n' for i in range(205)))
    (c.obs/'pending-proposals.jsonl').write_text(''.join(json.dumps({'ts':now,'id':str(i),'status':'pending','edit':escaped})+'\n' for i in range(55)))
    for i in range(21):
        d=c.obs/f'reviewer-runs/2026-10-01T00-00-{i:02d}-000Z';d.mkdir(parents=True)
        (d/'dispatch.log').write_text('Items: 2 (succeeded=1 failed=1)\nBy type: {"memory":2}\n[0] OK memory: /synthetic/Synthetic-retired-pulse-output.md\n')
    def hashes():return {str(p.relative_to(f.home)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (f.home/'.config/LIFEOS/USER').rglob('*') if p.is_file() and not p.name.endswith(('.sqlite3','.sqlite3-wal','.sqlite3-shm','.lock'))}
    before=hashes()
    raw={v:f.memory._native('pulse_snapshot',view=v)['snapshot'] for v in ('snapshot','state','health','runs')}
    out={v:c.snapshot(v) for v in raw}
    assert len(out['snapshot']['recentRuns'])==10 and len(out['runs'])==20
    assert out['snapshot']['lastFireCount']==200 and len(out['snapshot']['recentFires'])==5
    assert out['snapshot']['pendingProposals']==50 and len(out['snapshot']['proposalsRecent'])==5
    assert out['snapshot']['derivedState']==raw['snapshot']['derivedState']=='unhealthy_critical'
    assert out['health']['counts']==raw['health']['counts']=={'critical':2}
    assert out['state']['last_review_at']==now
    assert marker not in json.dumps(out) and 'Synthetic-retired-pulse-output' not in json.dumps(out)
    after=hashes()
    differences=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)]
    print(json.dumps({'hash_differences':differences}))
    assert all('/MEMORY/STATE/' in k for k in differences)
    print(json.dumps({'control':'native-cardinality-retirement-readonly','native':raw,'governed':out,'hashes_unchanged':True},indent=2))
finally:c.doCleanups()

for target in ('cadence','runs'):
    c=fixture()
    try:
        private=c.root/'LIFEOS/USER/CONFIG/private';private.mkdir()
        if target=='cadence':
            p=c.root/'LIFEOS/USER/CONFIG/memory-review.json';(private/'cadence.json').write_text('{"turn_threshold":2}');p.symlink_to(private/'cadence.json')
        else:
            p=c.obs/'reviewer-runs';p.symlink_to(private)
        try:c.snapshot()
        except RuntimeError as e:print(json.dumps({'control':target+'-redirect','error':str(e)}))
        else:raise AssertionError('redirect accepted')
    finally:c.doCleanups()
