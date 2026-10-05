# Raw review data

Date: 2026-10-05. Role: independent reviewer of unreviewed memory modules. Question: defects in requested lasting-memory runtime modules at c083037. Model: GPT-6 (Codex).

## Commands run

1. `git -C /home/outsider/Projects/Hermes_agent/LifeOS_plugin diff origin/main...c083037 --stat -- lifeos_hook_bridge patches`
2. For each input module: `git -C /home/outsider/Projects/Hermes_agent/LifeOS_plugin show c083037:lifeos_hook_bridge/<name>` and `git -C /home/outsider/Projects/Hermes_agent/LifeOS_plugin diff origin/main...c083037 -- lifeos_hook_bridge/<name>`.
3. For the patch: `git -C /home/outsider/Projects/Hermes_agent/LifeOS_plugin show c083037:patches/lifeos-memory-access.patch` and `git -C /home/outsider/Projects/Hermes_agent/LifeOS_plugin diff origin/main...c083037 -- patches/lifeos-memory-access.patch`.
4. Read numbered snapshots with `nl -ba`, `sed -n`, and searched snapshots and the patch with `rg -n`.
5. Read `memory_proposals.py` for the proposal validation call path using `git show c083037:lifeos_hook_bridge/memory_proposals.py`.
6. No test suites or network commands were run.

## Changed-file stat

```text
 lifeos_hook_bridge/cli.py                          |   72 +
 lifeos_hook_bridge/dashboard/dist/index.js         |    2 +
 lifeos_hook_bridge/dashboard/plugin_api.py         |   37 +-
 .../dependency_locks/0b910ecc5959037e628e6e43.lock |  438 ++
 .../dependency_locks/0c1b3413db5e14632bc135bf.lock |  211 +
 .../dependency_locks/1d67de528cad4b5e29b26ed8.lock |   35 +
 .../dependency_locks/3e75a2cbc0789fd335d6ffd2.lock |  773 +++
 .../dependency_locks/67188f5ef1b781ac943a2c04.lock |   17 +
 lifeos_hook_bridge/dependency_locks/catalog.json   |   67 +
 .../dependency_locks/cb7d9771ebe3fa59601058e7.lock |  307 +
 .../dependency_locks/cdb4ee2aea69cc6a83331bbe.lock |   15 +
 .../dependency_locks/d04ce1505b22cda8425a28aa.lock |   59 +
 .../dependency_locks/d2521ec9517f1c45120530f4.lock |  760 +++
 .../dependency_locks/d588cd097ed20e0586de639b.lock |   44 +
 .../dependency_locks/d6ab09ee4d6c7c76ac9d9719.lock |   39 +
 .../dependency_locks/e09cdc5de201501145f95e1d.lock |  167 +
 lifeos_hook_bridge/fresh_store.py                  |  224 +
 lifeos_hook_bridge/install_source.py               |   63 +-
 lifeos_hook_bridge/installation_lock.py            |   57 +-
 lifeos_hook_bridge/memory_access.py                |  103 +-
 lifeos_hook_bridge/memory_backup.py                |  238 +
 lifeos_hook_bridge/memory_backup_recovery.py       |  103 +
 lifeos_hook_bridge/memory_context_audit.py         |   74 +
 lifeos_hook_bridge/memory_counts.py                |   41 +
 lifeos_hook_bridge/memory_deny_hashes.py           |  149 +
 lifeos_hook_bridge/memory_derived_sync.py          |  210 +
 lifeos_hook_bridge/memory_distill.py               |  242 +
 lifeos_hook_bridge/memory_evidence.py              |  170 +
 lifeos_hook_bridge/memory_freshness.py             |  205 +
 lifeos_hook_bridge/memory_freshness_cache.py       |   54 +
 lifeos_hook_bridge/memory_freshness_migration.py   |  125 +
 lifeos_hook_bridge/memory_graph.py                 |  130 +
 lifeos_hook_bridge/memory_hermes_soul.py           |  129 +
 lifeos_hook_bridge/memory_history.py               |   10 +-
 lifeos_hook_bridge/memory_http.py                  |    3 +-
 lifeos_hook_bridge/memory_hypotheses.py            |  244 +
 lifeos_hook_bridge/memory_import.py                |  501 ++
 lifeos_hook_bridge/memory_interview.py             |  140 +
 lifeos_hook_bridge/memory_interview_scan.py        |   65 +
 lifeos_hook_bridge/memory_learning.py              |  134 +
 lifeos_hook_bridge/memory_lineage.py               |   64 +
 lifeos_hook_bridge/memory_native.ts                |  380 +-
 lifeos_hook_bridge/memory_ownership.py             |  249 +
 lifeos_hook_bridge/memory_preferences.py           |  123 +-
 lifeos_hook_bridge/memory_prompt.py                |   16 +-
 lifeos_hook_bridge/memory_provider.py              |   13 +
 lifeos_hook_bridge/memory_publication.ts           |    4 +-
 lifeos_hook_bridge/memory_pulse_adapters.py        |  332 ++
 lifeos_hook_bridge/memory_recurrence.py            |  177 +
 lifeos_hook_bridge/memory_runtime.py               |  105 +-
 lifeos_hook_bridge/memory_seed.py                  |   91 +
 lifeos_hook_bridge/memory_service.py               |  239 +
 lifeos_hook_bridge/memory_sharing.py               |  170 -
 lifeos_hook_bridge/memory_source_review.py         |   41 +-
 lifeos_hook_bridge/memory_sources.py               |  150 +-
 lifeos_hook_bridge/memory_state.py                 |   67 +
 lifeos_hook_bridge/memory_telos.py                 |   66 +
 lifeos_hook_bridge/memory_transaction.py           |   74 +-
 lifeos_hook_bridge/memory_wisdom.py                |  217 +
 lifeos_hook_bridge/native_dependencies.py          |  150 +
 lifeos_hook_bridge/ownership_setup.py              |  212 +
 .../patches/hermes-plugin-events.patch             |  155 +-
 .../patches/hermes-required-middleware.patch       |   57 +-
 .../patches/lifeos-memory-access.patch             | 6091 +++++++++++++++++---
 lifeos_hook_bridge/plugin.yaml                     |    3 +
 lifeos_hook_bridge/profile_backup.py               |  253 +
 lifeos_hook_bridge/profile_backup_recovery.py      |  145 +
 lifeos_hook_bridge/profile_services.py             |  306 +
 lifeos_hook_bridge/sqlite_snapshot.py              |   19 +
 patches/hermes-plugin-events.patch                 |  155 +-
 patches/hermes-required-middleware.patch           |   57 +-
 patches/lifeos-memory-access.patch                 | 6091 +++++++++++++++++---
 72 files changed, 21021 insertions(+), 1708 deletions(-)
```

