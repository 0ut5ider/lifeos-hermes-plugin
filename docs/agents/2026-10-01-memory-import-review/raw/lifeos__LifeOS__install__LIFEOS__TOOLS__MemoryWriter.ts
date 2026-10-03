     1	#!/usr/bin/env bun
     2	/**
     3	 * MemoryWriter — set-overwrite writer for PRINCIPAL_MEMORY.md / DA_MEMORY.md.
     4	 *
     5	 * LifeOS autonomic memory subsystem, F2.
     6	 *
     7	 * Set-overwrite design: the reviewer
     8	 * submits the canonical full list it wants for a memory file. The writer:
     9	 *   1. Validates each entry against the 5-prefix schema (silent-drop malformed)
    10	 *   2. Validates each entry's length ≤ 256 chars (silent-drop over-length)
    11	 *   3. Deduplicates (case-sensitive string match)
    12	 *   4. Checks the accepted+deduped count against the 48-entry cap; if over,
    13	 *      returns a structured at-cap error so the model can re-submit trimmed
    14	 *   5. Writes atomically: acquire <file>.lock → write <file>.tmp → atomic rename
    15	 *
    16	 * Why set-overwrite beats incremental add/replace/remove:
    17	 *   - No race surface (single atomic write per review)
    18	 *   - Idempotent (same input produces same file)
    19	 *   - Eviction is structural (model omits entries it wants gone)
    20	 *   - Simpler mental model: "here is the state I want"
    21	 *
    22	 * Five prefixes only (case-sensitive, exact match, followed by ": "):
    23	 *   NAME | ROLE | RELATION | PREFERENCE | RULE
    24	 *
    25	 * Allowed paths only (resolved + suffix-matched, no symlink escape):
    26	 *   LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md
    27	 *   LIFEOS/USER/DIGITAL_ASSISTANT/DA_MEMORY.md
    28	 *
    29	 * Observability: every successful setEntries appends a JSONL row to
    30	 * MEMORY/OBSERVABILITY/memory-writes.jsonl per ISC-107.
    31	 *
    32	 * CLI:
    33	 *   bun MemoryWriter.ts read <path>
    34	 *   bun MemoryWriter.ts set <path> <entries-as-newline-delimited-stdin>
    35	 *   bun MemoryWriter.ts test    (runs built-in smoke test)
    36	 */
    37	
    38	import {
    39	  appendFileSync,
    40	  closeSync,
    41	  existsSync,
    42	  fsyncSync,
    43	  mkdirSync,
    44	  openSync,
    45	  readFileSync,
    46	  readdirSync,
    47	  renameSync,
    48	  rmSync,
    49	  unlinkSync,
    50	  writeFileSync,
    51	} from "node:fs";
    52	import { dirname, resolve as pathResolve } from "node:path";
    53	import { homedir } from "node:os";
    54	
    55	import { memoryAccess, memoryObject, observedMemoryRevision } from "./lib/MemoryAccess";
    56	import { randomUUID } from "node:crypto";
    57	
    58	// ── Constants ──
    59	
    60	const CLAUDE_ROOT = pathResolve(homedir(), ".claude");
    61	
    62	const ALLOWED_FILES = new Set<string>([
    63	  pathResolve(CLAUDE_ROOT, "LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md"),
    64	  pathResolve(CLAUDE_ROOT, "LIFEOS/USER/DIGITAL_ASSISTANT/DA_MEMORY.md"),
    65	]);
    66	
    67	const PREFIX_PATTERN = /^(NAME|ROLE|RELATION|PREFERENCE|RULE): /;
    68	const MAX_CHARS_PER_ENTRY = 256;
    69	const MAX_ENTRIES = 48;
    70	
    71	export const BEGIN_MARKER = "<!-- BEGIN ENTRIES -->";
    72	export const END_MARKER = "<!-- END ENTRIES -->";
    73	
    74	const OBSERVABILITY_PATH = pathResolve(
    75	  CLAUDE_ROOT,
    76	  "LIFEOS/MEMORY/OBSERVABILITY/memory-writes.jsonl",
    77	);
    78	
    79	// ── Types ──
    80	
    81	export interface SetEntriesOk {
    82	  ok: true;
    83	  accepted: number;
    84	  dropped_malformed: number;
    85	  dropped_overlength: number;
    86	  dropped_duplicates: number;
    87	  prior_count: number;
    88	  new_count: number;
    89	  evictions: string[];
    90	  additions: string[];
    91	}
    92	
    93	export interface SetEntriesErrAtCap {
    94	  ok: false;
    95	  code: "EAT_CAP";
    96	  message: string;
    97	  over_count: number;
    98	  cap: number;
    99	  indexed_submission: string[];
   100	}
   101	
   102	export interface SetEntriesErrPath {
   103	  ok: false;
   104	  code: "EINVAL_PATH";
   105	  message: string;
   106	}
   107	
   108	export interface SetEntriesErrLock {
   109	  ok: false;
   110	  code: "ELOCK_HELD";
   111	  message: string;
   112	}
   113	
   114	export interface SetEntriesErrIO {
   115	  ok: false;
   116	  code: "EWRITE_FAILED";
   117	  message: string;
   118	}
   119	
   120	export interface SetEntriesErrShrink {
   121	  ok: false;
   122	  code: "ESUSPECT_SHRINK";
   123	  message: string;
   124	  prior_count: number;
   125	  new_count: number;
   126	}
   127	
   128	export interface SetEntriesErrErosion {
   129	  ok: false;
   130	  code: "ESUSPECT_EROSION";
   131	  message: string;
   132	  prior_count: number;
   133	  new_count: number;
   134	}
   135	
   136	export type SetEntriesResult =
   137	  | SetEntriesOk
   138	  | SetEntriesErrAtCap
   139	  | SetEntriesErrPath
   140	  | SetEntriesErrLock
   141	  | SetEntriesErrIO
   142	  | SetEntriesErrShrink
   143	  | SetEntriesErrErosion;
   144	
   145	export interface ReadResult {
   146	  entries: string[];
   147	  count: number;
   148	  chars_used: number;
   149	  cap_entries: number;
   150	  cap_chars: number;
   151	  /**
   152	   * On-disk entries excluded from `entries` as invalid (marker/newline content or
   153	   * over-length). NEVER silently ignorable: the reviewer's set-overwrite submits
   154	   * `entries`, so anything listed here is erased by its next write.
   155	   */
   156	  dropped_invalid: { entry: string; reason: "malformed" | "overlength" }[];
   157	}
   158	
   159	// ── Path validation ──
   160	
   161	function validatePath(filePath: string): { ok: true; abs: string } | SetEntriesErrPath {
   162	  let abs: string;
   163	  try {
   164	    abs = pathResolve(filePath);
   165	  } catch (e) {
   166	    return { ok: false, code: "EINVAL_PATH", message: `Cannot resolve path: ${filePath}` };
   167	  }
   168	  if (!ALLOWED_FILES.has(abs)) {
   169	    return {
   170	      ok: false,
   171	      code: "EINVAL_PATH",
   172	      message: `Path not in allowlist. MemoryWriter only operates on PRINCIPAL_MEMORY.md / DA_MEMORY.md. Got: ${abs}`,
   173	    };
   174	  }
   175	  return { ok: true, abs };
   176	}
   177	
   178	// ── Entry validation ──
   179	
   180	interface ValidationOutcome {
   181	  accepted: string[];
   182	  malformed: number;
   183	  overlength: number;
   184	  duplicates: number;
   185	}
   186	
   187	function validateAndDedup(entries: string[]): ValidationOutcome {
   188	  const seen = new Set<string>();
   189	  const accepted: string[] = [];
   190	  let malformed = 0;
   191	  let overlength = 0;
   192	  let duplicates = 0;
   193	
   194	  for (const raw of entries) {
   195	    const entry = raw.trim();
   196	    if (entry.length === 0) continue;
   197	
   198	    // One entry = one physical line. An embedded newline would serialize as
   199	    // multiple on-disk lines, inflating the real entry count past every cap and
   200	    // desyncing accepted/new_count from what a reparse sees.
   201	    if (/[\r\n]/.test(entry)) {
   202	      malformed++;
   203	      continue;
   204	    }
   205	
   206	    const m = entry.match(PREFIX_PATTERN);
   207	    if (!m) {
   208	      malformed++;
   209	      continue;
   210	    }
   211	
   212	    // Entries may never contain the structural markers: a marker substring inside
   213	    // an entry would pollute the block and blind naive parsers. A pre-existing
   214	    // on-disk offender still parses whole (markers are line-based), but
   215	    // resubmission drops it here — visible as dropped_malformed.
   216	    if (entry.includes(BEGIN_MARKER) || entry.includes(END_MARKER)) {
   217	      malformed++;
   218	      continue;
   219	    }
   220	
   221	    // Length check: total entry length must be ≤ prefix.length + MAX_CHARS_PER_ENTRY
   222	    // Equivalently: the content AFTER the prefix must be ≤ MAX_CHARS_PER_ENTRY.
   223	    const prefixWithColonSpace = m[0]; // e.g. "PREFERENCE: "
   224	    const content = entry.slice(prefixWithColonSpace.length);
   225	    if (content.length > MAX_CHARS_PER_ENTRY) {
   226	      overlength++;
   227	      continue;
   228	    }
   229	
   230	    if (seen.has(entry)) {
   231	      duplicates++;
   232	      continue;
   233	    }
   234	    seen.add(entry);
   235	    accepted.push(entry);
   236	  }
   237	
   238	  return { accepted, malformed, overlength, duplicates };
   239	}
   240	
   241	// ── File parse / serialize ──
   242	
   243	// Line-based canonical model (public PR #1593, @anikinsasha). The former
   244	// indexOf-over-the-whole-body parse had three compounding defects that produced
   245	// permanent, SILENT memory loss in the wild:
   246	//
   247	//   1. A stray END before BEGIN sent every write down the recovery branch, forever.
   248	//   2. serializeFile's self-heal appended the missing BEGIN *after* that stray END,
   249	//      manufacturing a permanent END-before-BEGIN inversion, and re-emitted one
   250	//      fresh END per write — files grew a stack of END markers, +1 per curation,
   251	//      never compacted.
   252	//   3. Every reader bailed to zero entries on marker disorder, so sessions ran with
   253	//      no memory loaded while the writer kept curating and the health check
   254	//      reported clean headroom (0/48).
   255	//
   256	// The model that fixes it: markers are recognized ONLY as whole trimmed lines, so
   257	// an entry that merely mentions a marker can never truncate the block. Parse is
   258	// uniformly lenient — every valid-prefix line anywhere after the frontmatter is an
   259	// entry (block ∪ orphans, order-preserved, first-seen deduped); marker lines are
   260	// structural and dropped; everything else is body, preserved verbatim, including
   261	// invalid-prefix orphans, which are never silently absorbed or deleted. Serialize
   262	// always emits the canonical shape (frontmatter → body → BEGIN → entries → END →
   263	// newline), so ONE write converges any historical corruption and repeated writes
   264	// are byte-identical.
   265	//
   266	// This is THE parser for the memory files. Every consumer (LoadMemory hook, Pulse
   267	// memory panel, MemoryHealthCheck, MemoryRestore) imports it — reader and writer
   268	// can never diverge again. Never write a second marker-parsing implementation.
   269	
   270	export interface ParsedMemoryFile {
   271	  frontmatter: string;
   272	  bodyLines: string[];
   273	  entries: string[];
   274	}
   275	
   276	export function parseMemoryContent(content: string): ParsedMemoryFile {
   277	  const fmMatch = content.match(/^---\r?\n[\s\S]*?\r?\n---\r?\n/);
   278	  // A "frontmatter" that swallowed a marker line is a mis-close: an unterminated
   279	  // opening fence closing on some later body `---` would hide the whole entries
   280	  // block inside frontmatter, blinding the parse AND the shrink guard while
   281	  // marker-sanity checks stay green. Demote to no-frontmatter so every entry is
   282	  // recovered from the body instead.
   283	  const fmRaw = fmMatch ? fmMatch[0] : "";
   284	  const fmValid = fmRaw !== "" && !fmRaw.includes(BEGIN_MARKER) && !fmRaw.includes(END_MARKER);
   285	  const frontmatter = fmValid ? fmRaw.replace(/\r\n/g, "\n") : "";
   286	  const afterFm = fmValid ? content.slice(fmRaw.length) : content;
   287	
   288	  const bodyLines: string[] = [];
   289	  const entries: string[] = [];
   290	  const seen = new Set<string>();
   291	
   292	  for (const line of afterFm.split(/\r?\n/)) {
   293	    const t = line.trim();
   294	    if (t === BEGIN_MARKER || t === END_MARKER) continue;
   295	    if (t.length > 0 && PREFIX_PATTERN.test(t)) {
   296	      if (!seen.has(t)) {
   297	        seen.add(t);
   298	        entries.push(t);
   299	      }
   300	      continue;
   301	    }
   302	    bodyLines.push(line);
   303	  }
   304	
   305	  // Trailing blank body lines are separator artifacts; serialize re-adds exactly
   306	  // one, keeping parse→serialize→parse byte-stable.
   307	  while (bodyLines.length > 0 && bodyLines[bodyLines.length - 1].trim() === "") {
   308	    bodyLines.pop();
   309	  }
   310	
   311	  return { frontmatter, bodyLines, entries };
   312	}
   313	
   314	function updateFrontmatterTimestamp(frontmatter: string): string {
   315	  if (!frontmatter) return frontmatter;
   316	  const now = new Date().toISOString();
   317	  // Replace last_updated value
   318	  if (/^last_updated:.*$/m.test(frontmatter)) {
   319	    return frontmatter.replace(/^last_updated:.*$/m, `last_updated: ${now}`);
   320	  }
   321	  // Add it before the closing ---
   322	  return frontmatter.replace(/\n---\n$/, `\nlast_updated: ${now}\n---\n`);
   323	}
   324	
   325	function updateFrontmatterUpdatedBy(frontmatter: string, by: string): string {
   326	  if (!frontmatter) return frontmatter;
   327	  if (/^last_updated_by:.*$/m.test(frontmatter)) {
   328	    return frontmatter.replace(/^last_updated_by:.*$/m, `last_updated_by: ${by}`);
   329	  }
   330	  return frontmatter.replace(/\n---\n$/, `\nlast_updated_by: ${by}\n---\n`);
   331	}
   332	
   333	/**
   334	 * Always emits the canonical shape — frontmatter → body → BEGIN → entries → END →
   335	 * trailing newline. No self-heal branches: there is exactly one output shape, so a
   336	 * single write converges any corrupted file and a repeat write is byte-identical.
   337	 */
   338	export function serializeMemoryContent(
   339	  parsed: ParsedMemoryFile,
   340	  newEntries: string[],
   341	  updatedBy: string,
   342	): string {
   343	  let fm = updateFrontmatterTimestamp(parsed.frontmatter);
   344	  fm = updateFrontmatterUpdatedBy(fm, updatedBy);
   345	
   346	  let out = fm;
   347	  if (parsed.bodyLines.length > 0) out += parsed.bodyLines.join("\n") + "\n\n";
   348	  out += BEGIN_MARKER + "\n";
   349	  if (newEntries.length > 0) out += newEntries.join("\n") + "\n";
   350	  out += END_MARKER + "\n";
   351	  return out;
   352	}
   353	
   354	// ── Atomic write with lock ──
   355	
   356	function withLock<T>(filePath: string, action: () => T): T | SetEntriesErrLock | SetEntriesErrIO {
   357	  const lockPath = `${filePath}.lock`;
   358	  let fd: number | null = null;
   359	  try {
   360	    fd = openSync(lockPath, "wx"); // O_CREAT | O_EXCL
   361	  } catch (e: any) {
   362	    if (e?.code === "EEXIST") {
   363	      return {
   364	        ok: false,
   365	        code: "ELOCK_HELD",
   366	        message: `Lock held by another writer: ${lockPath}. Investigate stale lock if persistent.`,
   367	      };
   368	    }
   369	    return {
   370	      ok: false,
   371	      code: "EWRITE_FAILED",
   372	      message: `Failed to acquire lock: ${e?.message || String(e)}`,
   373	    };
   374	  }
   375	
   376	  try {
   377	    const result = action();
   378	    return result;
   379	  } catch (e: any) {
   380	    return {
   381	      ok: false,
   382	      code: "EWRITE_FAILED",
   383	      message: `Write action threw: ${e?.message || String(e)}`,
   384	    };
   385	  } finally {
   386	    try {
   387	      if (fd !== null) closeSync(fd);
   388	    } catch { /* ignore */ }
   389	    try {
   390	      unlinkSync(lockPath);
   391	    } catch { /* lockfile cleanup best-effort */ }
   392	  }
   393	}
   394	
   395	// ── Per-write snapshots (recoverability) ──
   396	// Every Tier-A write snapshots the PRIOR file content to a ring buffer before
   397	// overwriting. set-overwrite has a "wipe the whole file" blast radius; git only
   398	// covers between commits. This makes every individual autonomic write reversible
   399	// via `MemoryRestore.ts`. Cheap: one file copy of <13KB, capped at 30 per file.
   400	const SNAPSHOT_DIR = pathResolve(CLAUDE_ROOT, "LIFEOS/MEMORY/OBSERVABILITY/memory-snapshots");
   401	const SNAPSHOT_RING = 30;
   402	
   403	function snapshotBeforeWrite(absPath: string, priorContent: string): void {
   404	  try {
   405	    mkdirSync(SNAPSHOT_DIR, { recursive: true });
   406	    const base = absPath.split("/").pop()!.replace(/\.md$/, "");
   407	    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
   408	    writeFileSync(pathResolve(SNAPSHOT_DIR, `${base}__${stamp}.md`), priorContent, "utf8");
   409	    // Trim the ring: keep the newest SNAPSHOT_RING per base file.
   410	    const mine = readdirSync(SNAPSHOT_DIR)
   411	      .filter((f: string) => f.startsWith(`${base}__`))
   412	      .sort(); // ISO stamp sorts chronologically
   413	    for (const stale of mine.slice(0, Math.max(0, mine.length - SNAPSHOT_RING))) {
   414	      try { rmSync(pathResolve(SNAPSHOT_DIR, stale)); } catch { /* best-effort */ }
   415	    }
   416	  } catch {
   417	    // Snapshotting is best-effort; never fail a write because the backup failed.
   418	  }
   419	}
   420	
   421	function atomicWrite(filePath: string, content: string): true | SetEntriesErrIO {
   422	  const tmpPath = `${filePath}.tmp`;
   423	  try {
   424	    // O_EXCL ("wx") after a best-effort unlink: a symlink planted at the
   425	    // predictable tmpPath would otherwise be written THROUGH — the write lands on
   426	    // its target before the rename ever runs. O_EXCL refuses any pre-existing
   427	    // path, symlinks included. (public PR #1593, @anikinsasha)
   428	    try { unlinkSync(tmpPath); } catch { /* absent is the normal case */ }
   429	    writeFileSync(tmpPath, content, { encoding: "utf8", flag: "wx" });
   430	    // fsync the tmp file for durability before rename
   431	    const fd = openSync(tmpPath, "r+");
   432	    try {
   433	      fsyncSync(fd);
   434	    } finally {
   435	      closeSync(fd);
   436	    }
   437	    renameSync(tmpPath, filePath);
   438	    // fsync the containing directory so the rename itself is durable — without it
   439	    // a power/kernel crash can roll the rename back despite this returning ok.
   440	    try {
   441	      const dirFd = openSync(dirname(filePath), "r");
   442	      try { fsyncSync(dirFd); } finally { closeSync(dirFd); }
   443	    } catch { /* dir fsync unsupported on some filesystems — best-effort */ }
   444	    return true;
   445	  } catch (e: any) {
   446	    try { unlinkSync(tmpPath); } catch { /* ignore */ }
   447	    return {
   448	      ok: false,
   449	      code: "EWRITE_FAILED",
   450	      message: `Atomic write failed: ${e?.message || String(e)}`,
   451	    };
   452	  }
   453	}
   454	
   455	// ── Observability ──
   456	
   457	function appendWriteLog(row: Record<string, unknown>): void {
   458	  try {
   459	    mkdirSync(dirname(OBSERVABILITY_PATH), { recursive: true });
   460	    appendFileSync(OBSERVABILITY_PATH, JSON.stringify(row) + "\n", "utf8");
   461	  } catch {
   462	    // Observability is best-effort; never fail a write because logging failed.
   463	  }
   464	}
   465	
   466	function logWriteEvent(
   467	  filePath: string,
   468	  result: SetEntriesOk,
   469	  updatedBy?: string,
   470	): void {
   471	  appendWriteLog({
   472	    ts: new Date().toISOString(),
   473	    file: filePath.replace(CLAUDE_ROOT + "/", ""),
   474	    updated_by: updatedBy ?? "unknown",
   475	    rejected: false,
   476	    prior_count: result.prior_count,
   477	    new_count: result.new_count,
   478	    accepted: result.accepted,
   479	    dropped_malformed: result.dropped_malformed,
   480	    dropped_overlength: result.dropped_overlength,
   481	    dropped_duplicates: result.dropped_duplicates,
   482	    evictions: result.evictions,
   483	    additions: result.additions,
   484	  });
   485	}
   486	
   487	/**
   488	 * Log a write the guard REFUSED, to the same log as accepted writes.
   489	 *
   490	 * The rejection has to be written here, not just returned: the memory-review
   491	 * hook spawns the reviewer with `stdio: "ignore"`, so a refusal that only
   492	 * travels back in the result object goes to /dev/null and the block is
   493	 * invisible to every surface meant to report it (public issue #1761,
   494	 * @jacobo-ortiz). The eviction and addition lists are logged in full — a
   495	 * blocked write is precisely the sample you need to tell erosion from
   496	 * consolidation later.
   497	 */
   498	function logRejectedWrite(
   499	  filePath: string,
   500	  rejection: { code: string; message: string; prior_count: number; new_count: number },
   501	  delta: { evictions: string[]; additions: string[] },
   502	  updatedBy?: string,
   503	): void {
   504	  appendWriteLog({
   505	    ts: new Date().toISOString(),
   506	    file: filePath.replace(CLAUDE_ROOT + "/", ""),
   507	    updated_by: updatedBy ?? "unknown",
   508	    rejected: true,
   509	    rejection_code: rejection.code,
   510	    rejection_message: rejection.message,
   511	    prior_count: rejection.prior_count,
   512	    new_count: rejection.new_count,
   513	    evictions: delta.evictions,
   514	    additions: delta.additions,
   515	  });
   516	}
   517	
   518	// ── Public API ──
   519	
   520	export interface SetEntriesOptions {
   521	  /** Who is writing — appears in the file's frontmatter last_updated_by. */
   522	  updatedBy?: string;
   523	  /** Bypass the catastrophic-shrink guard (legitimate full-clear / restore). */
   524	  allowDrastic?: boolean;
   525	}
   526	
   527	export function setEntries(
   528	  filePath: string,
   529	  entries: string[],
   530	  options: SetEntriesOptions = {},
   531	): SetEntriesResult {
   532	  const managed = memoryAccess("set", {path: pathResolve(filePath), entries, request_id: randomUUID(),
   533	    observed_revision: observedMemoryRevision(filePath), allow_drastic: options.allowDrastic === true},
   534	    (value): value is SetEntriesResult => memoryObject(value) && (value.ok === true
   535	      ? ["accepted", "dropped_malformed", "dropped_overlength", "dropped_duplicates", "prior_count", "new_count"].every(key => typeof value[key] === "number")
   536	        && Array.isArray(value.evictions) && Array.isArray(value.additions)
   537	      : value.ok === false && ["EINVAL_PATH", "EWRITE_FAILED"].includes(String(value.code)) && typeof value.message === "string"));
   538	  if (managed !== undefined) {
   539	    if (!managed.ok) return {ok: false, code: "EWRITE_FAILED", message: managed.message};
   540	    return managed;
   541	  }
   542	  const pathCheck = validatePath(filePath);
   543	  if (!("abs" in pathCheck)) return pathCheck;
   544	  const abs = pathCheck.abs;
   545	
   546	  if (!existsSync(abs)) {
   547	    return {
   548	      ok: false,
   549	      code: "EINVAL_PATH",
   550	      message: `Memory file does not exist (scaffold it first): ${abs}`,
   551	    };
   552	  }
   553	
   554	  const validated = validateAndDedup(entries);
   555	  const submitted = validated.accepted.length;
   556	  const indexedSubmission = validated.accepted.map((e, i) => `[${i}] ${e}`);
   557	
   558	  if (submitted > MAX_ENTRIES) {
   559	    return {
   560	      ok: false,
   561	      code: "EAT_CAP",
   562	      message: `Memory file cap is ${MAX_ENTRIES} entries — your submission has ${submitted} accepted+deduped entries. Trim ${submitted - MAX_ENTRIES} before re-submitting.`,
   563	      over_count: submitted - MAX_ENTRIES,
   564	      cap: MAX_ENTRIES,
   565	      indexed_submission: indexedSubmission,
   566	    };
   567	  }
   568	
   569	  const result = withLock(abs, () => {
   570	    const content = readFileSync(abs, "utf8");
   571	    const parsed = parseMemoryContent(content);
   572	    const priorEntries = parsed.entries;
   573	    const newEntries = validated.accepted;
   574	
   575	    // Compute the symmetric delta: evictions (present before, absent now) and
   576	    // additions (absent before, present now). Both feed the visibility surface.
   577	    const newSet = new Set(newEntries);
   578	    const priorSet = new Set(priorEntries);
   579	    const evictions = priorEntries.filter((e) => !newSet.has(e));
   580	    const additions = newEntries.filter((e) => !priorSet.has(e));
   581	
   582	    // Catastrophic-shrink guard (computed IN-LOCK against the just-read prior
   583	    // state, so it can't race a concurrent write). set-overwrite REPLACES the
   584	    // file, so a hallucinated empty/tiny reviewer list would wipe real memory
   585	    // (this exact wipe happened once during a cross-vendor audit). We block two
   586	    // shapes only — and deliberately ALLOW large honest consolidation (many
   587	    // drops accompanied by additions), so the reviewer can still shrink hard
   588	    // when it's genuinely merging. Bypass for legitimate full-clears via opts.
   589	    if (!options.allowDrastic && priorEntries.length >= 10) {
   590	      const FLOOR = 3;
   591	      const massDeleteNoAdd = evictions.length > priorEntries.length * 0.5 && additions.length === 0;
   592	      if (newEntries.length < FLOOR || massDeleteNoAdd) {
   593	        const shrinkErr: SetEntriesErrShrink = {
   594	          ok: false,
   595	          code: "ESUSPECT_SHRINK",
   596	          message: `Refused: op would shrink ${priorEntries.length} → ${newEntries.length} entries (${evictions.length} dropped, ${additions.length} added). Near-empty results and mass-deletion-without-curation are blocked as likely-bad output. A real consolidation that drops many should also ADD merged entries.`,
   597	          prior_count: priorEntries.length,
   598	          new_count: newEntries.length,
   599	        };
   600	        logRejectedWrite(abs, shrinkErr, { evictions, additions }, options.updatedBy);
   601	        return shrinkErr;
   602	      }
   603	
   604	      // Slow-erosion guard (public issue #1761, @jacobo-ortiz): the shapes
   605	      // above only catch catastrophes. The failure that actually destroys
   606	      // memory is LLM re-transcription quietly dropping a few entries per
   607	      // cycle — each write ~10% smaller, each carrying additions, so nothing
   608	      // above fires; 12 durable rules died in 48h that way on a reporter's
   609	      // install. Net loss of EROSION_LIMIT+ entries in ONE write is blocked;
   610	      // deliberate consolidation passes with allowDrastic. Replayed against
   611	      // 94 historical writes by the reporter: 5 blocked, all genuine erosion,
   612	      // 0 false positives.
   613	      const EROSION_LIMIT = 2;
   614	      const netLoss = evictions.length - additions.length;
   615	      if (netLoss >= EROSION_LIMIT) {
   616	        const erosionErr: SetEntriesErrErosion = {
   617	          ok: false,
   618	          code: "ESUSPECT_EROSION",
   619	          message: `Refused: op would net-drop ${netLoss} entries (${priorEntries.length} → ${newEntries.length}: ${evictions.length} dropped, ${additions.length} added). Slow erosion via re-transcription is blocked. If this is deliberate consolidation, retry with allowDrastic: true.`,
   620	          prior_count: priorEntries.length,
   621	          new_count: newEntries.length,
   622	        };
   623	        logRejectedWrite(abs, erosionErr, { evictions, additions }, options.updatedBy);
   624	        return erosionErr;
   625	      }
   626	    }
   627	
   628	    // Snapshot the prior content before we overwrite — individual-write recovery.
   629	    snapshotBeforeWrite(abs, content);
   630	
   631	    const newContent = serializeMemoryContent(parsed, newEntries, options.updatedBy || "MemoryWriter");
   632	    const writeRes = atomicWrite(abs, newContent);
   633	    if (writeRes !== true) return writeRes;
   634	
   635	    const ok: SetEntriesOk = {
   636	      ok: true,
   637	      accepted: newEntries.length,
   638	      dropped_malformed: validated.malformed,
   639	      dropped_overlength: validated.overlength,
   640	      dropped_duplicates: validated.duplicates,
   641	      prior_count: priorEntries.length,
   642	      new_count: newEntries.length,
   643	      evictions,
   644	      additions,
   645	    };
   646	    logWriteEvent(abs, ok, options.updatedBy);
   647	    return ok;
   648	  });
   649	
   650	  return result;
   651	}
   652	
   653	export function read(filePath: string): ReadResult | SetEntriesErrPath {
   654	  const managed = memoryAccess("read", {path: pathResolve(filePath)},
   655	    (value): value is ReadResult | SetEntriesErrPath => memoryObject(value) && (Array.isArray(value.entries)
   656	      ? value.entries.every(entry => typeof entry === "string") && ["count", "chars_used", "cap_entries", "cap_chars"].every(key => typeof value[key] === "number")
   657	        && Array.isArray(value.dropped_invalid)
   658	      : value.ok === false && value.code === "EINVAL_PATH" && typeof value.message === "string"));
   659	  if (managed !== undefined) return managed;
   660	  const pathCheck = validatePath(filePath);
   661	  if (!("abs" in pathCheck)) return pathCheck;
   662	  const abs = pathCheck.abs;
   663	
   664	  if (!existsSync(abs)) {
   665	    // Graceful degradation: missing file reads as zero entries
   666	    return {
   667	      entries: [],
   668	      count: 0,
   669	      chars_used: 0,
   670	      cap_entries: MAX_ENTRIES,
   671	      cap_chars: MAX_ENTRIES * MAX_CHARS_PER_ENTRY,
   672	      dropped_invalid: [],
   673	    };
   674	  }
   675	
   676	  const content = readFileSync(abs, "utf8");
   677	  const parsed = parseMemoryContent(content);
   678	  // Entries invalid at read time are excluded from `entries` but REPORTED, never
   679	  // silently swallowed: a set-overwrite computed from `entries` would otherwise
   680	  // erase them with no trace anywhere, since the write's dropped_* counts only
   681	  // cover the submission, which by then no longer contains them.
   682	  const valid = validateAndDedup(parsed.entries);
   683	  const acceptedSet = new Set(valid.accepted);
   684	  const dropped_invalid: ReadResult["dropped_invalid"] = [];
   685	  for (const entry of parsed.entries) {
   686	    if (acceptedSet.has(entry)) continue;
   687	    const m = entry.match(PREFIX_PATTERN);
   688	    const overlength = !!m && entry.slice(m[0].length).length > MAX_CHARS_PER_ENTRY;
   689	    dropped_invalid.push({ entry, reason: overlength ? "overlength" : "malformed" });
   690	  }
   691	  const chars_used = valid.accepted.reduce((sum, e) => sum + e.length, 0);
   692	
   693	  return {
   694	    entries: valid.accepted,
   695	    count: valid.accepted.length,
   696	    chars_used,
   697	    cap_entries: MAX_ENTRIES,
   698	    cap_chars: MAX_ENTRIES * MAX_CHARS_PER_ENTRY,
   699	    dropped_invalid,
   700	  };
   701	}
   702	
   703	// ── CLI ──
   704	
   705	function smokeTest(): number {
   706	  console.log("MemoryWriter smoke test starting…");
   707	
   708	  // Pure canonical-rebuild fixtures — NO filesystem, and in particular NOT the
   709	  // live memory files. The pre-port smoke test ran setEntries against the real
   710	  // PRINCIPAL_MEMORY.md and its step-7 cleanup submitted [], so running
   711	  // `bun MemoryWriter.ts test` on a populated install WIPED real memory.
   712	  // Write-path coverage lives in test/tools/MemoryWriter.test.ts.
   713	  // (public PR #1593, @anikinsasha)
   714	  const corrupted =
   715	    [
   716	      "---",
   717	      "schema_version: 1",
   718	      "---",
   719	      "# Hot-Layer Memory",
   720	      "",
   721	      "<!-- template comment -->",
   722	      END_MARKER,
   723	      BEGIN_MARKER,
   724	      END_MARKER,
   725	      END_MARKER,
   726	      "FACT: legacy invalid-prefix orphan stays in body",
   727	      "NAME: Fixture User",
   728	      `RULE: keep the ${END_MARKER} marker pair intact`,
   729	      END_MARKER,
   730	    ].join("\n") + "\n";
   731	
   732	  const p1 = parseMemoryContent(corrupted);
   733	  if (p1.entries.length !== 2) {
   734	    console.error(`FAIL: corrupted fixture expected 2 entries, got ${p1.entries.length}`);
   735	    return 1;
   736	  }
   737	  if (p1.entries[1] !== `RULE: keep the ${END_MARKER} marker pair intact`) {
   738	    console.error(`FAIL: marker-substring entry truncated on parse: ${p1.entries[1]}`);
   739	    return 1;
   740	  }
   741	  if (!p1.bodyLines.some((l) => l.startsWith("FACT: "))) {
   742	    console.error("FAIL: invalid-prefix orphan was silently absorbed instead of kept in body");
   743	    return 1;
   744	  }
   745	  console.log(`  parse: recovered ${p1.entries.length} entries from an END-before-BEGIN + END-stack file`);
   746	
   747	  // One write converges to canonical shape: exactly one BEGIN, one END, in order.
   748	  const rebuilt = serializeMemoryContent(p1, p1.entries, "smoke-test");
   749	  const begins = rebuilt.split("\n").filter((l) => l.trim() === BEGIN_MARKER).length;
   750	  const ends = rebuilt.split("\n").filter((l) => l.trim() === END_MARKER).length;
   751	  if (begins !== 1 || ends !== 1) {
   752	    console.error(`FAIL: canonical rebuild expected 1 BEGIN / 1 END, got ${begins} / ${ends}`);
   753	    return 1;
   754	  }
   755	  if (rebuilt.indexOf(BEGIN_MARKER) > rebuilt.indexOf(END_MARKER)) {
   756	    console.error("FAIL: canonical rebuild left END before BEGIN");
   757	    return 1;
   758	  }
   759	  console.log(`  serialize: converged ${begins} BEGIN / ${ends} END, in order`);
   760	
   761	  // Idempotency: a second round-trip is byte-identical apart from the stamp.
   762	  const stripStamp = (s: string) => s.replace(/^last_updated: .*$/m, "last_updated: X");
   763	  const again = serializeMemoryContent(parseMemoryContent(rebuilt), p1.entries, "smoke-test");
   764	  if (stripStamp(again) !== stripStamp(rebuilt)) {
   765	    console.error("FAIL: second write was not byte-identical — rebuild is not idempotent");
   766	    return 1;
   767	  }
   768	  console.log("  idempotency: second write byte-identical");
   769	
   770	  // Entry set is preserved verbatim across the heal (zero set-diff).
   771	  const after = parseMemoryContent(rebuilt).entries;
   772	  if (after.join("\u0000") !== p1.entries.join("\u0000")) {
   773	    console.error("FAIL: entry set changed across the heal");
   774	    return 1;
   775	  }
   776	  console.log(`  preservation: ${after.length}/${p1.entries.length} entries survived verbatim`);
   777	
   778	  // CRLF and frontmatter-less shapes parse the same way.
   779	  const crlf = `${BEGIN_MARKER}\r\nNAME: CRLF User\r\n${END_MARKER}\r\n`;
   780	  if (parseMemoryContent(crlf).entries.length !== 1) {
   781	    console.error("FAIL: CRLF file did not parse to 1 entry");
   782	    return 1;
   783	  }
   784	  if (parseMemoryContent("NAME: No Frontmatter\n").entries.length !== 1) {
   785	    console.error("FAIL: frontmatter-less file did not parse to 1 entry");
   786	    return 1;
   787	  }
   788	  console.log("  tolerance: CRLF + frontmatter-less parse correctly");
   789	
   790	  // Path allowlist still refuses anything outside the two memory files.
   791	  const w = setEntries("/etc/passwd", ["NAME: hacker"], { updatedBy: "smoke-test" });
   792	  if (w.ok || w.code !== "EINVAL_PATH") {
   793	    console.error(`FAIL: expected EINVAL_PATH for /etc/passwd, got ${w.ok ? "success" : w.code}`);
   794	    return 1;
   795	  }
   796	  console.log("  allowlist: /etc/passwd correctly rejected with EINVAL_PATH");
   797	
   798	  console.log("✓ MemoryWriter smoke test PASSED (no live memory file was touched)");
   799	  return 0;
   800	}
   801	
   802	async function main() {
   803	  const cmd = process.argv[2];
   804	  if (cmd === "test") {
   805	    process.exit(smokeTest());
   806	  }
   807	  if (cmd === "read") {
   808	    const path = process.argv[3];
   809	    if (!path) {
   810	      console.error("Usage: bun MemoryWriter.ts read <path>");
   811	      process.exit(2);
   812	    }
   813	    const r = read(path);
   814	    console.log(JSON.stringify(r, null, 2));
   815	    process.exit("code" in r ? 1 : 0);
   816	  }
   817	  if (cmd === "set") {
   818	    const path = process.argv[3];
   819	    if (!path) {
   820	      console.error("Usage: bun MemoryWriter.ts set <path>  (entries via stdin, one per line)");
   821	      process.exit(2);
   822	    }
   823	    const stdin = await new Promise<string>((resolve) => {
   824	      let data = "";
   825	      process.stdin.setEncoding("utf8");
   826	      process.stdin.on("data", (chunk) => { data += chunk; });
   827	      process.stdin.on("end", () => resolve(data));
   828	    });
   829	    const entries = stdin.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
   830	    const r = setEntries(path, entries, { updatedBy: "cli" });
   831	    console.log(JSON.stringify(r, null, 2));
   832	    process.exit(r.ok ? 0 : 1);
   833	  }
   834	  console.error("Usage: bun MemoryWriter.ts {test|read <path>|set <path>}");
   835	  process.exit(2);
   836	}
   837	
   838	if (import.meta.main) {
   839	  main();
   840	}
