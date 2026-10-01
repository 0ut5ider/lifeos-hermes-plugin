     1	# Future memory integration: LifeOS as the durable store
     2	
     3	Date: 2026-09-30. Status: Adrian authorizes implementation of this design now. The [implementation plan](../docs/memory-implementation-plan.md) records progress and activation gates. Memory ownership and sharing require their acceptance evidence. Hook parity remains a separate completion gate. This authorization does not permit copying existing server memory.
     4	
     5	## Resolved fresh-install experience
     6	
     7	Design resolution: a fresh LifeOS-enabled installation provides one lasting memory system, owned by LifeOS. Hermes retains conversation history, session search, and context compression. Other agents can optionally use the same lasting memory through an authenticated MCP connection. This is the target experience, not a statement that a memory provider is installed today.
     8	
     9	### What the user does
    10	
    11	1. Install Hermes and the LifeOS plugin.
    12	2. Select **Install LifeOS** in the plugin page.
    13	3. Complete LifeOS setup and select **Use LifeOS for lasting memory**, the recommended fresh-install choice.
    14	4. Chat normally. Native LifeOS hooks recall relevant memory and run their existing review process.
    15	5. Ask the agent to remember, find, correct, or forget a fact. The agent reports whether the change is saved, waiting for review, or rejected.
    16	6. Enable **Share memory with another agent** only when another agent needs access. Sharing is off until this step.
    17	
    18	The user does not choose two memory providers or keep two stores synchronized. The plugin must show whether LifeOS recall and saving work before it switches memory ownership. A failed setup keeps the prior configuration and shows the failure.
    19	
    20	Fresh installations contain only their new owner's data. They require no existing server, copied archive, or `.211`/`.213` connection. Existing Hermes users get a separate, optional import preview. That migration does not form part of the fresh-install default.
    21	
    22	### What remembering means
    23	
    24	| User action | Required result |
    25	| --- | --- |
    26	| Remember this fact | Save an allowed fact in the appropriate native LifeOS layer. Return its reference and writer provenance. If approval is required, say that it is pending. |
    27	| What do you know about this project? | Search permitted current LifeOS knowledge. Keep source references and distinguish retrieved facts from inference. |
    28	| That fact is wrong | Correct the identified record or submit a clearly labeled proposal. Ordinary recall must stop presenting the superseded version as current after the correction applies. |
    29	| Forget this | Remove the record from ordinary recall and invalidate derived context. Report remaining audit, backup, conversation-history, and development-log copies separately. Do not promise that these copies were erased. |
    30	
    31	The same meaning applies in Hermes and in an authorized MCP client. Raw conversation transcripts remain conversation history; saving them does not make every statement a lasting fact. Pending changes must never be described as applied changes.
    32	
    33	### Default sharing policy
    34	
    35	Remote sharing starts disabled. The first optional remote connection uses MCP over a restricted SSH connection. Give each client its own authenticated identity and revocable key. Generate connection instructions for supported clients instead of asking users to edit memory paths.
    36	
    37	A newly enrolled client starts with read access to the categories the user selected. The connection page preselects project knowledge, with principal preferences and identity left unselected. Project-fact writes require a separate grant. Changes to principal preferences, assistant rules, and identity use the native review policy. Another agent cannot grant itself those permissions by supplying a caller name. Revoking access removes its connection; it does not delete facts it previously contributed.
    38	
    39	Separate credentials from memory contents. The service sends only records that the client may read. MCP permissions govern that interface. A client with direct filesystem access can bypass it, so stronger isolation requires separate operating-system permissions. Local clients may use process transport; remote clients need authenticated transport. No public HTTP endpoint is needed for the initial version. A cloud-routed client can expose returned memory to its model provider, so the connection page must show the client's declared model route and permitted categories. An unknown model route must appear as unknown; the memory service cannot establish a client's downstream route from its name or SSH key.
    40	
    41	The MCP service shares facts and memory operations. It does not automatically give another agent LifeOS hooks, personality, background review jobs, or Hermes conversations. That boundary must be stated in the connection page.
    42	
    43	### Normal preferences page
    44	
    45	Keep the main page small:
    46	
    47	- **Lasting memory:** LifeOS, with a short explanation that Hermes retains conversation history.
    48	- **Memory status:** recall, saving, reviewer status, and the last verified failure.
    49	- **Review memories:** search current records and view their sources, corrections, and pending changes.
    50	- **Automatic review:** the existing LifeOS cadence and the configured review model.
    51	- **Share with another agent:** disabled by default; connected clients and their permissions appear after enrollment.
    52	
    53	Put import, backup, restore, and diagnostic details in an advanced section. Restore changes configuration without deleting memories. Keep privacy and retention settings separate from model routing.
    54	
    55	### Implementation boundary
    56	
    57	Ship the memory provider and optional MCP support with the plugin. Both adapters use native LifeOS retrieval and write operations through one policy implementation. Keep native memory hooks as the automatic recall and review owners. Do not add a second provider-driven extractor or a second archive of the same facts.
    58	
    59	Native hooks already call LifeOS operations. The adapter must use those operations and preserve their validation, locking, caps, and proposal rules. Drawing a shared access layer does not make existing direct hook writes pass through it. Verify all active writers and retrieval paths before claiming that a policy is enforced for the whole installation.
    60	
    61	## Installation model
    62	
    63	Build a self-contained installation: Hermes, the plugin, and LifeOS on a new server. The user installs Hermes, installs the plugin, and installs LifeOS through the plugin settings page. Memory must work on that server without another machine.
    64	
    65	Use `.212` for development and disposable test profiles. The working `.211` and `.213` systems are references only. Leave both unchanged. Do not copy their memory, hard-coded addresses, caller policies, SSH configuration, or deployment layout into the new installation.
    66	
    67	Sharing memory with other agents is optional. It exposes this installation's LifeOS store; it does not connect the installation to the existing `.211` archive.
    68	
    69	## Accepted ownership
    70	
    71	LifeOS owns durable memory for a LifeOS-enabled Hermes installation. Keep Hermes's memory manager and integrate through its supported memory-provider interface. Replacing the runtime memory manager would add code changes and update risk without resolving a storage requirement.
    72	
    73	| Responsibility | Owner |
    74	| --- | --- |
    75	| Durable facts, project findings, decisions, and lessons | LifeOS knowledge archive |
    76	| Principal preferences and assistant working preferences | LifeOS principal and assistant memory |
    77	| Automatic recall and durable memory review | LifeOS hooks and tools |
    78	| Conversation history and session search | Hermes |
    79	| Context compression and active session management | Hermes |
    80	| Procedural skills and skill learning | Existing Hermes and LifeOS mechanisms; assess separately from durable memory |
    81	| Shared access from authorized agents | Plugin-provided Model Context Protocol (MCP) service |
    82	
    83	One authoritative store can contain several LifeOS memory layers. It does not require one file for every kind of memory. Conversation history remains separate from curated durable facts.
    84	
    85	The target default disables independent writes and context injection from Hermes's built-in `MEMORY.md` and `USER.md` stores. Preserve existing files. Enable that default only after the supported Hermes version passes the behavior tests below.
    86	
    87	Do not maintain two editable copies of a fact. A derived cache, if needed, must identify its LifeOS source and refresh rule. It cannot become another authoritative store.
    88	
    89	## Why this direction
    90	
    91	Two independent stores can retain conflicting preferences or stale corrections. Synchronizing them would require conflict resolution, correction propagation, deletion propagation, and ownership rules. Give LifeOS ownership instead.
    92	
    93	Keeping both stores active offers a less disruptive transition and retains existing Hermes memory controls. It also retains the duplication risk. Provide a choice to keep the current setup, explain its limits, and test the LifeOS default before switching.
    94	
    95	One durable store makes memory availability more important. The plugin must show failures and provide recovery. It must not silently write to the former Hermes store when LifeOS is unavailable.
    96	
    97	## Two interfaces, one write policy
    98	
    99	Provide a Hermes memory provider and an MCP service backed by the same governed LifeOS access implementation. Each interface must use the installed LifeOS paths and compatibility set.
   100	
   101	```mermaid
   102	flowchart TB
   103	    Hermes["Hermes with LifeOS plugin"]
   104	    Hooks["Native LifeOS memory hooks"]
   105	    Provider["Hermes memory provider"]
   106	    Clients["Authorized external agents"]
   107	    MCP["Optional memory MCP service"]
   108	    Access["Governed LifeOS memory access"]
   109	    Store["This installation's LifeOS durable memory"]
   110	    Hermes --> Hooks
   111	    Hermes --> Provider
   112	    Hooks --> Access
   113	    Provider --> Access
   114	    Clients --> MCP
   115	    MCP --> Access
   116	    Access --> Store
   117	```
   118	
   119	The provider supplies explicit memory tools and integrates with Hermes. The MCP service gives Claude Code, Codex, OpenCode, or another client access without requiring that client to run Hermes or the full LifeOS hook set.
   120	
   121	Assess reuse of the existing `lifeos-memory-mcp` project as a versioned dependency or shared component. Keep one maintained implementation of its policy and protocol. Packaging remains open; do not assume that its current deployment can be copied unchanged.
   122	
   123	Use local process access for the colocated installation. Start remote sharing disabled. For the first remote transport, assess SSH carrying MCP over standard input and output, with a restricted key for each client. A separate HTTP service is not a prerequisite. Credentials must bind the client policy; a caller-name argument alone is not an access boundary.
   124	
   125	## Preserve hooks and prevent duplicate work
   126	
   127	Keep the native LifeOS memory hooks and their observable behavior. When `MemoryTurnStart` owns automatic recall, the provider must not inject a second copy of the same records. Explicit searches remain available.
   128	
   129	Map all loaded context, including small memory files and any LifeOS content rendered into `SOUL.md`. Identify snapshots that can become stale, their refresh rules, and repeated injection across hooks and the provider. Avoid introducing an extra recall path to compensate for a broken hook.
   130	
   131	LifeOS owns durable memory review. Assess how to retain Hermes skill learning independently. If Hermes produces a durable memory candidate, route it through the same governed LifeOS write or proposal path. Do not disable all Hermes background review solely to stop duplicate fact extraction.
   132	
   133	## Memory operations and failures
   134	
   135	Define and test remembering, recalling, correcting, and forgetting. The existing MCP search, retrieval, and append-style writes do not establish equivalence with Hermes add, replace, and remove operations. Use supported LifeOS operations or an explicit review workflow for changes that need approval.
   136	
   137	A correction must prevent ordinary recall from presenting a superseded claim as current. An appended correction alone is insufficient if search still returns the original claim. Define what forgetting removes, what audit evidence remains, and whether that evidence can enter model context.
   138	
   139	Record the writer and source for saved facts. Verify concurrent writes, interrupted writes, repeated requests, record identity, and recovery against LifeOS's actual storage behavior. Do not assume either interface supplies these guarantees.
   140	
   141	Report unavailable recall and failed saves clearly. Never report a failed save as successful. Preserve the conversation when memory fails unless an existing required LifeOS hook specifies a blocking outcome. Test that hook outcome rather than weakening it.
   142	
   143	## Privacy and sharing
   144	
   145	Set read and write permissions for each authenticated client. Permissions must follow the client's approved use and model route. A process running on the LAN may still send returned records to a cloud model.
   146	
   147	Keep memory access permissions separate from delivery permissions. A record permitted in a private session is not automatically permitted in a shared conversation. Use one policy for every connected messaging app. Verify private chats, groups, shared channels, threads, scheduled messages, and child-agent context where supported.
   148	
   149	Protect credentials and sensitive records through the governed access path. Document what the service enforces and what requires operating-system isolation or agent instructions. Do not describe a configurable caller name as enforced isolation.
   150	
   151	## Contracts clarified by the independent review
   152	
   153	The [independent design review](../docs/agents/2026-09-30-memory-design-review/memory-design-review.md) identified three contracts that need explicit requirements before implementation. These requirements refine the accepted ownership model. They do not enable a provider, migrate data, or establish runtime guarantees.
   154	
   155	### Current facts, retained history, and corrections
   156	
   157	Use active, superseded, forgotten, and pending status consistently across hot entries, archive sections, searchable learning records, and derived context. Ordinary recall must exclude superseded and forgotten claims. Retained historical material may remain available through an explicitly requested history operation under the user's access and retention policy. A historical label alone does not satisfy forgetting.
   158	
   159	Applied corrections and forget decisions must also govern native reviewers that process old transcripts or learning records. An older retained source cannot automatically recreate the removed claim. A later authenticated request to remember the fact again must be treated as a new request, with any conflicting correction or forget decision shown before the user authorizes reactivation.
   160	
   161	Reuse native references, status, and operations where they satisfy these requirements. If native operations cannot express them, document and test the smallest necessary extension before enabling the operation. Keep any required metadata with this installation's native store and backups. Do not create another editable copy of the facts.
   162	
   163	### One context policy for all messaging apps
   164	
   165	The host binds each operation to an authenticated principal and a trusted context policy. The policy includes the current author, participants, conversation visibility, permitted memory categories, selected model route, and actual outbound destination. Messaging adapters supply this information; the memory rules remain the same across apps. Equivalent authenticated contexts receive equivalent memory behavior and access.
   166	
   167	Bind account IDs from different apps to the same principal only through an approved identity mapping. Display names, prompt text, tool arguments, and client-supplied caller names cannot establish that binding. Recheck the current author in shared sessions. Unknown identity, visibility, or recipients receive restricted access; private memory remains excluded until authorization is established. Expose missing adapter metadata as a capability limit rather than treating it as a private conversation.
   168	
   169	Apply the policy before memory reaches any model through native hook output, explicit tools, rendered context, inherited child context, compression, or reviewer input. Enforce destination permissions separately before sending a response. A task that sends to another audience must use context permitted for that audience; filtering the final response alone is insufficient.
   170	
   171	Permission reductions, participant changes, audience changes, and destination changes require affected context and caches to be invalidated or rebuilt. Recalled facts must also refresh after corrections and forgetting. Cache results must be scoped by identity, policy, and store revision, or invalidated with equivalent guarantees. Never reuse a private context for a restricted session because its query text matches.
   172	
   173	Preserve native hook ownership, cadence, and behavior in authorized contexts. Restricted-context filtering is an explicit privacy requirement. If native interfaces cannot enforce it, record the necessary extension and its comparison tests. Do not claim that provider or MCP permissions govern native direct reads without proving that boundary.
   174	
   175	Verify actual model inputs with synthetic permitted and denied markers across at least two messaging adapters. Cover private and shared conversations, changing authors and participants, unknown metadata, scheduled sends, child tasks, resume, and compression. These tests establish representative evidence. Verify trusted metadata and common-policy behavior for every supported adapter before claiming support. An adapter that lacks required metadata stays restricted and reports that limitation.
   176	
   177	### References, write receipts, and safe retries
   178	
   179	A saved reference identifies a native file or note plus its entry or section, revision, and status. It must remain meaningful when unrelated entries move or change. Corrections and forgetting must refuse ambiguous targets and stale destructive edits. Establish the concrete native representation in disposable fixtures before exposing these operations.
   180	
   181	Bind writer identity to the authenticated Hermes author or enrolled MCP credential. Keep writer identity separate from source provenance. Return both in an operation receipt, and preserve the necessary metadata through restart, backup, and restore. A source-session string is not proof of the writer's identity.
   182	
   183	Scope retry keys to the authenticated writer and operation. Repeating a request after a lost response must resolve its previous outcome rather than append another fact or proposal. Receipts distinguish committed, unchanged, pending, rejected, conflict, and unknown outcomes. Partial acceptance must identify the accepted and rejected changes. A successful native call or spawned reviewer does not alone prove that the requested fact was saved.
   184	
   185	All writers, including native reviewers, must preserve other committed changes. Use native read-modify-write within the same lock, or revision checks with safe conflict handling. A mutex around only the provider or MCP cannot govern a direct native writer. Test content and metadata publication, interrupted operations, archive creation, related-link updates, guarded deletion, and live versus stale locks before enabling ownership.
   186	
   187	Before sharing, verify restricted SSH execution, server-bound client policy, separate proposal creation and approval grants, and revocation of active connections. Provider discovery, profile roots, skill learning, schema checks, and update or restore behavior remain required ownership tests. A backup must include the authoritative records and required status, identity, policy, and pending-operation metadata consistently with active writers.
   188	
   189	## Preferences page
   190	
   191	| Proposed control | User-visible purpose |
   192	| --- | --- |
   193	| Use LifeOS for lasting memory, recommended | Hermes and connected agents remember facts and preferences in LifeOS. Hermes keeps conversation history separately. |
   194	| Keep the current memory setup | Preserve separate stores and explain that facts saved in one may not appear in the other. |
   195	| Memory health | Show whether recall and saving work, and explain failures. |
   196	| Share memory with other agents | Enable optional MCP connection setup. Remote sharing starts disabled. |
   197	| Client permissions | Show and configure each client's permitted read and write categories. |
   198	| Automatic memory review | Configure the LifeOS review cadence and model through the existing model-routing choices. |
   199	| Review existing Hermes memory | Preview an optional import and resolve conflicts before changing ownership. |
   200	| Restore previous configuration | Restore memory settings without deleting LifeOS records. |
   201	
   202	These controls are a design proposal, not available page actions. Keep normal setup understandable without knowledge of Cortex, provider internals, or SSH commands.
   203	
   204	## Implementation order and acceptance evidence
   205	
   206	1. Map the actual `.212` reads, writes, reviewers, and context injection. Use synthetic data to measure duplication and stale recall.
   207	2. Define the shared access contract and implement the provider against disposable LifeOS roots. Preserve hook behavior and establish one automatic recall owner.
   208	3. Verify remembering, correcting, forgetting, review behavior, skill learning, and failure reporting before disabling built-in durable writes in a test profile.
   209	4. Add optional MCP access and authenticate client policies. Prove that Hermes and another agent can exchange an allowed fact through the same store.
   210	5. Test restarts, concurrent clients, child tasks, scheduled runs, and public-channel delivery restrictions. Test rejected writes and interrupted operations.
   211	6. Add the preferences controls and a clean installation test. Verify that the installation works independently of `.211` and `.213`.
   212	7. Test plugin and LifeOS update transactions, backup and restore, and configuration rollback while preserving synthetic memory. Treat importing existing Hermes memory as a separate, optional feature.
   213	
   214	Save commands, revisions, raw results, and expected outcomes for each acceptance case. Enable the recommended default only when the supported compatibility set passes these checks. Memory integration does not close or relax a hook parity gap.
   215	
   216	## Questions to resolve during implementation
   217	
   218	- Can the supported Hermes version disable both built-in stores while retaining provider tools and independent skill learning?
   219	- Which LifeOS operations correctly implement corrections and forgetting? What approval and retention rules apply?
   220	- How do native memory hooks, the provider, and rendered context avoid duplicate or stale records across an existing session?
   221	- Which locking, retry, and write-identity guarantees does LifeOS already provide?
   222	- How should optional MCP support be packaged and versioned with plugin and LifeOS updates?
   223	- Which client classes and delivery restrictions should a fresh installation offer by default?
   224	- Which failure cases can preserve conversation progress, and which must block under existing LifeOS hook rules?
   225	
   226	## Evidence and limits
   227	
   228	The 2026-09-30 inspection found built-in memory and profile enabled on `.212`. Its installed `lifeos` plugin is a tool guard. `MemoryTurnStart.hook.ts` contains hot-memory injection and task retrieval; `MemoryReviewFire.hook.ts` owns reviewer cadence. These code observations do not prove duplicate writes or successful reviewer operation.
   229	
   230	The existing `.211` memory MCP returned `integrity_error` during the discussion. The cause was not established. Use it as a failure-handling example, not a diagnosis of `.212` or a dependency of this design.
   231	
   232	Hermes documents its [memory-provider interface](https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin) and [built-in memory controls](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory#configuration). Verify both against the plugin's pinned host version. Documentation for current upstream does not prove support in the pinned fixture.
   233	
   234	## Pinned source inspection for this resolution
   235	
   236	The primary agent inspected source on `.212` at Hermes revision `a01564231eb587a28ceca75f7ad6fe8d2fba4b04`. The [source excerpts and hashes](../docs/verification/2026-09-30-memory-design/pinned-source-excerpts.txt) contain code only, with no memory records.
   237	
   238	- `get_builtin_memory_store_flags` separately reads `memory.memory_enabled` and `memory.user_profile_enabled`. Agent initialization loads the external provider independently of those flags. This supports the proposed configuration; a live disposable-profile test must still confirm tools, prompts, background review, and failure paths.
   239	- The external provider contract supplies tool schemas, tool dispatch, session lifecycle, and configuration fields. The memory toolset must remain enabled so the provider's tools are visible.
   240	- Hermes background review can retain skill tools when built-in memory is off. It is not necessary to disable all skill learning to stop duplicate fact extraction.
   241	- Native `MemoryTurnStart` performs gated hot-memory injection and task retrieval. Native `MemoryReviewFire` owns review cadence. Keep them; provider recall and extraction should not duplicate their work.
   242	- Native `MemorySystem` supports hot-memory `op:set` curation through `MemoryWriter`, in addition to append-style additions. Correction and forgetting therefore have a native starting point; a new append-only archive is not the answer.
   243	- `MemoryWriter` locks and atomically publishes each hot-memory file write. `MemorySystem.addMemoryItem` reads entries before submitting the new list. The inspected writer options have no expected-revision argument. File-write atomicity alone does not establish safe multi-client correction or prevent stale-list replacement. Verify this with concurrent native reviewers and MCP clients before enabling shared writes.
   244	
   245	The design choice is resolved. Native operation details, privacy enforcement across hook injection and delivery, concurrent updates, and record-level correction remain implementation acceptance work. Do not enable the new default until those tests pass. This record does not authorize a live migration or relax the existing hook completion gate.
