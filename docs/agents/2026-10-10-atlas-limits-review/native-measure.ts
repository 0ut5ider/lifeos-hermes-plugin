// ABOUTME: Measures deterministic synthetic Atlas graph growth with real native transactions.
// ABOUTME: Records SQLite, snapshot, transport, and table sizes without personal data.
import {mkdtempSync, rmSync, statSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
const native = '/home/outsider/.cache/lifeos-atlas-20261010/native-sync-final/LifeOS/install/LIFEOS/ATLAS/';
const root=mkdtempSync(join(tmpdir(),'atlas-limits-native-'));
process.env.ATLAS_DIR=join(root,'state'); process.env.LIFEOS_MEMORY_INTERNAL='1';
const {Store}=await import(native+'Store.ts');
const {collectGear}=await import(native+'collectors/Gear.ts');
const {collectProjects}=await import(native+'collectors/Projects.ts');
const NativeDate=Date;
let clock=Date.parse('2026-10-10T12:00:00Z');
class SyntheticDate extends NativeDate {constructor(...args: any[]){super(...(args.length ? args : [clock]) as [any]);} static now(){return clock;}}
globalThis.Date=SyntheticDate as typeof Date;
const gear=(n:number,generation=0)=>'## Computing\n'+Array.from({length:n},(_,i)=>`| **Device ${i}** | Synthetic Machine ${generation}-${i} | daily |`).join('\n')+'\n';
const projects=(n:number,generation=0)=>'| Name | Path | URL | Deploy |\n| --- | --- | --- | --- |\n'+Array.from({length:n},(_,i)=>`| Synthetic Project ${generation}-${i} | /synthetic/project-${i} github.com/synthetic/repo-${generation}-${i} | app-${generation}-${i}.example.invalid | local |`).join('\n')+'\n';
const rows:any[]=[];const rawDir=join(process.argv[2].replace(/[^/]+$/, ''),'native-raw');const {mkdirSync}=await import('node:fs');mkdirSync(rawDir,{recursive:true});
function measure(store:any,label:string,files?:any){store.db.exec('PRAGMA wal_checkpoint(TRUNCATE)');store.db.exec('PRAGMA journal_mode=DELETE');const counts:any={};const graph:any={};for(const name of ['asset','edge','source_observation','edge_observation','sync_run','lifecycle_event']) {counts[name]=store.db.query(`SELECT COUNT(*) AS n FROM ${name}`).get().n;graph[name]=store.db.query(`SELECT * FROM ${name}`).all();}const snapshot=store.exportSnapshot();const databaseBytes=statSync(store.db.filename).size;writeFileSync(join(rawDir,label+'.graph.json'),JSON.stringify({graph,metrics:store.insights()}));writeFileSync(join(rawDir,label+'.snapshot.json'),JSON.stringify(snapshot));const snapshotText=JSON.stringify(snapshot); const pythonSnapshotBytes=Buffer.byteLength(JSON.stringify(snapshot,null,0))+countPythonSpaces(snapshot);rows.push({label,clock:new Date().toISOString(),databaseBytes,snapshotCompactBytes:Buffer.byteLength(snapshotText),snapshotPythonBytes:pythonSnapshotBytes,graphCompactBytes:Buffer.byteLength(JSON.stringify({graph,metrics:store.insights()})),base64Bytes:4*Math.ceil(databaseBytes/3),counts,sourceBytes:files?Object.fromEntries(Object.entries(files).map(([k,v])=>[k,Buffer.byteLength(v as string)])):undefined});}
function countPythonSpaces(v:any):number {if(Array.isArray(v))return Math.max(v.length-1,0)+v.reduce((s,x)=>s+countPythonSpaces(x),0);if(v!==null&&typeof v==='object'){const entries=Object.entries(v);return Math.max(entries.length-1,0)+entries.length+entries.reduce((s,[k,x])=>s+countPythonSpaces(x),0);}return 0;}
function create(label:string){return new Store(join(root,label+'.db'));}
try {
for(const [g,p] of [[0,0],[20,10],[50,20],[100,100],[300,150],[500,200],[800,0],[0,200],[0,300],[311,0],[312,0],[0,84],[0,85],[100,57],[100,58]]) {const s=create(`inventory-${g}-${p}`),files={gear:gear(g),projects:projects(p)};s.applyRun('gear','full',collectGear(files.gear));s.applyRun('projects','full',collectProjects(files.projects));measure(s,`inventory-${g}-${p}`,files);s.close();}
const s=create('unchanged');const files={gear:gear(50),projects:projects(20)};const results=[collectGear(files.gear),collectProjects(files.projects)];for(let i=1;i<=1025;i++){clock+=1000;s.applyRun('gear','full',results[0]);s.applyRun('projects','full',results[1]);if([1,10,100,200,201,202,500,1000,1023,1024,1025].includes(i))measure(s,'unchanged-'+i,files);}s.close();
const changed=create('changed');for(let i=1;i<=100;i++){clock+=1000;const g=collectGear(gear(50));g.assets.forEach((a:any)=>a.attrs.category='Synthetic revision '+i);changed.applyRun('gear','full',g);changed.applyRun('projects','full',collectProjects(projects(20)));if([1,10,100].includes(i))measure(changed,'attrs-change-'+i);}changed.close();
const churn=create('churn');for(let i=0;i<20;i++){clock+=15*86400000;churn.applyRun('gear','full',collectGear(gear(20,i)));churn.applyRun('projects','full',collectProjects(projects(10,i)));if([0,1,4,9,19].includes(i))measure(churn,'replacement-'+(i+1));}churn.close();
const obs=create('observations');const result=collectGear(gear(50));for(let i=0;i<42;i++){obs.applyRun('collector-'+i,'full',result);if([0,11,12,19,39,40,41].includes(i))measure(obs,'collectors-'+(i+1));}obs.close();
const life=create('lifecycle');const lr=collectGear(gear(20));life.applyRun('gear','full',lr);for(let i=1;i<=105;i++){clock+=3*86400000;life.applyRun('gear','full',{complete:true,assets:[],edges:[]});clock+=12*86400000;life.applyRun('gear','full',{complete:true,assets:[],edges:[]});life.applyRun('gear','full',lr);if([1,10,25,26,34,35,50,100,103,105].includes(i))measure(life,'lifecycle-cycles-'+i);}life.close();
writeFileSync(process.argv[2],JSON.stringify({native,method:'Real Store.applyRun; synthetic clock; DELETE checkpoint; all source fixtures synthetic',rows},null,2)+'\n');
}finally{rmSync(root,{recursive:true,force:true});}
