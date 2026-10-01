     1	// ABOUTME: Executes native LifeOS memory functions for an isolated governed operation.
     2	// ABOUTME: Returns native validation and write results without starting a model or runtime.
     3	
     4	import { resolve } from "node:path";
     5	import { pathToFileURL } from "node:url";
     6	import { observePublication } from "./memory_publication";
     7	
     8	function object(value: unknown): value is Record<string, unknown> {
     9	  return value !== null && typeof value === "object" && !Array.isArray(value);
    10	}
    11	
    12	async function main(): Promise<void> {
    13	  const root = process.argv[2];
    14	  if (!root) throw new Error("An installed LifeOS root is required");
    15	  const input: unknown = JSON.parse(await Bun.stdin.text());
    16	  if (!object(input)) throw new Error("Native memory input must be an object");
    17	  const system: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemorySystem.ts")).href);
    18	  const writer: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryWriter.ts")).href);
    19	  if (!object(system) || !object(writer)) throw new Error("Native memory exports are unavailable");
    20	  const journal = process.env.LIFEOS_MEMORY_PUBLICATION_JOURNAL;
    21	  if (input.action === "add" && journal && object(input.item) && input.item.type === "proposal") {
    22	    const upgrades: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/Upgrades.ts")).href);
    23	    if (!object(upgrades) || typeof upgrades.observeUpgradePublication !== "function") {
    24	      throw new Error("The native proposal publication capability is unavailable");
    25	    }
    26	    upgrades.observeUpgradePublication((path: string) => observePublication(root, journal, path));
    27	  }
    28	  let result: unknown;
    29	  if (input.action === "pulse_snapshot") {
    30	    const paths = new Map([["snapshot", "/api/memory"], ["state", "/api/memory/state"],
    31	                           ["health", "/api/memory/health"], ["runs", "/api/memory/runs"]]);
    32	    const route = typeof input.view === "string" ? paths.get(input.view) : undefined;
    33	    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/modules/memory.ts")).href);
    34	    if (!route || !object(module) || typeof module.handleRequest !== "function") {
    35	      throw new Error("The native PULSE snapshot is unavailable");
    36	    }
    37	    const response: unknown = await module.handleRequest(new Request("http://localhost" + route), route);
    38	    if (!(response instanceof Response) || response.status !== 200) throw new Error("The native PULSE snapshot failed");
    39	    result = {snapshot: await response.json()};
    40	  } else if (input.action === "discover") {
    41	    const retriever: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryRetriever.ts")).href);
    42	    if (!object(retriever) || typeof retriever.discoverAllItems !== "function") throw new Error("Native memory discovery is unavailable");
    43	    result = {notes: retriever.discoverAllItems(null)};
    44	  } else if (input.action === "validate_batch") {
    45	    if (!Array.isArray(input.items) || typeof system.sanitizeTypedItemForPersistence !== "function") throw new Error("Invalid native validation batch");
    46	    result = {results: input.items.map((item: unknown) => system.sanitizeTypedItemForPersistence(item))};
    47	  } else if (input.action === "rank") {
    48	    const retriever: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryRetriever.ts")).href);
    49	    if (!object(retriever) || retriever.SUPPLIED_CORPUS_API_VERSION !== 1 || typeof retriever.getRelevantContext !== "function") {
    50	      throw new Error("The governed native retrieval capability is unavailable");
    51	    }
    52	    if (typeof input.query !== "string" || !Array.isArray(input.corpus)) throw new Error("Invalid retrieval input");
    53	    const options = object(input.options) ? input.options : {topK: input.limit, excerptChars: 65536};
    54	    result = retriever.getRelevantContext(input.query, {...options, corpus: input.corpus});
    55	  } else if (input.action === "proposal_capabilities") {
    56	    const proposals: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/lib/memory-proposals.ts")).href);
    57	    result = { available: object(proposals) && ["acceptProposal", "rejectProposal", "editProposal", "markProposalAppliedElsewhere", "autoApplyProposal"]
    58	      .every((name) => typeof proposals[name] === "function") };
    59	  } else if (input.action === "proposal_decision") {
    60	    const proposals: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/lib/memory-proposals.ts")).href);
    61	    if (!object(proposals) || typeof input.identifier !== "string") throw new Error("Native proposal decisions are unavailable");
    62	    const decide = input.decision === "accept" ? proposals.acceptProposal : input.decision === "reject" ? proposals.rejectProposal
    63	      : input.decision === "edit" ? proposals.editProposal : input.decision === "applied_elsewhere" ? proposals.markProposalAppliedElsewhere
    64	      : input.decision === "auto_apply" ? proposals.autoApplyProposal : undefined;
    65	    if (typeof decide !== "function") throw new Error("Invalid native proposal decision");
    66	    result = input.decision === "edit" ? decide(input.identifier, input.content)
    67	      : input.decision === "applied_elsewhere" ? decide(input.identifier, input.note)
    68	      : input.decision === "auto_apply" ? decide(input.identifier, input.confidence_threshold) : decide(input.identifier);
    69	  } else if (input.action === "route") {
    70	    const types: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryTypes.ts")).href);
    71	    if (!object(types) || typeof types.resolveStoragePath !== "function") throw new Error("Native memory routing is unavailable");
    72	    result = { path: types.resolveStoragePath(input.item) };
    73	  } else if (input.action === "add" || input.action === "validate") {
    74	    if (typeof system.sanitizeTypedItemForPersistence !== "function" || typeof system.add !== "function") {
    75	      throw new Error("Native memory validation or add operation is unavailable");
    76	    }
    77	    const checked: unknown = system.sanitizeTypedItemForPersistence(input.item);
    78	    if (!object(checked) || checked.ok !== true || input.action === "validate") result = checked;
    79	    else result = system.add(checked.item);
    80	  } else if (input.action === "read_hot") {
    81	    if (typeof writer.read !== "function" || typeof input.path !== "string") throw new Error("Invalid hot-memory read");
    82	    result = writer.read(input.path);
    83	  } else if (input.action === "set_hot") {
    84	    if (typeof writer.setEntries !== "function" || typeof input.path !== "string" || !Array.isArray(input.entries)
    85	        || input.entries.some((entry: unknown) => typeof entry !== "string")) throw new Error("Invalid hot-memory curation");
    86	    result = writer.setEntries(input.path, input.entries, { updatedBy: input.writer, allowDrastic: input.allowDrastic === true });
    87	  } else {
    88	    throw new Error("Unknown native memory operation");
    89	  }
    90	  process.stdout.write(JSON.stringify(result) + "\n");
    91	}
    92	
    93	main().catch((error: unknown) => {
    94	  process.stderr.write(String(error) + "\n");
    95	  process.exitCode = 1;
    96	});
