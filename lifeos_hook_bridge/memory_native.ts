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
  if (input.action === "learning_principal") process.env.LIFEOS_CONFIG_PATH = resolve(root, "LIFEOS/USER/CONFIG/LIFEOS_CONFIG.toml");
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
  if (input.action === 'performance_view') {
    if (typeof input.target !== 'string' || !/^\/api\/performance\/(?:cost(?:\?days=[1-9][0-9]{0,3})?|failures|summary|anthropic-cost)$/.test(input.target)
        || !Array.isArray(input.sources) || input.sources.some(source => !object(source)
          || typeof source.relative !== 'string' || typeof source.content !== 'string')
        || typeof input.history_descriptor !== 'number' || !Number.isInteger(input.history_descriptor)
        || input.history_descriptor < 3) throw new Error('Native Performance requires declared admitted histories');
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/Performance/module.ts')).href);
    if (!object(module) || typeof module.renderPerformanceView !== 'function') throw new Error('Native Performance exports are unavailable');
    const response: unknown = await module.renderPerformanceView(input.sources, input.history_descriptor, input.target);
    if (!(response instanceof Response)) throw new Error('Native Performance requires a response');
    result = {status: response.status, body: await response.json()};
  } else if (input.action === 'personal_module_view') {
    if (typeof input.module !== 'string' || !['books', 'projects', 'assets', 'evals', 'threatmodel', 'ledger'].includes(input.module)
        || typeof input.target !== 'string' || typeof input.running !== 'boolean' || !Array.isArray(input.sources)
        || !(input.modified === null || typeof input.modified === 'number' && Number.isFinite(input.modified))
        || input.sources.some(source => !object(source) || typeof source.relative !== 'string' || typeof source.content !== 'string')) {
      throw new Error('Native personal module views require declared admitted sources and runtime state');
    }
    const module: unknown = await import(pathToFileURL(resolve(root, `LIFEOS/PULSE/modules/${input.module}.ts`)).href);
    if (!object(module) || typeof module.renderPersonalView !== 'function') throw new Error('Native personal module exports are unavailable');
    const response: unknown = module.renderPersonalView(input.sources, input.target, input.running, input.modified);
    if (!(response instanceof Response)) throw new Error('Native personal module views require a response');
    result = {status: response.status, body: await response.json()};
  } else if (input.action === 'atlas_collect') {
    if (typeof input.collector !== 'string' || !['gear', 'projects'].includes(input.collector)
        || !(input.content === null || typeof input.content === 'string')) {
      throw new Error('Native Atlas collectors require fixed admitted source text');
    }
    const name = input.collector === 'gear' ? 'Gear' : 'Projects';
    const module: unknown = await import(pathToFileURL(resolve(root, `LIFEOS/ATLAS/collectors/${name}.ts`)).href);
    const render = object(module) ? module[`collect${name}`] : undefined;
    if (typeof render !== 'function') throw new Error('Native Atlas collector exports are unavailable');
    result = render(input.content);
  } else if (input.action === 'atlas_graph_state') {
    process.env.ATLAS_DIR = resolve(root, '../.local/state/lifeos/atlas');
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/ATLAS/Store.ts')).href);
    if (!object(module) || typeof module.atlasGraphState !== 'function') throw new Error('Native Atlas graph exports are unavailable');
    result = module.atlasGraphState();
  } else if (input.action === 'atlas_insights_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/modules/atlas.ts')).href);
    if (!object(module) || typeof module.renderAtlasInsights !== 'function'
        || !(input.metrics === null || object(input.metrics)) || !(input.cache === null || typeof input.cache === 'string')) {
      throw new Error('Native Atlas insights require admitted current metrics and narrative');
    }
    const response: unknown = module.renderAtlasInsights(input.metrics, input.cache);
    if (!(response instanceof Response)) throw new Error('Native Atlas insights require a response');
    result = {status: response.status, body: await response.json()};
  } else if (input.action === 'atlas_snapshot_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/modules/atlas.ts')).href);
    if (!object(module) || typeof module.renderAtlasSnapshot !== 'function'
        || !(input.snapshot === null || object(input.snapshot) && typeof input.snapshot.content === 'string'
          && typeof input.snapshot.modified_ms === 'number' && Number.isFinite(input.snapshot.modified_ms))) {
      throw new Error('Native Atlas views require a declared admitted snapshot');
    }
    const response: unknown = module.renderAtlasSnapshot(input.snapshot);
    if (!(response instanceof Response)) throw new Error('Native Atlas views require a response');
    result = {status: response.status, body: await response.json()};
  } else if (input.action === 'upgrade_store') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/TOOLS/Upgrades.ts')).href);
    if (!object(module) || typeof module.renderUpgradeStore !== 'function' || !Array.isArray(input.sources)
        || input.sources.some(source => !object(source) || typeof source.filename !== 'string' || typeof source.content !== 'string')
        || typeof input.action_name !== 'string' || !object(input.arguments)
        || !(input.state === null || typeof input.state === 'string') || typeof input.now !== 'string'
        || typeof input.source_session !== 'string') throw new Error('Native upgrades require declared current sources and actions');
    result = module.renderUpgradeStore(input.sources,input.state,input.action_name,input.arguments,input.now,input.source_session);
  } else if (input.action === 'life_business_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/Observability/observability.ts')).href);
    if (!object(module) || typeof module.renderBusinessView !== 'function' || typeof input.company !== 'string'
        || !Array.isArray(input.sources) || input.sources.some(source => !object(source)
          || typeof source.relative !== 'string' || typeof source.content !== 'string')) {
      throw new Error('Native business views require declared current company sources');
    }
    const response: unknown = module.renderBusinessView(input.sources, input.company);
    if (!(response instanceof Response)) throw new Error('Native business renderer requires a response');
    result = {status: response.status, body: await response.json()};
  } else if (input.action === 'life_work_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/Observability/observability.ts')).href);
    if (!object(module) || typeof module.renderWorkView !== 'function' || !Array.isArray(input.sources)
        || input.sources.some(source => !object(source) || typeof source.relative !== 'string'
          || typeof source.content !== 'string')) throw new Error('Native local work views require declared current sources');
    const response: unknown = module.renderWorkView(input.sources);
    if (!(response instanceof Response)) throw new Error('Native local work renderer requires a response');
    result = {status: response.status, body: await response.json()};
  } else if (input.action === 'finance_source_projections' || input.action === 'life_finance_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/Observability/observability.ts')).href);
    if (!object(module) || typeof module.financeSourceProjections !== 'function' || typeof module.renderFinanceView !== 'function'
        || !Array.isArray(input.sources) || input.sources.some(source => !object(source)
          || typeof source.relative !== 'string' || typeof source.content !== 'string')) {
      throw new Error('Native finance views require declared current sources');
    }
    if (input.action === 'finance_source_projections') result = {projections: module.financeSourceProjections(input.sources)};
    else {
      const response: unknown = module.renderFinanceView(input.sources);
      if (!(response instanceof Response)) throw new Error('Native finance renderer requires a response');
      result = {status: response.status, body: await response.json()};
    }
  } else if (input.action === 'life_health_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/Observability/observability.ts')).href);
    if (!object(module) || typeof module.renderHealthView !== 'function' || !Array.isArray(input.sources)
        || input.sources.some(source => !object(source) || typeof source.filename !== 'string'
          || typeof source.content !== 'string')) throw new Error('Native health views require declared current sources');
    const response: unknown = module.renderHealthView(input.sources);
    if (!(response instanceof Response)) throw new Error('Native health renderer requires a response');
    result = {status: response.status, body: await response.json()};
  } else if (input.action === 'operational_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/Observability/observability.ts')).href);
    if (!object(module) || typeof module.renderOperationalView !== 'function' || typeof input.target !== 'string'
        || !Array.isArray(input.sources) || input.sources.some(source => !object(source)
          || typeof source.relative !== 'string' || typeof source.content !== 'string')) {
      throw new Error('Native operational views require declared current sources');
    }
    let response: unknown;
    if (input.history_descriptor === undefined) response = module.renderOperationalView(input.sources, input.target);
    else {
      if (typeof module.renderOperationalHistory !== 'function'
          || input.target !== '/api/algorithm' && !/^\/api\/capabilities(?:\?window=(?:60|360|1440))?$/.test(input.target)
          || typeof input.history_descriptor !== 'number' || !Number.isInteger(input.history_descriptor)
          || input.history_descriptor < 3) throw new Error('Operational history requires a private inherited descriptor');
      response = await module.renderOperationalHistory(input.sources, input.history_descriptor, input.target);
    }
    if (!(response instanceof Response)) throw new Error('Native operational views require a response');
    result = {status: response.status, body: await response.json()};
  } else if (input.action === 'onboarding_sources' || input.action === 'onboarding_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/Observability/observability.ts')).href);
    if (!object(module) || typeof module.onboardingViewSources !== 'function' || typeof module.renderOnboardingView !== 'function') {
      throw new Error('Native onboarding exports are unavailable');
    }
    if (input.action === 'onboarding_sources') result = {sources: module.onboardingViewSources()};
    else {
      if (!Array.isArray(input.sources) || input.sources.some(source => !object(source)
          || typeof source.relative !== 'string' || typeof source.content !== 'string')) {
        throw new Error('Native onboarding requires declared current sources');
      }
      const response: unknown = module.renderOnboardingView(input.sources);
      if (!(response instanceof Response)) throw new Error('Native onboarding requires a response');
      result = {status: response.status, body: await response.json()};
    }
  } else if (input.action === 'telos_overview_sources' || input.action === 'telos_overview') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/Observability/observability.ts')).href);
    if (!object(module) || typeof module.telosOverviewSources !== 'function' || typeof module.renderTelosOverview !== 'function') {
      throw new Error('Native TELOS overview exports are unavailable');
    }
    if (input.action === 'telos_overview_sources') result = {sources: module.telosOverviewSources()};
    else {
      if (!Array.isArray(input.sources) || input.sources.some(source => !object(source)
          || typeof source.relative !== 'string' || typeof source.content !== 'string')) {
        throw new Error('Native TELOS overview requires declared current sources');
      }
      const state: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/TOOLS/UpdateLifeosState.ts')).href);
      if (!object(state) || typeof state.renderLifeosState !== 'function') {
        throw new Error('Native current dimension calculation is unavailable');
      }
      const dimensions = Object.fromEntries(input.sources.filter(source => object(source)
        && typeof source.relative === 'string'
        && /^LIFEOS\/USER\/TELOS\/(?:CURRENT_STATE|IDEAL_STATE)\/(?:HEALTH|MONEY|FREEDOM|CREATIVE|RELATIONSHIPS|RHYTHMS|INFRASTRUCTURE)\.md$/.test(source.relative))
        .map(source => [source.relative.slice('LIFEOS/USER/TELOS/'.length), source.content]));
      const rendered: unknown = state.renderLifeosState(dimensions, true);
      if (!object(rendered) || typeof rendered.content !== 'string') {
        throw new Error('Native current dimension calculation changes its declared output');
      }
      const response: unknown = await module.renderTelosOverview(input.sources, rendered.content);
      if (!(response instanceof Response)) throw new Error('Native TELOS overview requires a response');
      result = {status: response.status, body: await response.json()};
    }
  } else if (input.action === 'telos_file_names') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/Observability/observability.ts')).href);
    if (!object(module) || typeof module.telosFileNames !== 'function') {
      throw new Error('Native TELOS file names are unavailable');
    }
    result = {filenames: module.telosFileNames()};
  } else if (input.action === 'user_index_registry' || input.action === 'user_index') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/modules/user-index.ts')).href);
    if (!object(module) || typeof module.userIndexRegistry !== 'function' || typeof module.renderUserIndex !== 'function') {
      throw new Error('Native user index calculations are unavailable');
    }
    if (input.action === 'user_index_registry') result = {skip_directories: module.userIndexRegistry()};
    else {
      if (!Array.isArray(input.sources) || input.sources.some(source => !object(source)
          || typeof source.relative !== 'string' || typeof source.content !== 'string'
          || typeof source.modified !== 'string' || typeof source.size !== 'number')) {
        throw new Error('Native user index calculations require declared sources');
      }
      result = {index: module.renderUserIndex(input.sources)};
    }
  } else if (input.action === 'life_view_sources' || input.action === 'life_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/Observability/observability.ts')).href);
    if (!object(module) || typeof module.lifeViewSources !== 'function' || typeof module.renderLifeView !== 'function') {
      throw new Error('Native Life views are unavailable');
    }
    if (input.action === 'life_view_sources') result = {filenames: module.lifeViewSources()};
    else {
      if (typeof input.target !== 'string' || !Array.isArray(input.sources) || input.sources.some(source => !object(source)
          || typeof source.filename !== 'string' || typeof source.content !== 'string')) {
        throw new Error('Native Life views require declared current sources');
      }
      const response: unknown = module.renderLifeView(input.sources, input.target);
      if (!(response instanceof Response)) throw new Error('Native Life renderer requires a response');
      result = {status: response.status, body: await response.json()};
    }
  } else if (input.action === 'morning_brief') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/checks/life-morning-brief.ts')).href);
    if (!object(module) || typeof module.renderMorningBrief !== 'function' || !Array.isArray(input.sources)
        || input.sources.some(source => !object(source) || typeof source.filename !== 'string'
          || typeof source.content !== 'string')) throw new Error('Native morning brief requires declared current sources');
    result = {stdout: module.renderMorningBrief(input.sources)};
  } else if (input.action === 'tab_freshness_specs' || input.action === 'tab_freshness_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/modules/tab-freshness.ts')).href);
    if (!object(module) || typeof input.tab !== 'string' || typeof module.tabFreshnessSpecifications !== 'function'
        || typeof module.renderTabFreshness !== 'function') throw new Error('Native tab freshness requires its fixed registry');
    if (input.action === 'tab_freshness_specs') result = {specifications: module.tabFreshnessSpecifications(input.tab)};
    else {
      if (!Array.isArray(input.sources) || input.sources.some(source => !object(source)
          || typeof source.name !== 'string' || typeof source.path !== 'string' || typeof source.exists !== 'boolean'
          || !(source.mtime === null || typeof source.mtime === 'string')
          || !(source.content === null || typeof source.content === 'string'))) {
        throw new Error('Native tab freshness requires declared current sources and timestamps');
      }
      result = {status: 200, body: module.renderTabFreshness(input.tab,input.sources)};
    }
  } else if (input.action === 'upgrades_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/modules/upgrades.ts')).href);
    if (!object(module) || typeof module.renderUpgradesView !== 'function' || !Array.isArray(input.records)
        || !Array.isArray(input.hypotheses) || [...input.records, ...input.hypotheses].some(source => !object(source)
          || typeof source.filename !== 'string' || typeof source.content !== 'string') || typeof input.target !== 'string') {
      throw new Error('Native upgrades views require declared current records and hypotheses');
    }
    result = module.renderUpgradesView(input.records,input.hypotheses,input.target);
  } else if (input.action === 'hypothesis_review') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/modules/hypotheses.ts')).href);
    if (!object(module) || typeof module.renderHypothesisReview !== 'function' || !object(input.sources)
        || !Array.isArray(input.sources.hypotheses) || !object(input.sources.frames)
        || input.sources.hypotheses.some(source => !object(source) || typeof source.filename !== 'string' || typeof source.content !== 'string')
        || Object.values(input.sources.frames).some(content => typeof content !== 'string')
        || typeof input.sources.directory_exists !== 'boolean'
        || !(input.sources.state === null || typeof input.sources.state === 'string')
        || typeof input.slug !== 'string' || (input.verb !== 'graduate' && input.verb !== 'reject')
        || !(input.note === null || typeof input.note === 'string') || typeof input.now !== 'string') {
      throw new Error('Native hypothesis review requires declared sources and actions');
    }
    result = await module.renderHypothesisReview(input.sources, input.slug, input.verb,
      input.note === null ? undefined : input.note, input.now);
  } else if (input.action === 'hypothesis_list') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/modules/hypotheses.ts')).href);
    if (!object(module) || typeof module.renderHypothesisList !== 'function' || !Array.isArray(input.sources)
        || input.sources.some(source => !object(source) || typeof source.filename !== 'string' || typeof source.content !== 'string')) {
      throw new Error('Native pending hypotheses require declared current sources');
    }
    result = {status: 200, body: {hypotheses: module.renderHypothesisList(input.sources)}};
  } else if (input.action === 'hypothesis_view') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/PULSE/modules/hypotheses.ts')).href);
    if (!object(module) || typeof module.renderHypothesesView !== 'function' || !Array.isArray(input.sources)
        || input.sources.some(source => !object(source) || typeof source.filename !== 'string' || typeof source.content !== 'string')
        || typeof input.target !== 'string') throw new Error('Native hypothesis views require declared current sources');
    result = module.renderHypothesesView(input.sources, input.target);
  } else if (input.action === 'session_harvest') {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/TOOLS/SessionHarvester.ts')).href);
    if (!object(module) || typeof module.renderSessionHarvest !== 'function' || !Array.isArray(input.sessions)
        || typeof input.mine !== 'boolean' || typeof input.now !== 'string') {
      throw new Error('Session consolidation requires declared transcripts and modes');
    }
    result = module.renderSessionHarvest(input.sessions, input.mine, input.now);
  } else if (input.action === "proposal_gc") {
    const module: unknown = await import(pathToFileURL(resolve(root, 'LIFEOS/TOOLS/ProposalGC.ts')).href);
    if (!object(module) || typeof module.renderProposalGC !== 'function' || !object(input.sources)
        || Object.values(input.sources).some(content => typeof content !== 'string')
        || typeof input.auto !== 'boolean' || typeof input.route !== 'boolean') {
      throw new Error('Proposal cleanup requires declared sources and modes');
    }
    result = module.renderProposalGC(input.sources, input.auto, input.route);
  } else if (input.action === "learning_principal") {
    const module: unknown = await import(pathToFileURL(resolve(root, "hooks/lib/identity.ts")).href);
    if (!object(module) || typeof module.getPrincipalName !== "function") throw new Error("Native principal identity is unavailable");
    result = {name: module.getPrincipalName()};
  } else if (input.action === "learning_hypotheses") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/LearningPatternSynthesis.ts")).href);
    const ledger: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/RecurrenceLedger.ts")).href);
    const sources = input.sources;
    if (!object(module) || typeof module.renderHypothesisDerivation !== "function" || !object(ledger)
        || typeof ledger.collectObservabilityClusters !== "function" || typeof ledger.readPatchRegistry !== "function"
        || !object(sources) || !Array.isArray(sources.recurrence) || !Array.isArray(sources.ratings)
        || !Array.isArray(sources.frames) || !Array.isArray(sources.people) || !Array.isArray(sources.hypotheses)
        || typeof sources.log !== "string" || typeof sources.principal !== "string"
        || typeof input.now !== "string" || !Number.isFinite(Date.parse(input.now))
        || typeof input.window !== "number" || !Number.isInteger(input.window) || input.window < 1 || input.window > 365
        || typeof input.dry_run !== "boolean" || typeof input.no_inference !== "boolean" || typeof input.once_daily !== "boolean"
        || !(input.stamp === null || typeof input.stamp === "string")) throw new Error("Native hypothesis derivation requires declared current sources");
    const today = new Date(input.now).toLocaleDateString("en-CA");
    if (input.once_daily && !input.dry_run && input.stamp?.trim() === today) {
      result = {result: {emitted: 0, updated: 0, expired: 0}, publications: [],
        stdout: `🌙 deriver: already ran ${today} (--once-daily) — skipping\n`};
    } else {
      const declared = {...sources, now: input.now,
        clusters: ledger.collectObservabilityClusters(input.window, sources.recurrence),
        healed: ledger.readPatchRegistry(sources.recurrence).map((row: {class_id: string}) => row.class_id)};
      const rendered: unknown = await module.renderHypothesisDerivation({window: input.window,
        dryRun: input.dry_run, noInference: input.no_inference}, declared);
      if (!object(rendered) || !object(rendered.result) || !Array.isArray(rendered.publications)) throw new Error("Native hypothesis artifacts are invalid");
      if (input.once_daily && !input.dry_run) rendered.publications.push({path: resolve(root, "LIFEOS/MEMORY/OBSERVABILITY/deriver-lastrun.date"), content: today + "\n"});
      result = {...rendered, stdout: `🌙 deriver: window=${input.window}d expired=${rendered.result.expired} emitted=${rendered.result.emitted} updated=${rendered.result.updated}${input.dry_run ? " (dry-run)" : ""}\n`};
    }
  } else if (input.action === "recurrence_append") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/RecurrenceLedger.ts")).href);
    if (!object(module) || typeof module.renderPatchRegistry !== "function" || typeof input.previous !== "string"
        || !object(input.record)) throw new Error("Native registry publication requires declared record and bytes");
    result = {content: module.renderPatchRegistry(input.previous, input.record)};
  } else if (input.action === "distill_prepare") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/KnowledgeDistill.ts")).href);
    if (!object(module) || typeof module.prepareDistill !== "function" || !Array.isArray(input.sources)
        || input.sources.some(source => !object(source) || typeof source.path !== "string" || typeof source.content !== "string")
        || !(input.state === null || object(input.state)) || !(input.config === null || object(input.config))) {
      throw new Error("Native distill preparation requires declared state, configuration, and sources");
    }
    result = module.prepareDistill(input.state, input.config, input.sources);
  } else if (input.action === "distill_mark") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/KnowledgeDistill.ts")).href);
    if (!object(module) || typeof module.markDistill !== "function" || typeof input.content !== "string"
        || !(input.state === null || object(input.state))) {
      throw new Error("Native distill marking requires declared digest text and state");
    }
    result = module.markDistill(input.content, input.state);
  } else if (input.action === "distill_read") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/KnowledgeDistill.ts")).href);
    if (!object(module) || typeof module.readDistill !== "function" || !Array.isArray(input.args)
        || input.args.some(arg => typeof arg !== "string") || !Array.isArray(input.sources)
        || input.sources.some(source => !object(source) || typeof source.path !== "string" || typeof source.content !== "string")
        || !(input.state === null || object(input.state)) || !(input.config === null || object(input.config))) {
      throw new Error("Native distill read requires declared arguments and sources");
    }
    result = {value: module.readDistill(input.args, input.state, input.config, input.sources)};
  } else if (input.action === "pulse_manifest" || input.action === "pulse_sources") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/lib/manifest-loader.ts")).href);
    if (!object(module) || typeof module.parseManifest !== "function" || typeof module.resolveSources !== "function") {
      throw new Error("Native PULSE manifest exports are unavailable");
    }
    if (input.action === "pulse_manifest") {
      if (typeof input.content !== "string") throw new Error("PULSE manifests require declared text");
      result = {manifest: module.parseManifest(input.content)};
    } else {
      if (!object(input.manifest) || !Array.isArray(input.manifest.sourceGlobs)
          || input.manifest.sourceGlobs.some(value => typeof value !== "string")) {
        throw new Error("PULSE source resolution requires declared manifest globs");
      }
      result = {paths: module.resolveSources(input.manifest, root)};
    }
  } else if (input.action === "pulse_validate_page") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/PULSE/Schema/PulseSchema.ts")).href);
    if (!object(module) || !object(module.PageDataSchema) || typeof module.PageDataSchema.safeParse !== "function"
        || !object(module.PageMetaSchema) || typeof module.PageMetaSchema.safeParse !== "function") {
      throw new Error("Native PULSE schema exports are unavailable");
    }
    const page = input.page;
    result = {valid: object(page) && page.schemaVersion === "1.0.0"
      && module.PageDataSchema.safeParse(page.data).success === true
      && module.PageMetaSchema.safeParse(page._meta).success === true};
  } else if (input.action === "derived_sync_plan" || input.action === "derived_sync_finish") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/DerivedSync.ts")).href);
    const state = input.state;
    const hashes = input.hashes;
    if (!object(module) || typeof module.planDerivedSync !== "function" || typeof module.finishDerivedSync !== "function"
        || !object(hashes) || Object.values(hashes).some(hash => typeof hash !== "string" || !/^[a-f0-9]{64}$/.test(hash))
        || !(state === null || object(state) && object(state.fileHashes) && typeof state.lastRun === "string")
        || !Array.isArray(input.pages) || input.pages.some(id => typeof id !== "string") || typeof input.force !== "boolean") {
      throw new Error("Native derivative planning requires declared hashes, state, pages, and force mode");
    }
    const declared = {state, hashes, pages: input.pages, force: input.force};
    if (input.action === "derived_sync_plan") result = module.planDerivedSync(declared);
    else {
      if (!Array.isArray(input.failed) || input.failed.some(value => typeof value !== "boolean")) {
        throw new Error("Native derivative tracking requires declared child results");
      }
      result = module.finishDerivedSync(declared, input.failed);
    }
  } else if (input.action === "deny_hash_environment") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/DeriveDenyHashes.ts")).href);
    if (!object(module) || typeof module.renderDenyHashEnvironment !== "function" || typeof input.content !== "string") {
      throw new Error("Native deny salt generation requires declared environment bytes");
    }
    result = module.renderDenyHashEnvironment(input.content);
  } else if (input.action === "deny_hashes") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/DeriveDenyHashes.ts")).href);
    if (!object(module) || typeof module.renderDenyHashes !== "function" || !Array.isArray(input.sources)
        || input.sources.some(value => typeof value !== "string") || typeof input.operator !== "string"
        || !(input.salt === null || typeof input.salt === "string")) {
      throw new Error("Native deny hashing requires declared source and operator text");
    }
    result = module.renderDenyHashes(input.sources, input.operator, input.salt);
  } else if (input.action === "learning_ratings") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/LearningPatternSynthesis.ts")).href);
    if (!object(module) || typeof module.renderRatingSynthesis !== "function"
        || !(input.ratings === null || Array.isArray(input.ratings)) || typeof input.path !== "string"
        || typeof input.month !== "boolean" || typeof input.all !== "boolean" || typeof input.dry_run !== "boolean"
        || typeof input.now !== "string" || !Number.isFinite(Date.parse(input.now))) {
      throw new Error("Native learning analysis requires declared ratings");
    }
    result = module.renderRatingSynthesis(input.ratings,
      {month: input.month, all: input.all, dryRun: input.dry_run}, input.path, input.now);
  } else if (input.action === "wisdom_synthesis") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/WisdomCrossFrameSynthesizer.ts")).href);
    if (!object(module) || typeof module.renderCrossFrameSynthesis !== "function" || !Array.isArray(input.sources)
        || input.sources.some(source => !object(source) || typeof source.path !== "string" || typeof source.content !== "string")
        || typeof input.health !== "boolean" || typeof input.dry_run !== "boolean" || typeof input.exists !== "boolean") {
      throw new Error("Native Wisdom synthesis requires declared frame sources");
    }
    result = module.renderCrossFrameSynthesis(input.sources, input.health, input.dry_run, input.exists);
  } else if (input.action === "wisdom_frame_update") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/WisdomFrameUpdater.ts")).href);
    if (!object(module) || typeof module.renderFrameUpdate !== "function" || typeof input.domain !== "string"
        || typeof input.observation !== "string" || typeof input.type !== "string" || typeof input.path !== "string"
        || !(input.previous === null || typeof input.previous === "string")) {
      throw new Error("Native Wisdom update requires declared frame content");
    }
    result = module.renderFrameUpdate(input.domain, input.observation, input.type, input.previous, input.path);
  } else if (input.action === "hermes_soul_names" || input.action === "hermes_soul_render") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/RenderHermesSoul.ts")).href);
    const sources = input.sources;
    if (!object(module) || typeof module.renderHermesSoul !== "function"
        || typeof module.renderHermesSoulNames !== "function" || !object(sources)
        || !["daIdentity", "daMemory", "principal", "principalMemory", "telos", "projects"].every(
          name => typeof sources[name] === "string")) {
      throw new Error("Native Hermes soul rendering requires declared source text");
    }
    result = input.action === "hermes_soul_names" ? module.renderHermesSoulNames(sources)
      : typeof input.integrationSoul === "string" && typeof module.renderMountedHermesSoul === "function"
        ? module.renderMountedHermesSoul(input.integrationSoul, sources) : module.renderHermesSoul(sources);
  } else if (input.action === "interview_scan_name") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/InterviewScan.ts")).href);
    if (!object(module) || typeof module.renderScanName !== "function" || !(input.content === null || typeof input.content === "string")) {
      throw new Error("Native interview naming requires declared identity text");
    }
    result = {name: module.renderScanName(input.content)};
  } else if (input.action === "interview_scan") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/InterviewScan.ts")).href);
    const evidence: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/StateEvidence.ts")).href);
    if (!object(module) || typeof module.renderInterviewScan !== "function" || !object(evidence)
        || typeof evidence.gatherEvidence !== "function" || typeof input.name !== "string"
        || !Array.isArray(input.args) || input.args.some(arg => typeof arg !== "string") || !Array.isArray(input.sources)
        || !(input.evidence === null || object(input.evidence) && Array.isArray(input.evidence.sources)
          && (input.evidence.gitCommits === null || Array.isArray(input.evidence.gitCommits)
            && input.evidence.gitCommits.every(date => typeof date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(date))))) {
      throw new Error("Native interview scan requires declared text, evidence, and arguments");
    }
    function declared(values: unknown[]): Record<string, {path: string; content: string; lastModified: string}> {
      const sources: Record<string, {path: string; content: string; lastModified: string}> = {};
      for (const source of values) {
        if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string"
            || typeof source.lastModified !== "string" || Object.hasOwn(sources, source.path)) {
          throw new Error("Native interview scan requires distinct declared source bytes and dates");
        }
        sources[source.path] = {path: source.path, content: source.content, lastModified: source.lastModified};
      }
      return sources;
    }
    let observed = null;
    if (object(input.evidence)) {
      const sources: Record<string, string> = {};
      for (const value of Object.values(declared(input.evidence.sources))) sources[value.path] = value.content;
      observed = evidence.gatherEvidence(new Date(), {sources, gitCommits: input.evidence.gitCommits});
    }
    result = module.renderInterviewScan(input.args, {sources: declared(input.sources), name: input.name, evidence: observed});
  } else if (input.action === "interview_completion") {
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
  } else if (input.action === "context_audit") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/ContextAudit.ts")).href);
    if (!object(module) || typeof module.renderContextAudit !== "function" || !Array.isArray(input.sources)
        || input.sources.some(source => !object(source) || typeof source.path !== "string" || typeof source.content !== "string")) {
      throw new Error("Native context audit needs declared constitutional sources");
    }
    result = module.renderContextAudit(input.sources);
  } else if (input.action === "counts") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/GetCounts.ts")).href);
    const keys = ["skills", "workflows", "hooks", "signals", "files", "work", "research", "ratings"];
    if (!object(module) || typeof module.getCounts !== "function"
        || !(input.only === null || typeof input.only === "string" && keys.includes(input.only))) {
      throw new Error("Native installation counts require a fixed count selection");
    }
    result = module.getCounts(input.only ?? undefined, root, resolve(root, "LIFEOS"));
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
  } else if (input.action === "knowledge_conformance") {
    const module: unknown = await import(pathToFileURL(resolve(root, "hooks/handlers/KnowledgeConformance.ts")).href);
    if (!object(module) || typeof module.renderKnowledgeConformance !== "function" || !Array.isArray(input.sources)
        || !Array.isArray(input.directories) || !input.directories.every(value => typeof value === "string")
        || typeof input.exists !== "boolean") {
      throw new Error("Native Knowledge findings need declared sources and archive directories");
    }
    const sources: Array<{path: string; content: string}> = [];
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string") {
        throw new Error("Native Knowledge findings need declared source text");
      }
      sources.push({path: source.path, content: source.content});
    }
    result = module.renderKnowledgeConformance(sources, input.directories, input.exists);
  } else if (input.action === "knowledge_lint") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/KnowledgeLint.ts")).href);
    if (!object(module) || typeof module.renderKnowledgeLint !== "function" || !Array.isArray(input.sources)
        || typeof input.json !== "boolean" || typeof input.list !== "number" || !Number.isSafeInteger(input.list)
        || input.list < 0 || input.list > 10000 || !(input.directory === null || typeof input.directory === "string")) {
      throw new Error("Native Knowledge lint needs declared sources and bounded report options");
    }
    const sources: Array<{path: string; content: string}> = [];
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string") {
        throw new Error("Native Knowledge lint needs declared source text");
      }
      sources.push({path: source.path, content: source.content});
    }
    result = {stdout: module.renderKnowledgeLint(sources, {json: input.json, list: input.list, directory: input.directory})};
  } else if (input.action === "knowledge_harvester_view") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/KnowledgeHarvester.ts")).href);
    if (!object(module) || typeof module.renderKnowledgeView !== "function" || !Array.isArray(input.sources)
        || typeof input.view !== "string" || !["review", "status", "contradictions", "index"].includes(input.view) || !Array.isArray(input.ordering)
        || !input.ordering.every(value => typeof value === "string")) {
      throw new Error("Native Knowledge views need declared sources and options");
    }
    const sources: Array<{path: string; content: string}> = [];
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string") {
        throw new Error("Native Knowledge views need declared source text");
      }
      sources.push({path: source.path, content: source.content});
    }
    result = module.renderKnowledgeView(sources, input.view, input.ordering);
  } else if (input.action === "knowledge_harvest") {
    const module: unknown = await import(pathToFileURL(resolve(root, "LIFEOS/TOOLS/KnowledgeHarvester.ts")).href);
    if (!object(module) || typeof module.renderHarvest !== "function" || !Array.isArray(input.sources)
        || !(input.source === null || typeof input.source === "string") || typeof input.dry_run !== "boolean"
        || typeof input.max_notes !== "number" || !Number.isSafeInteger(input.max_notes)
        || input.max_notes < 1 || input.max_notes > 50 || !Array.isArray(input.occupied)
        || !input.occupied.every(value => typeof value === "string") || !Array.isArray(input.ordering)
        || !input.ordering.every(value => typeof value === "string")) {
      throw new Error("Native harvesting needs declared sources and bounded options");
    }
    const sources: Array<{path: string; content: string}> = [];
    for (const source of input.sources) {
      if (!object(source) || typeof source.path !== "string" || typeof source.content !== "string") {
        throw new Error("Native harvesting needs declared source text");
      }
      sources.push({path: source.path, content: source.content});
    }
    result = module.renderHarvest(sources, input.source, input.dry_run, input.max_notes, input.occupied, input.ordering);
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
