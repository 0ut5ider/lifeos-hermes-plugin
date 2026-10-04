// ABOUTME: Executes native LifeOS memory functions for an isolated governed operation.
// ABOUTME: Returns native validation and write results without starting a model or runtime.

import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { observePublication } from "./memory_publication";

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

async function main(): Promise<void> {
  const root = process.argv[2];
  if (!root) throw new Error("An installed LifeOS root is required");
  const input: unknown = JSON.parse(await Bun.stdin.text());
  if (!object(input)) throw new Error("Native memory input must be an object");
  const system: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemorySystem.ts")).href);
  const writer: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryWriter.ts")).href);
  if (!object(system) || !object(writer)) throw new Error("Native memory exports are unavailable");
  const journal = process.env.LIFEOS_MEMORY_PUBLICATION_JOURNAL;
  if (input.action === "add" && journal && object(input.item) && input.item.type === "proposal") {
    const upgrades: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/Upgrades.ts")).href);
    if (!object(upgrades) || typeof upgrades.observeUpgradePublication !== "function") {
      throw new Error("The native proposal publication capability is unavailable");
    }
    upgrades.observeUpgradePublication((path: string) => observePublication(root, journal, path));
  }
  let result: unknown;
  if (input.action === "interview_completion") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/InterviewDue.ts")).href);
    if (!object(module) || typeof module.renderInterviewCompletion !== "function" || typeof input.now !== "string") {
      throw new Error("Native interview completion needs its declared date");
    }
    result = {content: module.renderInterviewCompletion(new Date(input.now))};
  } else if (input.action === "interview_due") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/InterviewDue.ts")).href);
    const freshness: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/TelosFreshness.ts")).href);
    const evidence: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/StateEvidence.ts")).href);
    if (!object(module) || typeof module.buildInputs !== "function" || typeof module.computeVerdict !== "function"
        || !object(freshness) || typeof freshness.readContextFreshness !== "function" || typeof freshness.readStateFreshness !== "function"
        || !object(evidence) || typeof evidence.gatherEvidence !== "function" || typeof input.now !== "string"
        || !Array.isArray(input.context_sources) || !Array.isArray(input.state_sources) || !Array.isArray(input.interview_sources)
        || !(input.evidence_sources === null || object(input.evidence_sources) && Array.isArray(input.evidence_sources.sources)
          && (input.evidence_sources.gitCommits === null || Array.isArray(input.evidence_sources.gitCommits)
            && input.evidence_sources.gitCommits.every(date => typeof date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(date))))) {
      throw new Error("Native interview inputs require declared current sources and a date");
    }
    function declared(values: unknown[]): Record<string, {path: string; content: string; lastModified: string}> {
      const sources: Record<string, {path: string; content: string; lastModified: string}> = {};
      for (const source of values) {
        if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string"
            || typeof source.lastModified !== "string" || Object.hasOwn(sources, source.path)) {
          throw new Error("Native interview inputs require distinct declared source bytes and dates");
        }
        sources[source.path] = {path: source.path, content: source.content, lastModified: source.lastModified};
      }
      return sources;
    }
    const now = new Date(input.now);
    if (Number.isNaN(now.getTime())) throw new Error("Native interview inputs require a valid calculation date");
    const context = freshness.readContextFreshness(declared(input.context_sources));
    const state = freshness.readStateFreshness(declared(input.state_sources));
    let observed = null;
    if (object(input.evidence_sources)) {
      const values: Record<string, string> = {};
      for (const source of Object.values(declared(input.evidence_sources.sources))) values[source.path] = source.content;
      observed = evidence.gatherEvidence(now, {sources: values, gitCommits: input.evidence_sources.gitCommits});
    }
    const lastSources = Object.values(declared(input.interview_sources));
    const last = lastSources.length ? JSON.parse(lastSources[0].content) : null;
    const inputs = module.buildInputs(observed, now, {context, state, last});
    const verdict = module.computeVerdict(inputs, now);
    result = {inputs, verdict, verdict_content: JSON.stringify(verdict, null, 2) + "\n"};
  } else if (input.action === "state_evidence") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/StateEvidence.ts")).href);
    if (!object(module) || typeof module.gatherEvidence !== "function" || typeof module.gatherDomain !== "function"
        || !Array.isArray(input.sources) || typeof input.now !== "string"
        || !(input.domain === null || typeof input.domain === "string" && ["health", "activity", "work", "money"].includes(input.domain))
        || !(input.gitCommits === null || Array.isArray(input.gitCommits)
          && input.gitCommits.every(date => typeof date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(date)))) {
      throw new Error("Native state evidence needs declared source bytes, Git dates, and a domain");
    }
    const sources: Record<string, string> = {};
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string"
          || Object.hasOwn(sources, source.path)) {
        throw new Error("Native state evidence needs distinct declared source text");
      }
      sources[source.path] = source.content;
    }
    const now = new Date(input.now);
    if (Number.isNaN(now.getTime())) throw new Error("Native state evidence requires a valid calculation date");
    const declared = {sources, gitCommits: input.gitCommits};
    const value = input.domain === null ? module.gatherEvidence(now, declared) : module.gatherDomain(input.domain, now, declared);
    result = {value, content: JSON.stringify(value, null, 2) + "\n"};
  } else if (input.action === "freshness_write") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/TelosFreshness.ts")).href);
    if (!object(module) || typeof module.renderFreshnessWrite !== "function" || typeof input.kind !== "string"
        || typeof input.path !== "string" || typeof input.by !== "string"
        || !(input.slug === null || typeof input.slug === "string")
        || !(input.content === null || typeof input.content === "string")) {
      throw new Error("Native timestamp rendering needs a declared source and mutation");
    }
    result = module.renderFreshnessWrite(input.kind, input.content, input.by, input.slug, input.path);
  } else if (["read_freshness", "freshness_view", "freshness_cache", "freshness_migration"].includes(input.action as string)) {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/TelosFreshness.ts")).href);
    if (!object(module) || !Array.isArray(input.sources)) {
      throw new Error("Native freshness reads need declared sources and a view");
    }
    const sources: Record<string, {path: string; content: string; lastModified: string}> = {};
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string"
          || typeof source.lastModified !== "string" || Object.hasOwn(sources, source.path)) {
        throw new Error("Native freshness reads need distinct declared source bytes and times");
      }
      sources[source.path] = {path: source.path, content: source.content, lastModified: source.lastModified};
    }
    if (input.action === "freshness_migration") {
      const migration: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MigrateContextFreshness.ts")).href);
      if (!object(migration) || typeof migration.renderFreshnessMigration !== "function"
          || typeof input.dry_run !== "boolean" || typeof input.state !== "boolean") {
        throw new Error("Native freshness migration needs declared sources and boolean options");
      }
      result = migration.renderFreshnessMigration(sources, input.dry_run, input.state);
    } else if (input.action === "freshness_cache") {
      const cache: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/FreshnessCache.ts")).href);
      if (!object(cache) || typeof cache.buildFreshnessPayload !== "function") {
        throw new Error("Native freshness cache rendering needs a declared source builder");
      }
      const payload = cache.buildFreshnessPayload(sources);
      const content = JSON.stringify(payload);
      result = {content, bytes: content.length, generated_at: payload.generated_at};
    } else if (input.action === "freshness_view") {
      const view: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/modules/telos.ts")).href);
      if (!object(view) || typeof view.renderFreshnessView !== "function" || typeof input.target !== "string") {
        throw new Error("Native freshness HTTP rendering needs declared sources and a route");
      }
      const response: unknown = await view.renderFreshnessView(sources, input.target);
      if (!(response instanceof Response)) throw new Error("Native freshness rendering did not return a response");
      result = {status: response.status, body: await response.json()};
    } else {
      if (typeof input.view !== "string") throw new Error("Native freshness reads need a view");
      const functions: Record<string, string> = {telos: "readTelosFreshness", context: "readContextFreshness",
        state: "readStateFreshness", registry: "stateFreshnessRegistry", frontmatter: "readFileFrontmatter",
        legacy_path: "legacyTelosFilePath", legacy_date: "legacyTelosFileDate"};
      const name = functions[input.view];
      if (!name || typeof module[name] !== "function") throw new Error("This native freshness view is unavailable");
      const args = ["telos", "frontmatter"].includes(input.view) ? [input.path, sources]
        : ["legacy_path", "legacy_date"].includes(input.view) ? [input.slug, input.path, sources] : [sources];
      result = {value: module[name](...args)};
    }
  } else if (input.action === "telos_summary") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/GenerateTelosSummary.ts")).href);
    if (!object(module) || typeof module.renderTelosSummary !== "function" || !object(input.sources)
        || Object.values(input.sources).some(value => typeof value !== "string")) {
      throw new Error("Native TELOS rendering needs declared source text");
    }
    result = module.renderTelosSummary(input.sources);
  } else if (input.action === "lifeos_state") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/UpdateLifeosState.ts")).href);
    if (!object(module) || typeof module.renderLifeosState !== "function" || !object(input.sources)
        || Object.values(input.sources).some(value => typeof value !== "string")
        || typeof input.json_output !== "boolean") {
      throw new Error("Native state rendering needs declared sources and an output format");
    }
    result = module.renderLifeosState(input.sources, input.json_output);
  } else if (input.action === "memory_graph_view") {
    const graph: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryGraph.ts")).href);
    const view: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/Observability/observability.ts")).href);
    if (!object(graph) || typeof graph.renderMemoryGraphData !== "function"
        || !object(view) || typeof view.renderMemoryGraphView !== "function" || !Array.isArray(input.sources)) {
      throw new Error("Native graph views need declared sources and rendering capabilities");
    }
    const sources: Array<{path: string; content: string}> = [];
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string") {
        throw new Error("Native graph views need declared source text");
      }
      sources.push({path: source.path, content: source.content});
    }
    const content: unknown = graph.renderMemoryGraphData(sources, "all");
    if (typeof content !== "string") throw new Error("Native graph rendering returns an invalid graph");
    const response: unknown = view.renderMemoryGraphView(content);
    if (!(response instanceof Response)) throw new Error("Native graph rendering did not return a response");
    result = {status: response.status, body: await response.json()};
  } else if (input.action === "memory_graph") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryGraph.ts")).href);
    if (!object(module) || typeof module.renderMemoryGraph !== "function" || !Array.isArray(input.sources)
        || typeof input.command !== "string" || !["declared", "all"].includes(String(input.layer))
        || !(input.target === null || typeof input.target === "string")) {
      throw new Error("Native graph rendering needs its declared sources and command");
    }
    const sources: Array<{path: string; content: string}> = [];
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string") {
        throw new Error("Native graph rendering needs declared source text");
      }
      sources.push({path: source.path, content: source.content});
    }
    result = module.renderMemoryGraph(sources, input.command, input.layer, input.target);
  } else if (input.action === "prompt_bundle") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/HERMES/RenderSoul.ts")).href);
    if (!object(module) || typeof module.renderSoulFromSources !== "function") {
      throw new Error("Native prompt rendering is unavailable");
    }
    result = {bundle: module.renderSoulFromSources(input.sources, input.skills, input.options)};
  } else if (input.action === "canonical_records") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/Cortex.ts")).href);
    if (!object(module) || typeof module.parseCanonicalMarkdown !== "function"
        || typeof module.canonicalMetadata !== "function" || typeof input.root !== "string"
        || !Array.isArray(input.sources)) throw new Error("Canonical source parsing is unavailable");
    const records: unknown[] = [], metadata: unknown[] = [];
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string") {
        throw new Error("Canonical parsing requires declared source text");
      }
      records.push(module.parseCanonicalMarkdown(source.content, source.path, input.root));
      metadata.push(module.canonicalMetadata(source.content,source.path,input.root));
    }
    result = {records, metadata};
  } else if (input.action === "knowledge_view") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/Observability/observability.ts")).href);
    if (!object(module) || typeof module.renderKnowledgeView !== "function" || typeof input.target !== "string"
        || !Array.isArray(input.sources)) throw new Error("Native Knowledge rendering needs declared source text");
    const sources: Array<{path: string; content: string}> = [];
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string") {
        throw new Error("Native Knowledge sources are unavailable");
      }
      sources.push({path: source.path, content: source.content});
    }
    const response: unknown = module.renderKnowledgeView(sources, input.target);
    if (!(response instanceof Response)) throw new Error("Native Knowledge rendering did not return a response");
    result = {status: response.status, body: await response.json()};
  } else if (input.action === "wiki_view") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/modules/wiki.ts")).href);
    if (!object(module) || typeof module.renderWikiView !== "function" || typeof input.target !== "string"
        || !Array.isArray(input.sources)) throw new Error("Native wiki rendering needs declared source text");
    const sources: Array<{path: string; content: string; lastModified: string; category: string; slug: string; group?: string}> = [];
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string"
          || typeof source.lastModified !== "string" || typeof source.category !== "string"
          || typeof source.slug !== "string" || (source.group !== undefined && typeof source.group !== "string")) {
        throw new Error("Native wiki sources are unavailable");
      }
      sources.push({path: source.path, content: source.content, lastModified: source.lastModified,
        category: source.category, slug: source.slug, ...(typeof source.group === "string" ? {group: source.group} : {})});
    }
    const request = new Request("http://127.0.0.1" + input.target);
    const response: unknown = module.renderWikiView(sources, request, new URL(request.url).pathname);
    if (!(response instanceof Response)) throw new Error("Native wiki response is unavailable");
    result = {status: response.status, body: await response.json()};
  } else if (input.action === "knowledge_indexes") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/KnowledgeHarvester.ts")).href);
    if (!object(module) || typeof module.renderKnowledgeIndexes !== "function" || !Array.isArray(input.sources)
        || !object(input.state) || typeof input.state.lastHarvest !== "string"
        || typeof input.state.totalHarvested !== "number" || !Number.isSafeInteger(input.state.totalHarvested)
        || !Array.isArray(input.state.harvestedPaths) || !input.state.harvestedPaths.every(value => typeof value === "string")) {
      throw new Error("Native Knowledge rendering needs its declared corpus and state");
    }
    const sources: Array<{path: string; content: string}> = [];
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string") {
        throw new Error("Native Knowledge rendering needs declared source text");
      }
      sources.push({path: source.path, content: source.content});
    }
    result = {writes: module.renderKnowledgeIndexes(sources,input.state)};
  } else if (input.action === "pulse_snapshot") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/modules/memory.ts")).href);
    if (typeof input.view !== "string" || !object(module) || typeof module.readMemoryView !== "function") {
      throw new Error("The native PULSE snapshot is unavailable");
    }
    result = {snapshot: module.readMemoryView(input.view)};
  } else if (input.action === "discover") {
    const retriever: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryRetriever.ts")).href);
    if (!object(retriever) || typeof retriever.discoverAllItems !== "function") throw new Error("Native memory discovery is unavailable");
    result = {notes: retriever.discoverAllItems(null)};
  } else if (input.action === "validate_batch") {
    if (!Array.isArray(input.items) || typeof system.sanitizeTypedItemForPersistence !== "function") throw new Error("Invalid native validation batch");
    result = {results: input.items.map((item: unknown) => system.sanitizeTypedItemForPersistence(item))};
  } else if (input.action === "validate_source_batch") {
    const capture: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/CaptureEnvelope.ts")).href);
    if (!object(capture) || typeof capture.stripPrivateContent !== "function" || !Array.isArray(input.contents)) {
      throw new Error("Native retained source validation is unavailable");
    }
    const accepted: boolean[] = [];
    for (const content of input.contents) {
      if (typeof content !== "string") throw new Error("Native retained sources require declared text");
      // The canonical text boundary permits Markdown metadata and comments, unlike a new fact write.
      accepted.push(!/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/u.test(content)
        && !/[\uD800-\uDFFF]/u.test(content) && capture.stripPrivateContent(content) === content);
    }
    result = {accepted};
  } else if (input.action === "rank") {
    const retriever: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryRetriever.ts")).href);
    if (!object(retriever) || retriever.SUPPLIED_CORPUS_API_VERSION !== 1 || typeof retriever.getRelevantContext !== "function") {
      throw new Error("The governed native retrieval capability is unavailable");
    }
    if (typeof input.query !== "string" || !Array.isArray(input.corpus)) throw new Error("Invalid retrieval input");
    const options = object(input.options) ? input.options : {topK: input.limit, excerptChars: 65536};
    result = retriever.getRelevantContext(input.query, {...options, corpus: input.corpus});
  } else if (input.action === "proposal_capabilities") {
    const proposals: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/lib/memory-proposals.ts")).href);
    result = { available: object(proposals) && ["acceptProposal", "rejectProposal", "editProposal", "markProposalAppliedElsewhere", "autoApplyProposal"]
      .every((name) => typeof proposals[name] === "function") };
  } else if (input.action === "proposal_decision") {
    const proposals: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/lib/memory-proposals.ts")).href);
    if (!object(proposals) || typeof input.identifier !== "string") throw new Error("Native proposal decisions are unavailable");
    const decide = input.decision === "accept" ? proposals.acceptProposal : input.decision === "reject" ? proposals.rejectProposal
      : input.decision === "edit" ? proposals.editProposal : input.decision === "applied_elsewhere" ? proposals.markProposalAppliedElsewhere
      : input.decision === "auto_apply" ? proposals.autoApplyProposal : undefined;
    if (typeof decide !== "function") throw new Error("Invalid native proposal decision");
    result = input.decision === "edit" ? decide(input.identifier, input.content)
      : input.decision === "applied_elsewhere" ? decide(input.identifier, input.note)
      : input.decision === "auto_apply" ? decide(input.identifier, input.confidence_threshold) : decide(input.identifier);
  } else if (input.action === "route") {
    const types: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/MemoryTypes.ts")).href);
    if (!object(types) || typeof types.resolveStoragePath !== "function") throw new Error("Native memory routing is unavailable");
    result = { path: types.resolveStoragePath(input.item) };
  } else if (input.action === "add" || input.action === "validate") {
    if (typeof system.sanitizeTypedItemForPersistence !== "function" || typeof system.add !== "function") {
      throw new Error("Native memory validation or add operation is unavailable");
    }
    const checked: unknown = system.sanitizeTypedItemForPersistence(input.item);
    if (!object(checked) || checked.ok !== true || input.action === "validate") result = checked;
    else result = system.add(checked.item);
  } else if (input.action === "parse_hot") {
    if (typeof input.content !== "string" || typeof writer.parseMemoryContent !== "function") {
      throw new Error("Native recovery requires declared hot content");
    }
    result = writer.parseMemoryContent(input.content);
  } else if (input.action === "read_hot") {
    if (typeof writer.read !== "function" || typeof input.path !== "string") throw new Error("Invalid hot-memory read");
    result = writer.read(input.path);
  } else if (input.action === "set_hot") {
    if (typeof writer.setEntries !== "function" || typeof input.path !== "string" || !Array.isArray(input.entries)
        || input.entries.some((entry: unknown) => typeof entry !== "string")) throw new Error("Invalid hot-memory curation");
    result = writer.setEntries(input.path, input.entries, { updatedBy: input.writer, allowDrastic: input.allowDrastic === true });
  } else {
    throw new Error("Unknown native memory operation");
  }
  process.stdout.write(JSON.stringify(result) + "\n");
}

main().catch((error: unknown) => {
  process.stderr.write(String(error) + "\n");
  process.exitCode = 1;
});