All requested input files exist at c083037. The snapshot copy in `/tmp/pr3-memory-review/` came from the `git show` commands above; each `.diff` came from the corresponding range diff.

## Per-file notes

- `lifeos_hook_bridge/memory_native.ts`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_publication.ts`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_runtime.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_http.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_mcp.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_rpc.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_service.py`: Finding 1: client grant is loaded once; in-flight operations do not recheck it.
- `lifeos_hook_bridge/memory_policy.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_access.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_transaction.py`: Finding 3: generic journal recovery restores without checking for later destination edits.
- `lifeos_hook_bridge/memory_sources.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_source_review.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_prompt.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_history.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_lineage.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_context_audit.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_counts.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_pulse_adapters.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_pulse.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_freshness.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_freshness_cache.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_freshness_migration.py`: Finding 4: a later migration can replace the fixed-name backup.
- `lifeos_hook_bridge/memory_distill.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_hypotheses.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_wisdom.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_interview.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_interview_scan.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_learning.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_recurrence.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_seed.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_state.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_telos.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_graph.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_evidence.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_deny_hashes.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `lifeos_hook_bridge/memory_derived_sync.py`: Read the full c083037 snapshot and its range diff; no defect found in the requested failure classes.
- `patches/lifeos-memory-access.patch`: Read the permission, audience, HTTP routing, migration, and MemoryAccess helper hunks listed in the coverage section. Findings 2 and 4 use those hunks. Other patch regions were not read line by line.

## Failure paths and relevant excerpts

1. Revocation race: `call_client` loads a grant once (service lines 570-576). `_call` then runs `remember` or `recall` without a current-grant callback (lines 603-620). The configuration update lock is separate from the memory transaction lock.
2. Marker-loss fallback: patch lines 6698-6707 return the process-local `managedHTTP` boolean; a newly started process sees false when both files are absent. Patch lines 1175-1195 show the direct memory route remains underneath the managed branch. The source helper also returns direct file content when its service result is undefined (lines 6587-6594).
3. Recovery overwrite: `prepare` stores `after_digest` only when the caller supplies an expected map (transaction lines 80-94). In `recover`, lines 148-159 skip `_check_restore` for ordinary journals and publish the old copy over the current destination.
4. Backup replacement: Python `backup_name()` always returns the same date-stamped path (migration lines 14-19), and its publication loop calls `publish()` unconditionally (lines 117-119). The patch at line 4740 shows upstream constructs that same backup name for each run.
5. Proposal size: service lines 82-85 validate only nested keys and required fields. `memory_proposals.enqueue()` then passes the object to `memory._native('validate', item=item)`, which serializes it and starts Bun. A proposal creation grant is required, so this is an authenticated availability issue.

### lifeos_hook_bridge/memory_service.py:82-89

```text
   82:         elif key == "proposal":
   83:             if (not isinstance(value, dict) or set(value) - set(schema["properties"])
   84:                     or set(schema["required"]) - set(value) or value.get("type") != "proposal"):
   85:                 raise ValueError("Invalid native proposal fields")
   86:         elif key == "reference":
   87:             if not isinstance(value, dict) or set(value) != {"id", "revision"} or not isinstance(value["id"], str) or not value["id"]:
   88:                 raise ValueError("Invalid memory reference")
   89:             if type(value["revision"]) is not int or value["revision"] < 1:
