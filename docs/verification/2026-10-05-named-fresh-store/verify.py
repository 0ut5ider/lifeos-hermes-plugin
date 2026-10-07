# ABOUTME: Verifies the named-store evidence against its artifacts and recorded implementation.
# ABOUTME: Checks the reviewed dependency catalog and optional complete native source hashes.
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--native-source',type=Path)
    selected=parser.parse_args()
    bundle=Path(__file__).resolve().parent
    project=bundle.parents[2]
    artifacts=json.loads((bundle/'artifact-hashes.json').read_text())
    for name,expected in artifacts.items():
        if digest(bundle/name)!=expected:raise ValueError('An evidence artifact changes: '+name)
    sources=json.loads((bundle/'source-hashes.json').read_text())
    for name,expected in sources.items():
        if digest(project/name)!=expected:raise ValueError('A recorded source changes: '+name)
    programs=json.loads((bundle/'native-program-hashes.json').read_text())
    if selected.native_source:
        for name,expected in programs.items():
            if digest(selected.native_source/name)!=expected:raise ValueError('A native program changes: '+name)
    if (bundle/'named-store.done').read_text().strip()!='0':raise ValueError('The native test does not pass')
    print(json.dumps({'artifacts':len(artifacts),'sources':len(sources),
        'native_programs':len(programs),'native_source_checked':selected.native_source is not None}))


if __name__=='__main__':
    main()
