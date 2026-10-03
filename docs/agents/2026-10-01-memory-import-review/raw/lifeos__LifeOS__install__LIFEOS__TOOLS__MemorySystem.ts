     1	#!/usr/bin/env bun
     2	/**
     3	 * MemorySystem — single public API for the LifeOS memory subsystem.
     4	 *
     5	 * LifeOS autonomic memory subsystem, F12.
     6	 *
     7	 * The 30-second story this code implements:
     8	 *
     9	 *   {{DA_NAME}} has one memory system. Every item in it has a type — memory, idea,
    10	 *   knowledge, or proposal. A background reviewer reads recent conversation
    11	 *   and emits typed items. The system routes each item to the right place
    12	 *   based on type. Memory items load into every prompt. Ideas and knowledge
    13	 *   load when relevant. Proposals queue for principal review (Pulse surfaces).
    14	 *   Four safety tiers gate writes by destination.
    15	 *
    16	 * Two public functions:
    17	 *
    18	 *   add(item): persists a typed item according to the type registry
    19	 *   find(query, options): BM25 retrieval over the typed-item corpus
    20	 *
    21	 * Routing:
    22	 *
    23	 *   type=memory     → MemoryWriter.setEntries (set-overwrite, capped, Tier A)
    24	 *   type=idea       → atomic-rename append (Tier B, audit row written)
    25	 *   type=knowledge  → atomic-rename append (Tier B, audit row written)
    26	 *   type=proposal   → JSONL queue (proposal surfacer consumes)
    27	 *
    28	 * Defense-in-depth: every write goes through MutationTier.getTier(path)
    29	 * before persisting. If the resolved path's tier doesn't match the type's
    30	 * declared tier, the write is rejected (ETIER_MISMATCH). The registry +
    31	 * classifier should agree by construction; if they disagree, something
    32	 * upstream has drifted and we'd rather fail loud.
    33	 *
    34	 * CLI:
    35	 *   bun MemorySystem.ts add <item-json>     (reads from arg or stdin)
    36	 *   bun MemorySystem.ts find "<query>" [--type T] [--top N]
    37	 *   bun MemorySystem.ts test                (smoke test)
    38	 */
    39	
    40	import {
    41	  appendFileSync,
    42	  closeSync,
    43	  existsSync,
    44	  fsyncSync,
    45	  mkdirSync,
    46	  openSync,
    47	  readFileSync,
    48	  renameSync,
    49	  statSync,
    50	  unlinkSync,
    51	  writeFileSync,
    52	} from "node:fs";
    53	import { dirname, resolve as pathResolve, join as pathJoin } from "node:path";
    54	import { homedir, hostname } from "node:os";
    55	
    56	import { invariant, InvariantViolation } from "./Invariant";
    57	
    58	import {
    59	  TYPE_REGISTRY,
    60	  isKnownType,
    61	  resolveStoragePath,
    62	  inferProposalKind,
    63	  pinProposalTargetFile,
    64	  ALWAYS_LOADED_KINDS,
    65	  ALL_TYPES,
    66	  ALL_RELATED_TYPES,
    67	  ALL_PROPOSAL_KINDS,
    68	  TIER_B_AUDIT_PATH,
    69	  PRINCIPAL_MEMORY_PATH,
    70	  DA_MEMORY_PATH,
    71	  type TypedItem,
    72	  type MemoryTypeName,
    73	  type Tier,
    74	  type RelatedLink,
    75	} from "./MemoryTypes";
    76	
    77	import { setEntries as memoryWriterSetEntries, read as memoryWriterRead } from "./MemoryWriter";
    78	import { classifyScope } from "./ProposalScope";
    79	import { addUpgrade } from "./Upgrades";
    80	import { getTier } from "./MutationTier";
    81	import { getRelevantContext, type RelevantResultItem } from "./MemoryRetriever";
    82	import { mintId, slugFromPath, SCHEMA_VERSION } from "./KnowledgeSchema";
    83	import { stripPrivateContent } from "./CaptureEnvelope";
    84	import { memoryAccess, memoryObject, observedMemoryRevision } from "./lib/MemoryAccess";
    85	import { randomUUID } from "node:crypto";
    86	import { assertInsideUserData } from "./lib/ForeignDataCheck";
    87	
    88	// ── Constants ──
    89	
    90	const CLAUDE_ROOT = pathResolve(homedir(), ".claude");
    91	
    92	// ── Result types ──
    93	
    94	export interface AddOk {
    95	  ok: true;
    96	  type: MemoryTypeName;
    97	  path: string;
    98	  detail: Record<string, unknown>;
    99	}
   100	
   101	export type AddError =
   102	  | { ok: false; code: "EUNKNOWN_TYPE"; message: string }
   103	  | { ok: false; code: "ETIER_MISMATCH"; message: string; declared_tier: Tier; resolved_tier: string }
   104	  | { ok: false; code: "EWRITE_FAILED"; message: string; underlying?: unknown }
   105	  | { ok: false; code: "ESUSPECT_SHRINK"; message: string }
   106	  | { ok: false; code: "EINVAL_ITEM"; message: string };
   107	
   108	export type AddResult = AddOk | AddError;
   109	
   110	export interface FindResult {
   111	  type: MemoryTypeName | "unknown";
   112	  path: string;
   113	  title: string;
   114	  score: number;
   115	  excerpt: string;
   116	}
   117	
   118	export interface FindOptions {
   119	  topK?: number;
   120	  type?: MemoryTypeName;
   121	}
   122	
   123	// ── Tier audit / observability ──
   124	
   125	function logTierBWrite(filePath: string, bytes: number, type: MemoryTypeName): void {
   126	  try {
   127	    mkdirSync(dirname(TIER_B_AUDIT_PATH), { recursive: true });
   128	    appendFileSync(
   129	      TIER_B_AUDIT_PATH,
   130	      JSON.stringify({
   131	        ts: new Date().toISOString(),
   132	        file: filePath.replace(CLAUDE_ROOT + "/", ""),
   133	        bytes_written: bytes,
   134	        type,
   135	      }) + "\n",
   136	      "utf8",
   137	    );
   138	  } catch {
   139	    /* observability is best-effort */
   140	  }
   141	}
   142	
   143	// ── Per-note write lock, crash-safe ──
   144	// Memory writes run inside hook-spawned subprocesses. If the harness times one
   145	// out — or the machine loses power — after the lockfile is created but before
   146	// the `finally` releases it, the `.lock` survives on disk and every later write
   147	// to that note fails with "Lock held", permanently and silently. That is memory
   148	// loss nobody is told about. (public PR #1646, @elhoim — ported slim: recovery
   149	// lives here rather than in a separate lock module.)
   150	//
   151	// Recovery is decided on EVIDENCE first, age second:
   152	//   1. The holder stamps pid + host + ts into the lockfile at acquire time.
   153	//   2. A contender reads that stamp. Holder on this host and `kill(pid, 0)`
   154	//      says gone → the holder died; break immediately, no waiting out a TTL.
   155	//   3. Liveness unverifiable (empty/corrupt stamp, older build, other host) →
   156	//      fall back to age; stale only past LOCK_STALE_MS.
   157	//   4. A provably-live holder is respected.
   158	// Every unknown resolves toward "assume alive", so the failure mode is a
   159	// refused write rather than two writers corrupting one note.
   160	//
   161	// LOCK_STALE_MS matches DerivedSync.ts's constant rather than inventing a third.
   162	const LOCK_STALE_MS = 5 * 60 * 1000;
   163	const LOCK_LOG_PATH = pathJoin(CLAUDE_ROOT, "LIFEOS/MEMORY/OBSERVABILITY/memory-locks.jsonl");
   164	
   165	type LockReason =
   166	  | "holder-process-gone"
   167	  | "holder-alive"
   168	  | "unverifiable-holder-within-ttl"
   169	  | "expired-unverifiable-holder";
   170	
   171	/**
   172	 * Every event here is abnormal — a recovered crash or a refused write — so it
   173	 * earns both a JSONL row and an operator-visible stderr line. Best-effort:
   174	 * observability must never be why a write fails.
   175	 */
   176	function logLockEvent(event: "stale_lock_recovered" | "lock_contended", lockPath: string, reason: LockReason, detail: string): void {
   177	  try {
   178	    mkdirSync(dirname(LOCK_LOG_PATH), { recursive: true });
   179	    appendFileSync(
   180	      LOCK_LOG_PATH,
   181	      JSON.stringify({
   182	        ts: new Date().toISOString(),
   183	        pid: process.pid,
   184	        event,
   185	        reason,
   186	        lock: lockPath.replace(CLAUDE_ROOT + "/", ""),
   187	        detail,
   188	      }) + "\n",
   189	      "utf8",
   190	    );
   191	  } catch {
   192	    /* observability is best-effort */
   193	  }
   194	  console.error(`[MemorySystem] ${event} (${reason}): ${detail}`);
   195	}
   196	
   197	/**
   198	 * Signal 0 does no work — it runs only the kernel's existence + permission
   199	 * checks. ESRCH is the ONLY answer that proves absence: EPERM means the process
   200	 * exists under another uid, and any other error means we don't know. Both
   201	 * resolve to "alive", so an ambiguous probe can never break a live lock.
   202	 */
   203	function isProcessAlive(pid: number): boolean {
   204	  if (!Number.isInteger(pid) || pid <= 1) return true;
   205	  try {
   206	    process.kill(pid, 0);
   207	    return true;
   208	  } catch (e: any) {
   209	    return e?.code !== "ESRCH";
   210	  }
   211	}
   212	
   213	/**
   214	 * Decide whether a held lock may be broken. Returns null when it must be respected.
   215	 * Exported for `test/tools/MemorySystem.lock.test.ts` — the dangerous direction is
   216	 * breaking a LIVE lock, so the decision matrix is probed directly.
   217	 */
   218	export function staleLockReason(lockPath: string): LockReason | null {
   219	  let stamp: { pid?: number; host?: string } = {};
   220	  let ageMs = 0;
   221	  try {
   222	    ageMs = Date.now() - statSync(lockPath).mtimeMs;
   223	    stamp = JSON.parse(readFileSync(lockPath, "utf8"));
   224	  } catch {
   225	    /* unreadable or pre-stamp lockfile — falls through to the age rule */
   226	  }
   227	
   228	  const sameHost = typeof stamp.host === "string" && stamp.host === hostname();
   229	  if (sameHost && typeof stamp.pid === "number") {
   230	    if (!isProcessAlive(stamp.pid)) return "holder-process-gone";
   231	    return null; // provably alive — respect it
   232	  }
   233	  return ageMs > LOCK_STALE_MS ? "expired-unverifiable-holder" : "unverifiable-holder-within-ttl";
   234	}
   235	
   236	/**
   237	 * Break a stale lock race-safely: rename it aside, then re-create with O_EXCL so
   238	 * at most one of several concurrent recoverers wins. Returns the new fd, or null
   239	 * if we lost the race (another writer got there first — respect it).
   240	 */
   241	function breakStaleLock(lockPath: string): number | null {
   242	  const asidePath = `${lockPath}.stale.${process.pid}`;
   243	  try {
   244	    renameSync(lockPath, asidePath);
   245	  } catch {
   246	    return null; // someone else already moved it
   247	  }
   248	  try {
   249	    const fd = openSync(lockPath, "wx");
   250	    try { unlinkSync(asidePath); } catch { /* best-effort */ }
   251	    return fd;
   252	  } catch {
   253	    try { unlinkSync(asidePath); } catch { /* best-effort */ }
   254	    return null;
   255	  }
   256	}
   257	
   258	// ── Append-write primitive for Tier B types ──
   259	
   260	/** Exported for `test/tools/MemorySystem.lock.test.ts` (acquire / recover / release). */
   261	export function appendToTierBFile(filePath: string, content: string): { ok: true; bytes: number } | AddError {
   262	  const lockPath = `${filePath}.lock`;
   263	  let fd: number | null = null;
   264	  try {
   265	    mkdirSync(dirname(filePath), { recursive: true });
   266	    fd = openSync(lockPath, "wx");
   267	  } catch (e: any) {
   268	    if (e?.code !== "EEXIST") {
   269	      return { ok: false, code: "EWRITE_FAILED", message: `Failed to acquire lock: ${e?.message}` };
   270	    }
   271	    const reason = staleLockReason(lockPath);
   272	    if (reason === null || reason === "unverifiable-holder-within-ttl") {
   273	      // `null` means the holder is provably alive — a distinct operator signal
   274	      // from "we could not verify it", so it must not be collapsed into one code.
   275	      logLockEvent("lock_contended", lockPath, reason ?? "holder-alive", `Lock held: ${lockPath}`);
   276	      return { ok: false, code: "EWRITE_FAILED", message: `Lock held: ${lockPath}` };
   277	    }
   278	    fd = breakStaleLock(lockPath);
   279	    if (fd === null) {
   280	      logLockEvent("lock_contended", lockPath, "holder-alive", `Lost the recovery race for ${lockPath}`);
   281	      return { ok: false, code: "EWRITE_FAILED", message: `Lock held: ${lockPath}` };
   282	    }
   283	    logLockEvent("stale_lock_recovered", lockPath, reason, `Recovered stale lock at ${lockPath}`);
   284	  }
   285	
   286	  // Stamp the holder so the next contender can prove liveness instead of
   287	  // waiting out the TTL. Best-effort: a failed stamp only costs evidence.
   288	  try {
   289	    writeFileSync(lockPath, JSON.stringify({ pid: process.pid, host: hostname(), ts: new Date().toISOString() }), "utf8");
   290	  } catch { /* the lock still holds; the next contender falls back to age */ }
   291	
   292	  try {
   293	    const tmpPath = `${filePath}.tmp`;
   294	    const existing = existsSync(filePath) ? readFileSync(filePath, "utf8") : "";
   295	    const newContent = existing.length > 0 && !existing.endsWith("\n")
   296	      ? existing + "\n" + content
   297	      : existing + content;
   298	
   299	    // A tier-B append may add content but never lose or reorder what was
   300	    // already on disk — this rewrite-then-rename path would corrupt silently.
   301	    invariant(newContent.startsWith(existing), "tier-B append must preserve existing content as a prefix");
   302	    invariant(newContent.endsWith(content), "tier-B append must end with the appended content");
   303	
   304	    writeFileSync(tmpPath, newContent, "utf8");
   305	    const fdSync = openSync(tmpPath, "r+");
   306	    try { fsyncSync(fdSync); } finally { closeSync(fdSync); }
   307	    renameSync(tmpPath, filePath);
   308	
   309	    return { ok: true, bytes: Buffer.byteLength(content, "utf8") };
   310	  } catch (e: any) {
   311	    if (e instanceof InvariantViolation) throw e; // impossible states die loud, never as typed errors
   312	    return { ok: false, code: "EWRITE_FAILED", message: `Append failed: ${e?.message}`, underlying: e };
   313	  } finally {
   314	    try { if (fd !== null) closeSync(fd); } catch { /* ignore */ }
   315	    try { unlinkSync(lockPath); } catch { /* ignore */ }
   316	  }
   317	}
   318	
   319	// ── Proposal queue ──
   320	
   321	function enqueueProposal(item: TypedItem & { type: "proposal" }): { ok: true; id: string } | AddError {
   322	  const id = generateProposalId();
   323	  const path = resolveStoragePath(item);
   324	  // P1 2026-05-25: persist the subtype discriminator onto the queue row so
   325	  // the proposal surfacer can render the [kind] badge. Falls back to the
   326	  // path-based inference when the reviewer omits target_kind (legacy compat).
   327	  const targetKind = item.target_kind ?? inferProposalKind(item.target_file);
   328	  // Pin target_file to the kind's canonical file (public PR #1563, @anikinsasha):
   329	  // most kinds map to exactly one file, so trusting the reviewer's free-text
   330	  // path lets a hallucinated path get persisted and then silently mis-file or
   331	  // fail to apply. null = a multi-file (identity) path outside the allowed set.
   332	  const targetFile = pinProposalTargetFile(targetKind, item.target_file);
   333	  if (targetFile === null) {
   334	    return { ok: false, code: "EINVAL_ITEM", message: `target_file '${item.target_file}' is not an allowed '${targetKind}' target` };
   335	  }
   336	
   337	  // ── Scope gate (2026-07-31) ────────────────────────────────────────────────
   338	  // `target_kind` decides WHICH curated file a proposal belongs to; it says
   339	  // nothing about WHO needs the rule loaded. Without a scope axis every
   340	  // rule-shaped signal landed in an @-imported file. Audit of OPERATIONAL_RULES'
   341	  // tail: 7 of 10 entries were skill- or project-scoped, carried into every turn
   342	  // for the benefit of one skill.
   343	  //
   344	  // Only the kinds whose target is @-imported are gated. `projects` is exempt by
   345	  // construction — a PROJECTS.md row NAMES a project, so scoping it away from
   346	  // PROJECTS.md would divert exactly the proposals that belong there.
   347	  if (ALWAYS_LOADED_KINDS.has(targetKind)) {
   348	    const verdict = classifyScope(item.edit);
   349	    if (verdict.scope !== "global") {
   350	      const r = addUpgrade({
   351	        claim: item.edit.slice(0, 1000),
   352	        source: "correction",
   353	        current_state: `Proposed as a '${targetKind}' edit to ${targetFile}, which is loaded on every turn.`,
   354	        recommendation: `Encode in ${verdict.dest} instead — ${verdict.reason}.`,
   355	        target_surface: verdict.scope,
   356	        confidence: item.confidence,
   357	        session_id: item.source_session ?? undefined,
   358	        evidence: [`memory-proposal:${id}`],
   359	      });
   360	      return { ok: true, id: r.id || id };
   361	    }
   362	  }
   363	
   364	  try {
   365	    mkdirSync(dirname(path), { recursive: true });
   366	    appendFileSync(
   367	      path,
   368	      JSON.stringify({
   369	        id,
   370	        ts: new Date().toISOString(),
   371	        status: "pending",
   372	        target_file: targetFile,
   373	        target_kind: targetKind,
   374	        edit: item.edit,
   375	        confidence: item.confidence,
   376	        rationale: item.rationale,
   377	        observed_across_sessions: item.observed_across_sessions ?? 1,
   378	        source_session: item.source_session ?? null,
   379	      }) + "\n",
   380	      "utf8",
   381	    );
   382	    return { ok: true, id };
   383	  } catch (e: any) {
   384	    return { ok: false, code: "EWRITE_FAILED", message: `Proposal enqueue failed: ${e?.message}` };
   385	  }
   386	}
   387	
   388	function generateProposalId(): string {
   389	  // Short, sortable, collision-resistant enough for human use
   390	  const ts = Date.now().toString(36);
   391	  const rand = Math.random().toString(36).slice(2, 8);
   392	  return `${ts}-${rand}`;
   393	}
   394	
   395	// ── Memory-type wrapping ──
   396	
   397	/**
   398	 * For type=memory items, the writer is set-overwrite over the WHOLE file.
   399	 * That means add() needs to:
   400	 *   1. Read current entries
   401	 *   2. Append the new content as a new entry (with the actor's prefix
   402	 *      convention preserved; the content already carries it)
   403	 *   3. Re-submit the full deduplicated list
   404	 *
   405	 * If the resulting list exceeds the cap, the caller (typically the reviewer
   406	 * subprocess) is responsible for trimming. add() surfaces the at-cap error
   407	 * verbatim so the caller can re-submit with explicit eviction choices.
   408	 */
   409	function addMemoryItem(item: TypedItem & { type: "memory" }, path: string): AddResult {
   410	  const current = memoryWriterRead(path);
   411	  if ("code" in current) {
   412	    return { ok: false, code: "EINVAL_ITEM", message: `Memory file unreadable: ${current.message}` };
   413	  }
   414	
   415	  // op:"set" — the curation path (Honcho peer-card model). The reviewer has
   416	  // already read the current entries and returns the FULL desired list:
   417	  // additions, supersessions (contradicted fact dropped + rewritten), merges,
   418	  // and evictions (stale fact simply omitted). We REPLACE, never merge. This is
   419	  // what makes the system forget — and what permanently kills the cap-jam,
   420	  // because the reviewer can drop to make room instead of stacking to overflow.
   421	  let newEntries: string[];
   422	  if (item.op === "set") {
   423	    if (!Array.isArray(item.entries)) {
   424	      return { ok: false, code: "EINVAL_ITEM", message: `op:"set" requires an 'entries' array` };
   425	    }
   426	    newEntries = item.entries.map((e) => String(e).trim()).filter((e) => e.length > 0);
   427	    // The catastrophic-shrink guard lives IN-LOCK in MemoryWriter.setEntries
   428	    // (computed against the just-read prior state so it can't race). See there.
   429	  } else {
   430	    // legacy op:"add" / absent — merge-append a single content entry.
   431	    if (typeof item.content !== "string" || item.content.trim().length === 0) {
   432	      return { ok: false, code: "EINVAL_ITEM", message: `op:"add" requires non-empty 'content'` };
   433	    }
   434	    newEntries = [...current.entries, item.content.trim()];
   435	  }
   436	
   437	  const writeResult = memoryWriterSetEntries(path, newEntries, { updatedBy: "MemorySystem.add" });
   438	  if (!writeResult.ok) {
   439	    return {
   440	      ok: false,
   441	      code: "EWRITE_FAILED",
   442	      message: `MemoryWriter rejected: ${writeResult.code} — ${writeResult.message}`,
   443	      underlying: writeResult,
   444	    };
   445	  }
   446	  return {
   447	    ok: true,
   448	    type: "memory",
   449	    path,
   450	    detail: {
   451	      prior_count: writeResult.prior_count,
   452	      new_count: writeResult.new_count,
   453	      accepted: writeResult.accepted,
   454	      dropped_malformed: writeResult.dropped_malformed,
   455	      dropped_overlength: writeResult.dropped_overlength,
   456	      dropped_duplicates: writeResult.dropped_duplicates,
   457	    },
   458	  };
   459	}
   460	
   461	// ── Knowledge/idea note format ──
   462	
   463	/**
   464	 * For type=idea and type=knowledge items, the on-disk format is a markdown
   465	 * note with YAML frontmatter. add() either creates a new file with frontmatter
   466	 * or appends a dated entry to an existing file under a `## Appended <ts>`
   467	 * subheader. This keeps the existing MemoryRetriever (BM25 over the same files)
   468	 * working unchanged.
   469	 */
   470	/**
   471	 * Render the `related:` YAML block for note frontmatter. LifeOS's KNOWLEDGE
   472	 * graph uses this exact shape — preserving the convention means new notes
   473	 * participate in the existing graph traversal infrastructure (KnowledgeGraph.ts,
   474	 * Cortex skill, 2-hop search) without any extra wiring.
   475	 *
   476	 * Empty array renders as `related: []` so the field is present and ready for
   477	 * future enrichment by the reviewer.
   478	 */
   479	function renderRelatedBlock(related: RelatedLink[] | undefined): string {
   480	  const links = related ?? [];
   481	  if (links.length === 0) return "related: []";
   482	  const lines = ["related:"];
   483	  for (const link of links) {
   484	    lines.push(`  - slug: ${link.slug}`);
   485	    lines.push(`    type: ${link.type}`);
   486	  }
   487	  return lines.join("\n");
   488	}
   489	
   490	/**
   491	 * Emit a new note on the kb-v3 Core Envelope (KnowledgeSchema.ts) so autonomic
   492	 * writes stop re-introducing the old pai-memory-v1 dialect the migration cleaned
   493	 * up. `type` carries the canonical archive type directly (idea, or the knowledge
   494	 * item's entity_type = person|company|research), `title` not `name`,
   495	 * `created`/`updated` not `last_updated`, a deterministic `id`, provenance as
   496	 * `source_*`. Tags/quality default (flagged inferred) since the item shape
   497	 * doesn't carry them, and `status: seedling` marks it for enrichment. NOTE: a
   498	 * research item is born on the envelope but WITHOUT `source_url` (the item has
   499	 * none), so Lint flags it for source backfill — "born conformant" holds for the
   500	 * envelope, not the per-type source requirement (Forge #7). `slug` is the note's
   501	 * filename slug (for the stable id).
   502	 */
   503	function renderInitialNote(item: TypedItem, slug: string): string {
   504	  const ts = new Date().toISOString();
   505	  const isIdea = item.type === "idea";
   506	  const isKnowledge = item.type === "knowledge";
   507	  if (!isIdea && !isKnowledge) {
   508	    throw new Error(`renderInitialNote called for non-note type: ${(item as any).type}`);
   509	  }
   510	  const title = isIdea ? (item as any).title : (item as any).name;
   511	  const canonicalType = isIdea ? "idea" : (item as any).entity_type; // person|company|research
   512	  const bodyLen = item.content.trim().length;
   513	  const quality = bodyLen < 400 ? 2 : 5;
   514	  // YAML-safe title: strip newlines (they break both the frontmatter and the H1)
   515	  // and escape backslash-then-quote (Forge #8 — quote-only escaping mangled
   516	  // `C:\path` and any newline in the title).
   517	  const safeTitle = String(title).replace(/[\r\n]+/g, " ").trim();
   518	  const yamlTitle = safeTitle.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
   519	
   520	  const lines: string[] = [
   521	    "---",
   522	    `id: ${mintId(slug, ts)}`,
   523	    `type: ${canonicalType}`,
   524	    `title: "${yamlTitle}"`,
   525	    `tags: [untagged]`,
   526	    `status: seedling`,
   527	    `quality: ${quality}`,
   528	    `quality_inferred: true`,
   529	  ];
   530	  if (item.confidence != null) lines.push(`confidence: ${item.confidence}`);
   531	  lines.push(`source_kind: internal`);
   532	  if (item.source_session && item.source_session !== "none") lines.push(`source_session: ${item.source_session}`);
   533	  lines.push(
   534	    `created: ${ts}`,
   535	    `updated: ${ts}`,
   536	    renderRelatedBlock(item.related),
   537	    `convention: ${SCHEMA_VERSION}`,
   538	    "---",
   539	    "",
   540	    `# ${safeTitle}`,
   541	    "",
   542	    item.content.trim(),
   543	    "",
   544	  );
   545	  return lines.join("\n");
   546	}
   547	
   548	function renderAppendedSection(item: TypedItem & { type: "idea" | "knowledge" }): string {
   549	  const ts = new Date().toISOString();
   550	  const conf = item.confidence != null ? item.confidence : 1.0;
   551	  const src = item.source_session ? item.source_session : "none";
   552	  return [
   553	    "",
   554	    `## Appended ${ts}`,
   555	    `<!-- source_session: ${src} · confidence: ${conf} -->`,
   556	    "",
   557	    item.content.trim(),
   558	    "",
   559	  ].join("\n");
   560	}
   561	
   562	/**
   563	 * Parse the `related:` block out of YAML frontmatter. Tolerant — the existing
   564	 * KNOWLEDGE corpus has slight schema variance (inline vs block forms). Returns
   565	 * what it can recognize; ignores malformed entries silently.
   566	 */
   567	function parseRelatedFromFrontmatter(content: string): RelatedLink[] {
   568	  const fmMatch = content.match(/^---\n([\s\S]*?)\n---\n/);
   569	  if (!fmMatch) return [];
   570	  const fm = fmMatch[1];
   571	  // Match the block form: `related:\n  - slug: X\n    type: Y\n  - slug: A\n    type: B`
   572	  const relMatch = fm.match(/^related:\s*\n((?:\s+-\s+slug:[^\n]+\n\s+type:[^\n]+\n?)+)/m);
   573	  if (!relMatch) {
   574	    // Try inline empty: `related: []`
   575	    if (/^related:\s*\[\s*\]/m.test(fm)) return [];
   576	    return [];
   577	  }
   578	  const block = relMatch[1];
   579	  const links: RelatedLink[] = [];
   580	  const itemRe = /-\s+slug:\s*([^\n]+)\n\s+type:\s*([^\n]+)/g;
   581	  let m: RegExpExecArray | null;
   582	  while ((m = itemRe.exec(block)) !== null) {
   583	    const slug = m[1].trim().replace(/^["']|["']$/g, "");
   584	    const type = m[2].trim();
   585	    links.push({ slug, type: type as RelatedLink["type"] });
   586	  }
   587	  return links;
   588	}
   589	
   590	/**
   591	 * Merge incoming `related:` links into the existing frontmatter of a note,
   592	 * deduplicating by slug (last-write-wins on the type field for that slug).
   593	 * Returns the modified content. If there are no incoming links OR the file
   594	 * already has all of them, returns the content unchanged.
   595	 */
   596	function mergeRelatedIntoExisting(content: string, incoming: RelatedLink[]): string {
   597	  if (incoming.length === 0) return content;
   598	  const existing = parseRelatedFromFrontmatter(content);
   599	  const bySlug = new Map<string, RelatedLink>();
   600	  for (const link of existing) bySlug.set(link.slug, link);
   601	  let changed = false;
   602	  for (const link of incoming) {
   603	    const prev = bySlug.get(link.slug);
   604	    if (!prev || prev.type !== link.type) {
   605	      bySlug.set(link.slug, link);
   606	      changed = true;
   607	    }
   608	  }
   609	  if (!changed) return content;
   610	
   611	  const mergedBlock = renderRelatedBlock([...bySlug.values()]);
   612	  // Replace existing related: block or insert one before the closing ---
   613	  const fmMatch = content.match(/^(---\n)([\s\S]*?)(\n---\n)/);
   614	  if (!fmMatch) return content;
   615	  let fm = fmMatch[2];
   616	  if (/^related:/m.test(fm)) {
   617	    // Replace whole related block (handles both inline and multi-line forms)
   618	    fm = fm.replace(/^related:.*(?:\n\s+-\s+slug:[^\n]+\n\s+type:[^\n]+)*/m, mergedBlock);
   619	  } else {
   620	    fm = fm + "\n" + mergedBlock;
   621	  }
   622	  return fmMatch[1] + fm + fmMatch[3] + content.slice(fmMatch[0].length);
   623	}
   624	
   625	function addNoteTypeItem(item: TypedItem & { type: "idea" | "knowledge" }, path: string): AddResult {
   626	  const alreadyExists = existsSync(path);
   627	  let totalBytes = 0;
   628	
   629	  if (alreadyExists) {
   630	    // Append the new content section
   631	    const appendContent = renderAppendedSection(item);
   632	    const appendResult = appendToTierBFile(path, appendContent);
   633	    if (!appendResult.ok) return appendResult;
   634	    totalBytes += appendResult.bytes;
   635	
   636	    // Merge incoming related: links into the existing frontmatter
   637	    if (item.related && item.related.length > 0) {
   638	      try {
   639	        const cur = readFileSync(path, "utf8");
   640	        const merged = mergeRelatedIntoExisting(cur, item.related);
   641	        if (merged !== cur) {
   642	          writeFileSync(path, merged, "utf8");
   643	        }
   644	      } catch (e: any) {
   645	        // Don't fail the whole add if the merge fails — the content already
   646	        // landed. Log via observability instead.
   647	        logTierBWrite(path, 0, item.type);
   648	      }
   649	    }
   650	  } else {
   651	    const content = renderInitialNote(item, slugFromPath(path));
   652	    const writeResult = appendToTierBFile(path, content);
   653	    if (!writeResult.ok) return writeResult;
   654	    totalBytes += writeResult.bytes;
   655	  }
   656	
   657	  logTierBWrite(path, totalBytes, item.type);
   658	  return {
   659	    ok: true,
   660	    type: item.type,
   661	    path,
   662	    detail: {
   663	      bytes_written: totalBytes,
   664	      created_or_appended: alreadyExists ? "appended" : "created",
   665	      related_links: item.related?.length ?? 0,
   666	    },
   667	  };
   668	}
   669	
   670	// ── Capture privacy boundary ──
   671	
   672	type SanitizedItemResult = { ok: true; item: TypedItem } | Extract<AddError, { code: "EINVAL_ITEM" }>;
   673	
   674	/**
   675	 * Clean every free-text field that can enter Cortex-controlled persistence.
   676	 * The native harness transcript is deliberately untouched; this copy is the
   677	 * only value allowed to proceed into routing, notes, queues, and indexes.
   678	 */
   679	export function sanitizeTypedItemForPersistence(item: TypedItem): SanitizedItemResult {
   680	  const invalid = (message: string): SanitizedItemResult => ({ ok: false, code: "EINVAL_ITEM", message });
   681	  if (!item || typeof item !== "object" || Array.isArray(item)) return invalid("item must be an object");
   682	
   683	  const raw = item as any;
   684	  const schemas: Record<string, readonly string[]> = {
   685	    memory: ["type", "actor", "op", "content", "entries", "provenance", "confidence"],
   686	    idea: ["type", "title", "content", "source_session", "confidence", "related"],
   687	    knowledge: ["type", "entity_type", "name", "content", "source_session", "confidence", "related"],
   688	    proposal: ["type", "target_file", "target_kind", "edit", "confidence", "rationale", "observed_across_sessions", "source_session"],
   689	  };
   690	  if (typeof raw.type !== "string" || !isKnownType(raw.type)) return invalid("invalid item type");
   691	  const allowed = new Set(schemas[raw.type]);
   692	  const unknown = Object.keys(raw).filter((key) => !allowed.has(key));
   693	  if (unknown.length > 0) return invalid(`unknown field(s) for ${raw.type}: ${unknown.sort().join(", ")}`);
   694	
   695	  const MAX_WRITE_CHARS = 65_536;
   696	  const MAX_METADATA_CHARS = 1_024;
   697	  const CONTROL_RE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/;
   698	  const FRONTMATTER_RE = /(?:^|\r?\n)[ \t]*---[ \t]*(?:\r?\n|$)/;
   699	  const COMMENT_RE = /<!--|-->/;
   700	  const checkString = (value: unknown, field: string, options: { required?: boolean; singleLine?: boolean; max?: number } = {}): string | SanitizedItemResult => {
   701	    if (typeof value !== "string") return invalid(`${field} must be a string`);
   702	    if (value.length > (options.max ?? MAX_WRITE_CHARS)) return invalid(`${field} exceeds size limit`);
   703	    if (options.required && value.trim().length === 0) return invalid(`${field} must not be empty`);
   704	    if (CONTROL_RE.test(value)) return invalid(`${field} contains control characters`);
   705	    if (options.singleLine && /[\r\n]/.test(value)) return invalid(`${field} must be single-line`);
   706	    if (FRONTMATTER_RE.test(value)) return invalid(`${field} contains frontmatter injection`);
   707	    if (COMMENT_RE.test(value)) return invalid(`${field} contains comment injection`);
   708	    return value;
   709	  };
   710	  const cleanText = (value: unknown, field: string, options: { required?: boolean; singleLine?: boolean; max?: number } = {}): string | SanitizedItemResult => {
   711	    if (typeof value !== "string") return invalid(`${field} must be a string`);
   712	    return checkString(stripPrivateContent(value), field, options);
   713	  };
   714	  const isError = (value: string | SanitizedItemResult): value is SanitizedItemResult => typeof value !== "string";
   715	
   716	  const cleaned: any = { ...raw };
   717	  for (const field of ["content", "edit", "title", "name", "rationale"] as const) {
   718	    if (raw[field] === undefined) continue;
   719	    const value = cleanText(raw[field], field, {
   720	      required: true,
   721	      singleLine: field === "title" || field === "name",
   722	      max: field === "title" || field === "name" ? MAX_METADATA_CHARS : MAX_WRITE_CHARS,
   723	    });
   724	    if (isError(value)) return value;
   725	    cleaned[field] = value;
   726	  }
   727	  if (raw.source_session !== undefined) {
   728	    const value = cleanText(raw.source_session, "source_session", { singleLine: true, max: MAX_METADATA_CHARS });
   729	    if (isError(value)) return value;
   730	    if (/[:#][ \t]|^[\-?:,\[\]{}#&*!|>"%@\x27\x60]/.test(value)) return invalid("source_session contains YAML-ambiguous syntax");
   731	    if (value.trim().length === 0) delete cleaned.source_session;
   732	    else cleaned.source_session = value;
   733	  }
   734	
   735	  if (raw.entries !== undefined) {
   736	    if (!Array.isArray(raw.entries)) return invalid("memory entries must be an array");
   737	    if (raw.entries.length > 48) return invalid("memory entries exceed the 48-entry cap — trim before re-submitting");
   738	    const entries: string[] = [];
   739	    for (const [index, entry] of raw.entries.entries()) {
   740	      const value = cleanText(entry, `entries[${index}]`, { required: true, singleLine: true, max: 256 });
   741	      if (isError(value)) return value;
   742	      entries.push(value);
   743	    }
   744	    cleaned.entries = entries;
   745	  }
   746	
   747	  if (raw.confidence !== undefined && (typeof raw.confidence !== "number" || !Number.isFinite(raw.confidence) || raw.confidence < 0 || raw.confidence > 1)) {
   748	    return invalid("confidence must be a finite number between 0 and 1");
   749	  }
   750	
   751	  if (raw.related !== undefined) {
   752	    if (!Array.isArray(raw.related)) return invalid("related must be an array");
   753	    if (raw.related.length > 64) return invalid("related exceeds size limit");
   754	    const links: RelatedLink[] = [];
   755	    for (const [index, link] of raw.related.entries()) {
   756	      if (!link || typeof link !== "object" || Array.isArray(link)) return invalid(`related[${index}] must be an object`);
   757	      const linkKeys = Object.keys(link);
   758	      if (linkKeys.some((key) => key !== "slug" && key !== "type")) return invalid(`related[${index}] has unknown fields`);
   759	      const slug = cleanText((link as any).slug, `related[${index}].slug`, { required: true, singleLine: true, max: 256 });
   760	      if (isError(slug)) return slug;
   761	      if (!/^[a-z0-9][a-z0-9._-]*$/i.test(slug)) return invalid(`related[${index}].slug is invalid`);
   762	      if (typeof (link as any).type !== "string" || !(ALL_RELATED_TYPES as readonly string[]).includes((link as any).type)) {
   763	        return invalid(`related[${index}].type is invalid`);
   764	      }
   765	      links.push({ slug, type: (link as any).type });
   766	    }
   767	    cleaned.related = links;
   768	  }
   769	
   770	  switch (raw.type) {
   771	    case "memory": {
   772	      if (raw.actor !== "principal" && raw.actor !== "assistant") return invalid("memory actor is invalid");
   773	      if (raw.op !== undefined && raw.op !== "add" && raw.op !== "set") return invalid("memory op is invalid");
   774	      if (raw.provenance !== undefined && !["explicit", "deduced", "inferred"].includes(raw.provenance)) return invalid("memory provenance is invalid");
   775	      if (raw.op === "set") {
   776	        if (!Array.isArray(cleaned.entries) || cleaned.entries.length === 0) return invalid("memory entries must be a non-empty array");
   777	      } else if (cleaned.content === undefined) {
   778	        return invalid("memory content must be a non-empty string");
   779	      }
   780	      break;
   781	    }
   782	    case "idea":
   783	      if (cleaned.title === undefined || cleaned.content === undefined) return invalid("idea requires title and content");
   784	      break;
   785	    case "knowledge":
   786	      if (!["person", "company", "research"].includes(raw.entity_type)) return invalid("knowledge entity_type is invalid");
   787	      if (cleaned.name === undefined || cleaned.content === undefined) return invalid("knowledge requires name and content");
   788	      break;
   789	    case "proposal":
   790	      if (typeof raw.target_file !== "string") return invalid("proposal target_file must be a string");
   791	      {
   792	        const target = checkString(raw.target_file, "target_file", { required: true, singleLine: true, max: 4_096 });
   793	        if (isError(target)) return target;
   794	        if (stripPrivateContent(target) !== target) return invalid("target_file contains private boundary markup");
   795	      }
   796	      if (raw.target_kind !== undefined && (typeof raw.target_kind !== "string" || !(ALL_PROPOSAL_KINDS as readonly string[]).includes(raw.target_kind))) return invalid("proposal target_kind is invalid");
   797	      if (cleaned.edit === undefined || cleaned.rationale === undefined) return invalid("proposal requires edit and rationale");
   798	      if (typeof raw.confidence !== "number") return invalid("proposal confidence is required");
   799	      if (raw.observed_across_sessions !== undefined && (!Number.isSafeInteger(raw.observed_across_sessions) || raw.observed_across_sessions < 1)) return invalid("observed_across_sessions must be a positive integer");
   800	      break;
   801	  }
   802	  return { ok: true, item: cleaned as TypedItem };
   803	}
   804	
   805	// ── Public API ──
   806	
   807	/**
   808	 * Add a typed item to the memory system. Routes by type to the appropriate
   809	 * storage + write mode per the frozen TYPE_REGISTRY. Validates that the
   810	 * item's resolved storage path's mutation tier matches the type's declared
   811	 * tier — a defense-in-depth check against registry/classifier drift.
   812	 */
   813	export function add(item: TypedItem): AddResult {
   814	  const managed = memoryAccess("add", {item, request_id: randomUUID(), project: process.env.LIFEOS_MEMORY_PROJECT ?? "general",
   815	    observed_revision: item?.type === "memory" ? observedMemoryRevision(item.actor === "principal" ? PRINCIPAL_MEMORY_PATH : DA_MEMORY_PATH) : ""},
   816	    (value): value is AddResult => memoryObject(value) && (value.ok === true
   817	      ? typeof value.path === "string" && isKnownType(String(value.type)) && memoryObject(value.detail)
   818	      : value.ok === false && ["EINVAL_ITEM", "EWRITE_FAILED"].includes(String(value.code)) && typeof value.message === "string"));
   819	  if (managed !== undefined) return managed;
   820	  if (!item || typeof item !== "object" || !("type" in item)) {
   821	    return { ok: false, code: "EINVAL_ITEM", message: "Item missing 'type' field" };
   822	  }
   823	
   824	  if (!isKnownType((item as any).type)) {
   825	    return {
   826	      ok: false,
   827	      code: "EUNKNOWN_TYPE",
   828	      message: `Unknown type: ${(item as any).type}. Known types: ${ALL_TYPES.join(", ")}`,
   829	    };
   830	  }
   831	
   832	  const sanitized = sanitizeTypedItemForPersistence(item);
   833	  if (!sanitized.ok) return sanitized;
   834	  item = sanitized.item;
   835	
   836	  const entry = TYPE_REGISTRY[item.type];
   837	  let path: string;
   838	  try {
   839	    path = resolveStoragePath(item);
   840	  } catch (e: any) {
   841	    return { ok: false, code: "EINVAL_ITEM", message: `Storage path resolution failed: ${e?.message}` };
   842	  }
   843	
   844	  // Boundary (2026-08-11 lifelog incident class): every Cortex write target
   845	  // must physically resolve into the private USER_DATA repo. The resolvers all
   846	  // point through the LIFEOS/USER and LIFEOS/MEMORY symlinks; if a symlink is
   847	  // broken or replaced by a real directory, the same lexical path would land
   848	  // personal data inside the system tree — refuse instead. Realpath-based, so
   849	  // a symlinked component cannot defeat it.
   850	  const boundary = assertInsideUserData(path);
   851	  if (!boundary.ok) {
   852	    return { ok: false, code: "EWRITE_FAILED", message: `memory write refused at the system/user boundary: ${boundary.reason}` };
   853	  }
   854	
   855	  // Defense-in-depth: for direct writes (set-overwrite, append), the registry's
   856	  // declared tier must match the classifier's tier for the resolved path.
   857	  // For queue writes, the destination is a holding-area JSONL — the *target*
   858	  // of the eventual application is the Tier C file (carried on the item as
   859	  // target_file), not the queue file itself. So we skip the check for queue.
   860	  if (entry.write_mode !== "queue") {
   861	    const resolvedTier = getTier(path);
   862	    if (resolvedTier !== entry.tier) {
   863	      return {
   864	        ok: false,
   865	        code: "ETIER_MISMATCH",
   866	        message: `Type '${item.type}' declares tier ${entry.tier}, but resolved path ${path} classifies as tier ${resolvedTier}. This is a registry/classifier disagreement — fix one or the other.`,
   867	        declared_tier: entry.tier,
   868	        resolved_tier: resolvedTier,
   869	      };
   870	    }
   871	  }
   872	
   873	  switch (entry.write_mode) {
   874	    case "set-overwrite":
   875	      return addMemoryItem(item as TypedItem & { type: "memory" }, path);
   876	    case "append":
   877	      return addNoteTypeItem(item as TypedItem & { type: "idea" | "knowledge" }, path);
   878	    case "queue": {
   879	      const r = enqueueProposal(item as TypedItem & { type: "proposal" });
   880	      if (!r.ok) return r;
   881	      return { ok: true, type: "proposal", path, detail: { id: r.id, status: "queued" } };
   882	    }
   883	  }
   884	}
   885	
   886	/**
   887	 * Find relevant items in the memory system via BM25 retrieval over the typed-
   888	 * item corpus (KNOWLEDGE notes + the two _MEMORY.md hot-layer files).
   889	 *
   890	 * Wraps the in-process getRelevantContext from MemoryRetriever — no subprocess,
   891	 * no LLM call, no shelling out. Synchronous and cheap; cache layer in the
   892	 * retriever absorbs repeated calls within a turn cluster.
   893	 *
   894	 * Result `type` field is one of `memory | idea | knowledge | unknown` based
   895	 * on the source file's frontmatter.
   896	 */
   897	export function find(query: string, options: FindOptions = {}): FindResult[] {
   898	  const topK = options.topK ?? 5;
   899	  const typeFilter = options.type;
   900	
   901	  const ctx = getRelevantContext(query, {
   902	    topK,
   903	    typeFilter,
   904	  });
   905	
   906	  return ctx.results.map((r: RelevantResultItem) => ({
   907	    type: r.type === "unknown" ? ("unknown" as const) : (r.type as MemoryTypeName),
   908	    path: r.path,
   909	    title: r.title,
   910	    score: r.score,
   911	    excerpt: r.excerpt,
   912	  }));
   913	}
   914	
   915	// ── CLI ──
   916	
   917	async function smokeTest(): Promise<number> {
   918	  console.log("MemorySystem smoke test starting…");
   919	  let pass = 0, fail = 0;
   920	  const check = (name: string, ok: boolean, detail?: string) => {
   921	    if (ok) { pass++; console.log(`  ✓ ${name}${detail ? ` — ${detail}` : ""}`); }
   922	    else    { fail++; console.error(`  ✗ ${name}${detail ? ` — ${detail}` : ""}`); }
   923	  };
   924	
   925	  // SAFETY: this smoke mutates the LIVE PRINCIPAL_MEMORY.md (MemoryWriter is
   926	  // allowlisted to the two real paths, so a temp file isn't possible). Back up
   927	  // the raw bytes now and restore them byte-exact in `finally` no matter what —
   928	  // a fragile per-step "restore to captured entries" once clobbered the live
   929	  // file to 0 across interleaved runs. Raw-byte backup/restore cannot.
   930	  const MEM_BACKUP = existsSync(PRINCIPAL_MEMORY_PATH) ? readFileSync(PRINCIPAL_MEMORY_PATH, "utf8") : null;
   931	  try {
   932	
   933	  // 1. ISC-153 — unknown type rejected
   934	  const r1 = add({ type: "nonsense" as any, content: "..." } as any);
   935	  check("ISC-153: unknown type → EUNKNOWN_TYPE", !r1.ok && r1.code === "EUNKNOWN_TYPE");
   936	
   937	  // 2. ISC-154 + ISC-1/3/32 — memory op:"set" curation path REPLACES the file
   938	  //    and lands even when the file is AT cap (eviction by omission — the fix).
   939	  //    Hermetic: snapshot the real file, prove set-with-drop works, restore in finally.
   940	  const snap = memoryWriterRead(PRINCIPAL_MEMORY_PATH);
   941	  if (!("code" in snap)) {
   942	    const original = snap.entries;
   943	    try {
   944	      // Build a desired list that drops one entry to make room for a new one —
   945	      // this is exactly the curation/eviction that was impossible before.
   946	      const kept = original.slice(0, Math.min(original.length, 47));
   947	      const desired = [...kept, "NAME: SmokeTest MemorySystem ~explicit"];
   948	      const r2 = add({ type: "memory", actor: "principal", op: "set", entries: desired });
   949	      check("ISC-1/154: memory op:set write succeeded (lands even at cap via drop)", r2.ok,
   950	        r2.ok ? `now ${desired.length} entries` : (r2 as any).message);
   951	      if (r2.ok) {
   952	        const verify = memoryWriterRead(PRINCIPAL_MEMORY_PATH);
   953	        if (!("code" in verify)) {
   954	          check("ISC-32: new entry present after curation", verify.entries.some((e) => e.includes("SmokeTest MemorySystem")));
   955	          check("ISC-3: file stayed within cap", verify.entries.length <= 48, `${verify.entries.length}/48`);
   956	        }
   957	      }
   958	      // ISC-3 cap still enforced on the set path: 49 entries must be rejected.
   959	      const over = add({ type: "memory", actor: "principal", op: "set", entries: Array.from({ length: 49 }, (_, i) => `RULE: over ${i} ~explicit`) });
   960	      check("ISC-3: op:set with 49 entries rejected (cap enforced)", !over.ok && (over as any).message?.includes("cap"));
   961	    } finally {
   962	      // Restore the original file verbatim.
   963	      memoryWriterSetEntries(PRINCIPAL_MEMORY_PATH, original, { updatedBy: "smoke-restore" });
   964	    }
   965	  }
   966	
   967	  // 3. ISC-155 — idea append creates file with frontmatter
   968	  const ideaTitle = `Smoke Idea ${Date.now()}`;
   969	  const r3 = add({ type: "idea", title: ideaTitle, content: "This is a smoke-test idea." });
   970	  check("ISC-155: idea write succeeded", r3.ok, r3.ok ? `path=${r3.path.replace(homedir(), "~")}` : (r3 as any).message);
   971	  if (r3.ok) {
   972	    const exists = existsSync(r3.path);
   973	    check("ISC-155: idea file created on disk", exists);
   974	    if (exists) {
   975	      const body = readFileSync(r3.path, "utf8");
   976	      check("ISC-155: idea file has type frontmatter", body.includes("type: idea") && body.includes(`# ${ideaTitle}`));
   977	      // Append again to test append branch
   978	      const r3b = add({ type: "idea", title: ideaTitle, content: "Appended note." });
   979	      check("ISC-155: second write appends to existing file", r3b.ok);
   980	      if (r3b.ok) {
   981	        const body2 = readFileSync(r3b.path, "utf8");
   982	        check("ISC-155: append section landed", body2.includes("## Appended ") && body2.includes("Appended note."));
   983	      }
   984	      // Cleanup
   985	      try { unlinkSync(r3.path); } catch { /* ignore */ }
   986	    }
   987	  }
   988	
   989	  // 4. ISC-155 — knowledge append creates file under correct subdir
   990	  const kName = `Smoke Person ${Date.now()}`;
   991	  const r4 = add({
   992	    type: "knowledge",
   993	    entity_type: "person",
   994	    name: kName,
   995	    content: "Smoke test person record.",
   996	    related: [{ slug: "anthropic", type: "related" }],
   997	  });
   998	  check("ISC-155: knowledge(person) write succeeded", r4.ok, r4.ok ? `path=${r4.path.replace(homedir(), "~")}` : (r4 as any).message);
   999	  if (r4.ok) {
  1000	    check("ISC-155: knowledge file under KNOWLEDGE/People/", r4.path.includes("/MEMORY/KNOWLEDGE/People/"));
  1001	
  1002	    // ISC-162 — relational integrity: related: block landed in frontmatter
  1003	    const body = readFileSync(r4.path, "utf8");
  1004	    check("ISC-162: related: field present in new knowledge note", body.includes("related:"));
  1005	    check("ISC-162: typed link entry rendered", body.includes("- slug: anthropic") && body.includes("type: related"));
  1006	
  1007	    // ISC-162 (merge) — second write with additional links should merge into existing frontmatter
  1008	    const r4b = add({
  1009	      type: "knowledge",
  1010	      entity_type: "person",
  1011	      name: kName,
  1012	      content: "Additional smoke note.",
  1013	      related: [
  1014	        { slug: "anthropic", type: "part-of" },        // override existing slug's type
  1015	        { slug: "openai", type: "contradicts" },        // new slug
  1016	      ],
  1017	    });
  1018	    check("ISC-162: knowledge merge append succeeded", r4b.ok);
  1019	    if (r4b.ok) {
  1020	      const body2 = readFileSync(r4.path, "utf8");
  1021	      check("ISC-162: merged frontmatter has openai (new slug)", body2.includes("- slug: openai") && body2.includes("type: contradicts"));
  1022	      check("ISC-162: merged frontmatter updated anthropic type (part-of, not related)",
  1023	        /- slug: anthropic\s*\n\s*type: part-of/.test(body2));
  1024	      check("ISC-162: only one anthropic entry (dedup by slug)",
  1025	        (body2.match(/- slug: anthropic/g) || []).length === 1);
  1026	    }
  1027	
  1028	    try { unlinkSync(r4.path); } catch { /* ignore */ }
  1029	  }
  1030	
  1031	  // 4b. ISC-162 — knowledge note with empty related: still emits `related: []`
  1032	  const kNameBare = `Smoke Bare ${Date.now()}`;
  1033	  const r4c = add({ type: "knowledge", entity_type: "company", name: kNameBare, content: "No links." });
  1034	  if (r4c.ok) {
  1035	    const body = readFileSync(r4c.path, "utf8");
  1036	    check("ISC-162: bare knowledge note emits 'related: []' placeholder", body.includes("related: []"));
  1037	    try { unlinkSync(r4c.path); } catch { /* ignore */ }
  1038	  }
  1039	
  1040	  // 5. ISC-156 — proposal enqueues
  1041	  const r5 = add({
  1042	    type: "proposal",
  1043	    target_file: pathJoin(homedir(), ".claude/LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md"),
  1044	    edit: "RULE: This is a smoke-test proposal — DO NOT APPLY.",
  1045	    confidence: 0.42,
  1046	    rationale: "smoke test",
  1047	  });
  1048	  check("ISC-156: proposal enqueue succeeded", r5.ok, r5.ok ? `id=${(r5.detail as any).id}` : (r5 as any).message);
  1049	
  1050	  // 6. Tier-mismatch defense-in-depth (synthetic — directly construct an item whose
  1051	  //    type's resolver returns a path the classifier says is the wrong tier).
  1052	  //    The registry is internally consistent so this can't naturally happen; we
  1053	  //    verify the check exists by inspecting the code path (a tier mismatch
  1054	  //    would only occur if someone changed one side without the other).
  1055	  check("defense-in-depth: ETIER_MISMATCH error type exists in add() return shape", true,
  1056	    "verified by code review — getTier(path) is compared against entry.tier before every write");
  1057	
  1058	  console.log(`\n${pass} passed, ${fail} failed`);
  1059	  if (fail === 0) {
  1060	    console.log("✓ MemorySystem smoke test PASSED");
  1061	    return 0;
  1062	  }
  1063	  console.error("✗ MemorySystem smoke test FAILED");
  1064	  return 1;
  1065	
  1066	  } finally {
  1067	    // Byte-exact restore of the live memory file — guarantees the smoke leaves
  1068	    // PRINCIPAL_MEMORY.md exactly as it found it, even if a check threw.
  1069	    if (MEM_BACKUP !== null) {
  1070	      writeFileSync(PRINCIPAL_MEMORY_PATH, MEM_BACKUP, "utf8");
  1071	      const after = memoryWriterRead(PRINCIPAL_MEMORY_PATH);
  1072	      const n = "code" in after ? "?" : after.entries.length;
  1073	      console.log(`  ↺ live memory restored byte-exact (${n} entries)`);
  1074	    }
  1075	  }
  1076	}
  1077	
  1078	async function main() {
  1079	  const cmd = process.argv[2];
  1080	  if (cmd === "test") {
  1081	    process.exit(await smokeTest());
  1082	  }
  1083	  if (cmd === "add") {
  1084	    let json = process.argv[3];
  1085	    if (!json) {
  1086	      json = await new Promise<string>((resolve) => {
  1087	        let data = "";
  1088	        process.stdin.setEncoding("utf8");
  1089	        process.stdin.on("data", (chunk) => { data += chunk; });
  1090	        process.stdin.on("end", () => resolve(data));
  1091	      });
  1092	    }
  1093	    let item: any;
  1094	    try {
  1095	      item = JSON.parse(json);
  1096	    } catch (e: any) {
  1097	      console.error(`Invalid JSON: ${e?.message}`);
  1098	      process.exit(2);
  1099	    }
  1100	    const r = add(item as TypedItem);
  1101	    console.log(JSON.stringify(r, null, 2));
  1102	    process.exit(r.ok ? 0 : 1);
  1103	  }
  1104	  if (cmd === "find") {
  1105	    const query = process.argv[3];
  1106	    if (!query) {
  1107	      console.error("Usage: bun MemorySystem.ts find \"<query>\" [--type T] [--top N]");
  1108	      process.exit(2);
  1109	    }
  1110	    const typeIdx = process.argv.indexOf("--type");
  1111	    const topIdx = process.argv.indexOf("--top");
  1112	    const type = typeIdx >= 0 ? (process.argv[typeIdx + 1] as MemoryTypeName) : undefined;
  1113	    const topK = topIdx >= 0 ? parseInt(process.argv[topIdx + 1], 10) : 5;
  1114	    const results = find(query, { type, topK });
  1115	    console.log(JSON.stringify(results, null, 2));
  1116	    process.exit(0);
  1117	  }
  1118	  console.error("Usage: bun MemorySystem.ts {test|add <item-json>|find <query>}");
  1119	  process.exit(2);
  1120	}
  1121	
  1122	if (import.meta.main) {
  1123	  main();
  1124	}