```
### lifeos_hook_bridge/memory_service.py:570-576

```text
  570:     def call_client(self, identifier: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
  571:         try:
  572:             configuration = self.configuration.load()
  573:             scope = self.client_scope(configuration, identifier)
  574:         except (MemoryUnavailable, ValueError, OSError) as error:
  575:             return {"status": "rejected", "reason": str(error)}
  576:         return self._call(configuration, scope, name, arguments)
```
### lifeos_hook_bridge/memory_service.py:603-620

```text
  603:             if name == "lifeos_memory_propose":
  604:                 result = memory.native_add(scope, arguments["proposal"], request_id=arguments["request_id"], project="",
  605:                                            source_session=source_session)
  606:                 return result.get("receipt", {"status":"rejected", "reason":result.get("message", "Native proposal failed")})
  607:             if name == "lifeos_memory_proposals":
  608:                 return {"status":"ok", "results":memory.review_proposals(scope)}
  609:             if name == "lifeos_memory_decide_proposal":
  610:                 return memory.decide_proposal(scope, **arguments)
  611:             if name == "lifeos_memory_search":
  612:                 return {"status": "ok", "results": memory.recall(scope, **arguments)}
  613:             if name == "lifeos_memory_get":
  614:                 return memory.get(scope, arguments["reference"])
  615:             if name == "lifeos_memory_remember":
  616:                 return memory.remember(scope, **arguments, source={'kind': 'explicit', 'session': source_session})
  617:             if name == "lifeos_memory_correct":
  618:                 return memory.correct(scope, **arguments)
  619:             if name == "lifeos_memory_forget":
  620:                 return memory.forget(scope, **arguments)
```
### lifeos_hook_bridge/memory_transaction.py:80-94

```text
   80:     def prepare(self, writer: str, request_id: str, paths: list[str], *, expected=None) -> None:
   81:         if expected is not None and (not isinstance(expected, dict) or set(expected) != set(paths)
   82:                 or any(not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None
   83:                        for value in expected.values())):
   84:             raise ValueError('Expected publications require one exact digest for each destination')
   85:         copies = []
   86:         for name in sorted(set(paths)):
   87:             path = self.resolve(name)
   88:             present = path.exists()
   89:             copies.append({"path": name, "data": base64.b64encode(path.read_bytes()).decode() if present else None,
   90:                            "mode": stat.S_IMODE(path.stat().st_mode) if present else None})
   91:             if expected is not None:
   92:                 copies[-1]['after_digest'] = expected[name]
   93:         publish(self.journal, json.dumps({"writer": writer, "request_id": request_id, "copies": copies}).encode())
   94: 
```
### lifeos_hook_bridge/memory_transaction.py:143-163

```text
  143:         row = connection.execute("SELECT receipt FROM operations WHERE writer=? AND request_id=?",
  144:                                  (operation["writer"], operation["request_id"])).fetchone()
  145:         if row is not None and json.loads(row["receipt"])["status"] != "unknown":
  146:             self.journal.unlink()
  147:             return
  148:         expected = any('after_digest' in copy for copy in operation['copies'])
  149:         if expected:
  150:             for copy in operation['copies']:
  151:                 self._check_restore(copy)
  152:         for copy in operation["copies"]:
  153:             if expected:
  154:                 self._check_restore(copy)
  155:             path = self.resolve(copy["path"])
  156:             if copy["data"] is None:
  157:                 path.unlink(missing_ok=True)
  158:             else:
  159:                 publish(path, base64.b64decode(copy["data"], validate=True), mode=copy.get('mode', 0o600))
  160:         connection.execute("DELETE FROM operations WHERE writer=? AND request_id=?",
  161:                            (operation["writer"], operation["request_id"]))
  162:         connection.commit()
  163:         self.journal.unlink()
```
### lifeos_hook_bridge/memory_freshness_migration.py:14-19

```text
   14: def backup_name(relative):
   15:     path = Path(relative)
   16:     return (path.parent / 'Backups' / (path.stem + '-2026-05-03-23-00-00.md')).as_posix()
   17: 
   18: 
   19: SYSTEM_BACKUPS = frozenset(backup_name(relative) for relative in SYSTEM_PUBLICATIONS)
```
### lifeos_hook_bridge/memory_freshness_migration.py:117-124

```text
  117:         for item in result['publications']:
  118:             relative = Path(item['path']).relative_to(memory.root).as_posix()
  119:             publish(memory._publication_path(relative), item['content'].encode())
  120:         output.append({name: result[name] for name in ('status', 'stdout', 'stderr')})
  121:         return {'status': 'committed' if result['publications'] else 'unchanged',
  122:                 'artifacts': len(result['publications'])}
  123: 
  124:     receipt = memory._operation(scope, 'freshness-migration-' + uuid4().hex, payload, apply)
```
### lifeos_hook_bridge/memory_publication.ts:11-25

```text
   11: export function observePublication(root: string, journal: string, destination: string): void {
   12:   const expected = resolve(root, "LIFEOS/MEMORY/STATE/memory-operation.json");
   13:   const info = lstatSync(journal);
   14:   if (resolve(journal) !== expected || !info.isFile() || info.isSymbolicLink()
   15:       || info.uid !== process.getuid?.() || (info.mode & 0o077) !== 0) {
   16:     throw new Error("The native publication journal needs the fixed private owner path");
   17:   }
   18:   const path = resolve(destination);
   19:   const parent = realpathSync(dirname(path));
   20:   const upgrades = realpathSync(resolve(root, "LIFEOS/MEMORY/UPGRADES"));
   21:   const user = realpathSync(resolve(root, "../.config/LIFEOS/USER"));
   22:   if (!upgrades.startsWith(user + "/")) throw new Error("The upgrade store leaves native user data");
   23:   if (!parent.startsWith(upgrades + "/") && parent !== upgrades) {
   24:     throw new Error("The upgrade publication leaves its governed store");
   25:   }
```
### lifeos_hook_bridge/memory_publication.ts:40-53

```text
   40:   const operation: unknown = JSON.parse(readFileSync(journal, "utf8"));
   41:   if (!object(operation) || !Array.isArray(operation.copies)) throw new Error("Invalid native publication journal");
   42:   if (operation.copies.some((copy: unknown) => object(copy) && copy.path === name)) return;
   43:   operation.copies.push({path: name, data: present ? readFileSync(path).toString("base64") : null, mode: originalMode});
   44:   const temporary = journal + "." + randomUUID();
   45:   const fd = openSync(temporary, "wx", 0o600);
   46:   try {
   47:     writeFileSync(fd, JSON.stringify(operation));
   48:     fsyncSync(fd);
   49:   } finally { closeSync(fd); }
   50:   renameSync(temporary, journal);
   51:   const directory = openSync(dirname(journal), "r");
   52:   try { fsyncSync(directory); } finally { closeSync(directory); }
   53: }
```
### lifeos_hook_bridge/memory_native.ts:12-27

```text
   12: async function main(): Promise<void> {
   13:   const root = process.argv[2];
   14:   if (!root) throw new Error("An installed LifeOS root is required");
   15:   const input: unknown = JSON.parse(await Bun.stdin.text());
   16:   if (!object(input)) throw new Error("Native memory input must be an object");
   17:   if (input.action === "learning_principal") process.env.LIFEOS_CONFIG_PATH = resolve(root, "LIFEOS/USER/CONFIG/LIFEOS_CONFIG.toml");
   18:   const system: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemorySystem.ts")).href);
   19:   const writer: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryWriter.ts")).href);
   20:   if (!object(system) || !object(writer)) throw new Error("Native memory exports are unavailable");
   21:   const journal = process.env.LIFEOS_MEMORY_PUBLICATION_JOURNAL;
   22:   if (input.action === "add" && journal && object(input.item) && input.item.type === "proposal") {
   23:     const upgrades: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/Upgrades.ts")).href);
   24:     if (!object(upgrades) || typeof upgrades.observeUpgradePublication !== "function") {
   25:       throw new Error("The native proposal publication capability is unavailable");
   26:     }
   27:     upgrades.observeUpgradePublication((path: string) => observePublication(root, journal, path));
```
### lifeos_hook_bridge/memory_native.ts:527-549

```text
  527:   } else if (input.action === "add" || input.action === "validate") {
  528:     if (typeof system.sanitizeTypedItemForPersistence !== "function" || typeof system.add !== "function") {
  529:       throw new Error("Native memory validation or add operation is unavailable");
  530:     }
  531:     const checked: unknown = system.sanitizeTypedItemForPersistence(input.item);
  532:     if (!object(checked) || checked.ok !== true || input.action === "validate") result = checked;
  533:     else result = system.add(checked.item);
  534:   } else if (input.action === "parse_hot") {
  535:     if (typeof input.content !== "string" || typeof writer.parseMemoryContent !== "function") {
  536:       throw new Error("Native recovery requires declared hot content");
  537:     }
  538:     result = writer.parseMemoryContent(input.content);
  539:   } else if (input.action === "read_hot") {
  540:     if (typeof writer.read !== "function" || typeof input.path !== "string") throw new Error("Invalid hot-memory read");
  541:     result = writer.read(input.path);
  542:   } else if (input.action === "set_hot") {
  543:     if (typeof writer.setEntries !== "function" || typeof input.path !== "string" || !Array.isArray(input.entries)
  544:         || input.entries.some((entry: unknown) => typeof entry !== "string")) throw new Error("Invalid hot-memory curation");
  545:     result = writer.setEntries(input.path, input.entries, { updatedBy: input.writer, allowDrastic: input.allowDrastic === true });
  546:   } else {
  547:     throw new Error("Unknown native memory operation");
  548:   }
  549:   process.stdout.write(JSON.stringify(result) + "\n");
```
### lifeos_hook_bridge/memory_sources.py:104-157

```text
  104: def authorize(scope: MemoryScope) -> dict[str, Any]:
  105:     if not CATEGORIES <= set(scope.read) or '*' not in scope.projects:
  106:         raise MemoryUnavailable('This unclassified native source requires unrestricted owner recall')
  107:     return {'ok':True}
  108: 
  109: 
  110: def _source_path(memory, scope: MemoryScope, path: str, *, diagnostic: bool = False,
  111:                  require_file: bool = True, evidence: bool = False,
  112:                  interview_setup: bool = False, deny_hashes: bool = False, derived_sync: bool = False) -> tuple[Path, str]:
  113:     authorize(scope)
  114:     if not isinstance(path,str):
  115:         raise MemoryUnavailable('A supported native source path is required')
  116:     relative = Path(path).relative_to(memory.root).as_posix()
  117:     if '..' in Path(relative).parts:
  118:         raise MemoryUnavailable('The native source cannot leave its installed root')
  119:     system = (relative in SYSTEM_FILES or relative.startswith(SYSTEM_PREFIXES)
  120:               or re.fullmatch(r'skills/[^/.][^/]*/SKILL\.md', relative) is not None
  121:               or derived_sync and relative.startswith("LIFEOS/PULSE/pages/")
  122:               or interview_setup and relative in {'.env', 'LIFEOS/PULSE/PULSE.toml'})
  123:     if derived_sync:
  124:         directory = False
  125:         permitted = is_sync_source(relative)
  126:     elif deny_hashes:
  127:         directory = False
  128:         permitted = is_deny_source(relative)
  129:     elif interview_setup:
  130:         directory = False
  131:         permitted = relative in INTERVIEW_SETUP_FILES
  132:     elif evidence:
  133:         directory = False
  134:         permitted = is_evidence_source(relative)
  135:     elif diagnostic:
  136:         from .memory_diagnostics import DIAGNOSTIC_FILES, DIAGNOSTIC_DIRECTORIES
  137:         directory = not require_file and relative in DIAGNOSTIC_DIRECTORIES
  138:         report = not require_file and re.fullmatch(
  139:             r'LIFEOS/MEMORY/OBSERVABILITY/reports/[A-Za-z0-9][A-Za-z0-9_-]*\.json', relative)
  140:         permitted = relative in DIAGNOSTIC_FILES or directory or report
  141:     else:
  142:         directory = False
  143:         permitted = (relative in FILES | LOG_FILES | CACHE_FILES | CONTEXT_FILES | TELOS_SOURCES | FRESHNESS_TELOS_SOURCES
  144:                      or is_state_source(relative)
  145:                      or relative.startswith(PREFIXES) or system)
  146:     if not permitted:
  147:         raise MemoryUnavailable('This is not a supported native history or context source')
  148:     source = memory.root / relative if system else memory._path(relative)
  149:     physical = memory.physical_root / relative if system else memory.root.parent/'.config/LIFEOS/USER'/Path(relative).relative_to(
  150:         'LIFEOS/USER' if relative.startswith('LIFEOS/USER/') else 'LIFEOS')
  151:     if (source.resolve() != physical.absolute() or (require_file and not source.is_file())
  152:             or (not require_file and source.exists() and not (source.is_dir() if directory else source.is_file()))):
  153:         raise MemoryUnavailable('The native source is missing or changes its permitted physical path')
  154:     # Closing another descriptor for the SQLite inode releases this process's transaction locks.
  155:     if system and source.exists() and memory.database.exists() and source.samefile(memory.database):
  156:         raise MemoryUnavailable('Native memory content cannot alias its SQLite registry')
  157:     return source, relative
```
### lifeos_hook_bridge/memory_sources.py:166-186

```text
  166: def _text_source(memory, scope: MemoryScope, path: str, *, suffix='.md', evidence=False, interview_setup=False, deny_hashes=False, preserve_newlines=False, derived_sync=False):
  167:     source, relative = _source_path(memory, scope, path, evidence=evidence, interview_setup=interview_setup, deny_hashes=deny_hashes, derived_sync=derived_sync)
  168:     if source.suffix != suffix:
  169:         raise MemoryUnavailable('The declared wiki source must be native Markdown')
  170:     before = source.stat()
  171:     if before.st_size > SOURCE_LIMIT:
  172:         raise MemoryUnavailable('The native wiki source exceeds the 256 KiB limit')
  173:     try:
  174:         with source.open('r', encoding='utf-8', newline='' if preserve_newlines else None) as stream:
  175:             content = stream.read()
  176:     except UnicodeError as error:
  177:         raise MemoryUnavailable('The native wiki source is not valid UTF-8') from error
  178:     after = source.stat()
  179:     if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
  180:             != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
  181:         raise MemoryUnavailable('The native wiki source changed during collection')
  182:     _source_path(memory, scope, path, evidence=evidence, interview_setup=interview_setup, deny_hashes=deny_hashes, derived_sync=derived_sync)
  183:     if len(content.encode()) > SOURCE_LIMIT:
  184:         raise MemoryUnavailable('The native wiki source exceeds the 256 KiB limit')
  185:     return ({'path': path, 'relative': relative, 'content': content,
  186:              'lastModified': _source_time(after, milliseconds=True)}, _source_time(after))
```
### lifeos_hook_bridge/memory_access.py:315-353

```text
  315:     def _operation(self, scope: MemoryScope, request_id: str, payload: dict[str, Any],
  316:                    callback: Callable[[sqlite3.Connection], dict[str, Any]], *,
  317:                    identity_payload: dict[str, Any] | None = None, publication_digests=None) -> dict[str, Any]:
  318:         if not isinstance(request_id, str) or not request_id or len(request_id) > 256:
  319:             return {"status": "rejected", "reason": "A bounded request identifier is required"}
  320:         payload_digest = _digest(json.dumps(payload if identity_payload is None else identity_payload, sort_keys=True))
  321:         reserved = False
  322:         try:
  323:             with self._transaction() as connection:
  324:                 prior = connection.execute("SELECT * FROM operations WHERE writer=? AND request_id=?",
  325:                                            (scope.writer, request_id)).fetchone()
  326:                 if prior is not None:
  327:                     if prior["payload_digest"] != payload_digest:
  328:                         return {"status": "conflict", "reason": "This request identifier names another operation"}
  329:                     return json.loads(prior["receipt"])
  330:                 unknown = {"status": "unknown", "reason": "The operation outcome needs recovery before retry",
  331:                            "writer": scope.writer, "request_id": request_id}
  332:                 paths = self._publication_paths(connection, scope, payload)
  333:                 self.transaction.prepare(scope.writer, request_id, paths, expected=publication_digests)
  334:                 connection.execute("INSERT INTO operations VALUES (?,?,?,?)",
  335:                                    (scope.writer, request_id, payload_digest, json.dumps(unknown)))
  336:                 connection.commit()
  337:                 reserved = True
  338:                 connection.execute("BEGIN IMMEDIATE")
  339:                 try:
  340:                     receipt = callback(connection)
  341:                 except MemoryConflict as error:
  342:                     receipt = {"status": "conflict", "reason": str(error)}
  343:                 receipt.setdefault("writer", scope.writer)
  344:                 receipt.setdefault("request_id", request_id)
  345:                 connection.execute("UPDATE operations SET receipt=? WHERE writer=? AND request_id=?",
  346:                                    (json.dumps(receipt), scope.writer, request_id))
  347:                 self.transaction.flush_publication()
  348:                 return receipt
  349:         except MemoryConflict as error:
  350:             return {"status": "conflict", "reason": str(error), "writer": scope.writer, "request_id": request_id}
  351:         except (MemoryUnavailable, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
  352:             return {"status": "unknown" if reserved else "rejected",
  353:                     "reason": str(error), "writer": scope.writer, "request_id": request_id}
```
### lifeos_hook_bridge/memory_access.py:709-720

```text
  709:     def recall(self, scope: MemoryScope, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
  710:         if not isinstance(query, str) or not query.strip():
  711:             raise ValueError("A memory query is required")
  712:         if type(limit) is not int:
  713:             raise ValueError("The memory result limit must be an integer")
  714:         with self._transaction() as connection:
  715:             records, corpus = self._corpus(connection, scope)
  716:             if not corpus:
  717:                 return []
  718:             ranked = self._native("rank", query=query, corpus=corpus, limit=max(1, min(limit, 100)))
  719:             return [{**records[item["path"]], "score": item["score"]} for item in ranked["results"]]
  720: 
```
### patches/lifeos-memory-access.patch:6538-6558

```text
 6538: +export function hasMemoryAccess(): boolean {
 6539: +  if (process.env.LIFEOS_MEMORY_INTERNAL === "1") return false;
 6540: +  for (const name of ["memory-access.json", "memory-http.json"]) {
 6541: +    try {
 6542: +      lstatSync(resolve(homedir(), ".claude/LIFEOS/USER/CONFIG", name));
 6543: +      return true;
 6544: +    } catch (error: unknown) {
 6545: +      if (!memoryObject(error) || error.code !== "ENOENT") throw error;
 6546: +    }
 6547: +  }
 6548: +  return false;
 6549: +}
 6550: +
 6551: +export function observedMemoryRevision(path: string): string {
 6552: +  return revisions.get(resolve(path)) ?? "";
 6553: +}
 6554: +
 6555: +export function memoryAccess<T>(operation: string, arguments_: Record<string, unknown>,
 6556: +                                valid: (value: unknown) => value is T): T | undefined {
 6557: +  if (operation !== "pulse_http" && !hasMemoryAccess()) return undefined;
 6558: +  const path = resolve(homedir(), ".claude/LIFEOS/USER/CONFIG/memory-access.json");
```
### patches/lifeos-memory-access.patch:6587-6594

```text
 6587: +export function readMemorySource(path: string): string {
 6588: +  const governed = memoryAccess("read_source", {path: resolve(path)},
 6589: +    (value): value is Record<string, unknown> => memoryObject(value) && typeof value.ok === "boolean");
 6590: +  if (governed === undefined) return readFileSync(path, "utf8");
 6591: +  if (governed.ok !== true || typeof governed.content !== "string" || governed.excluded !== false) {
 6592: +    throw new Error("The retained native source is excluded or unavailable");
 6593: +  }
 6594: +  return governed.content;
```
### patches/lifeos-memory-access.patch:6694-6708

```text
 6694: +let managedHTTP = false;
 6695: +
 6696: +// ABOUTME: Resolves managed HTTP mode independently from ambient agent context.
 6697: +// ABOUTME: Retains refusal after connector loss and honors the persistent HTTP marker.
 6698: +export function hasManagedMemoryHTTP(): boolean {
 6699: +  for (const name of ["memory-http.json", "memory-access.json"]) {
 6700: +    try {
 6701: +      lstatSync(resolve(homedir(), ".claude/LIFEOS/USER/CONFIG", name));
 6702: +      managedHTTP = true;
 6703: +    } catch (error: unknown) {
 6704: +      if (!memoryObject(error) || error.code !== "ENOENT") throw error;
 6705: +    }
 6706: +  }
 6707: +  return managedHTTP;
 6708: +}
```
### patches/lifeos-memory-access.patch:4735-4744

```text
 4735: -function writeBackup(path: string, content: string): string {
 4736: +function writeBackup(path: string, content: string, input?: MigrationInput): string {
 4737:    const backupDir = join(dirname(path), "Backups");
 4738: -  if (!existsSync(backupDir)) mkdirSync(backupDir, { recursive: true });
 4739: +  if (!input && !existsSync(backupDir)) mkdirSync(backupDir, { recursive: true });
 4740:    const backupPath = join(backupDir, `${basename(path, ".md")}-${BACKUP_TS}.md`);
 4741: -  writeFileSync(backupPath, content);
 4742: +  publishMigration(backupPath, content, input);
 4743:    return backupPath;
 4744:  }
```
### patches/lifeos-memory-access.patch:1170-1195

```text
 1170: +  if (pathname === "/api/memory" || pathname.startsWith("/api/memory/")) {
 1171: +    const refused = (status: number, error: string): Response => new Response(JSON.stringify({error}), {
 1172: +      status, headers: {"content-type": "application/json", "cache-control": "no-store"},
 1173: +    });
 1174: +    try {
 1175: +      if (hasManagedMemoryHTTP()) {
 1176: +        const views: Record<string, string> = {"/api/memory": "snapshot", "/api/memory/": "snapshot",
 1177: +          "/api/memory/state": "state", "/api/memory/health": "health", "/api/memory/runs": "runs",
 1178: +          "/api/memory/graph": "graph"};
 1179: +        const view = views[pathname];
 1180: +        if (!view) return refused(404, "This managed memory route is not supported");
 1181: +        if (req.method !== "GET") return refused(405, "Memory views require GET");
 1182: +        const url = new URL(req.url);
 1183: +        if (url.search) return refused(400, "Memory views use the installed owner configuration");
 1184: +        const origin = req.headers.get("origin");
 1185: +        if (origin && origin !== url.origin) return refused(403, "Memory views require the current origin");
 1186: +        return memoryHTTPResponse(req, view);
 1187: +      }
 1188: +    } catch {
 1189: +      return refused(503, "Authenticated memory is unavailable");
 1190: +    }
 1191: +  }
 1192:    if (req.method !== "GET") return null;
 1193:  
 1194:    if (pathname === "/api/memory" || pathname === "/api/memory/") {
 1195: diff --git a/LifeOS/install/LIFEOS/PULSE/modules/telos.ts b/LifeOS/install/LIFEOS/PULSE/modules/telos.ts
```
