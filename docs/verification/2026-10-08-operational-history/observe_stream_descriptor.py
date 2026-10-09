# ABOUTME: Measures Bun read-stream ownership of borrowed anonymous file descriptors.
# ABOUTME: Compares descriptor survival before and after the actual stream destroy call.
import json
import os
from pathlib import Path
import subprocess
import tempfile

program = '''import {createReadStream,fstatSync,openSync} from "node:fs";
import {createInterface} from "node:readline";
const inherited=Number(process.argv[2]);const mode=process.argv[3];
function alive(fd:number):boolean {try{fstatSync(fd);return true;}catch{return false;}}
const origin=openSync(`/proc/self/fd/${inherited}`,"r");
const stream=mode==="borrowed"?createReadStream("",{fd:origin,autoClose:false,start:0}):createReadStream(`/proc/self/fd/${origin}`);
const lines=createInterface({input:stream,crlfDelay:Infinity});
let count=0;let readError=false;
try{for await(const line of lines){JSON.parse(line);count++;}}catch{readError=true;}
const beforeDestroy=alive(origin);
lines.close();stream.destroy();
const afterDestroy=alive(origin);
await new Promise<void>(resolve=>setImmediate(resolve));
console.log(JSON.stringify({mode,count,readError,beforeDestroy,afterDestroy,afterTick:alive(origin)}));
'''

with tempfile.TemporaryDirectory(prefix='lifeos-descriptor-observation-') as directory:
    script = Path(directory) / 'descriptor.ts'
    script.write_text(program)
    with tempfile.TemporaryFile('w+b') as snapshot:
        snapshot.write((json.dumps({'content': 'Synthetic streamed descriptor record'}) + '\n').encode() * 5000)
        snapshot.flush()
        with os.fdopen(os.open(f'/proc/self/fd/{snapshot.fileno()}', os.O_RDONLY), 'rb') as reader:
            observed = []
            for mode in ['borrowed', 'owned']:
                for iteration in range(40):
                    result = subprocess.run(['bun', '--no-install', str(script), str(reader.fileno()), mode],
                        capture_output=True, text=True, timeout=30, pass_fds=(reader.fileno(),))
                    if result.returncode or result.stderr: raise RuntimeError(result.stderr)
                    observed.append({'iteration': iteration, **json.loads(result.stdout)})
            print(json.dumps(observed))
