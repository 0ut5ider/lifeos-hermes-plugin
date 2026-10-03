# Memory host ownership review

Date: 2026-09-30

Role: Independent bounded code and behavior reviewer

Question: Do the new real-host tests accurately characterize provider selection, explicit built-in memory flags, disabled tool writes, unavailable provider behavior, and configuration restoration?

Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

The four current characterization tests pass independently. I found no material defect in their bounded assertions. They establish a useful prerequisite for ownership work: selecting LifeOS alone leaves the built-in stores active, while explicitly disabling both built-in flags removes their prompt blocks and memory tool and refuses the tested writes. This conclusion does not establish an ownership activation transaction.

Reviewed repository HEAD: `01052f0ecd34e8e959fd4e639ff7ced94c62f921` on `feature/lifeos-memory`. The only implementation-unit changes at snapshot were the two untracked test files. I changed no implementation, committed nothing, and used no live account, memory, journal, SSH, or live Hermes import.

## Scope and evidence

I reviewed `tests/memory_host_calls.py` and `tests/test_memory_host.py`, including the final unavailable-provider test and its logging capture. I inspected the corresponding initialization, system-prompt, memory-tool, and memory-store code in the owned app-startup host source. I loaded the coding-rules skill.

The test runs a real `AIAgent` constructor in a subprocess. It installs a copy of the plugin under a private profile, supplies a private HOME and HERMES_HOME, and builds the real system prompt. The memory files contain only synthetic markers. The selected model endpoint is a real localhost fixture. Neither the host constructor nor the tool functions are mocked.

| Independent test | Verified outcome |
| --- | --- |
| Provider selection alone | Both built-in flags remain true, the built-in store exists, both file markers enter the prompt, and the LifeOS provider is selected. |
| Both explicit flags false | No built-in store, no built-in memory tool, neither file marker in the prompt, LifeOS remember/forget tools and skill_manage present. Four direct memory-tool add attempts are refused across both targets and both absent/store-loaded cases. |
| Configuration A to B to A | Fresh processes restore the built-in flags, memory tool, skill_manage, and both original prompt markers after removing the provider selection and explicit false flags. |
| LifeOS provider unavailable | Disabling ownership in the isolated LifeOS configuration produces a captured host warning. No provider, built-in store, built-in memory tool, LifeOS remember tool, or built-in marker reappears. skill_manage remains present. |

All initial synthetic MEMORY.md and USER.md bytes remain identical after every constructor call. Every request received by the localhost endpoint is asserted to be `/api/show` with exactly `{"name":"synthetic-model"}`. This validates that these observed requests contain no prompt or memory marker and are capability probes, not model-generation requests. The test allows zero probes and does not instrument arbitrary other network destinations; I do not infer a general network isolation guarantee from that assertion.

Independent command:

```sh
LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/lifeos/LifeOS/install LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-app-startup/hermes /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest discover -s tests -p test_memory_host.py -v
```

Result: **4 tests passed in 20.648 seconds**, no failures or skips. Full independent stdout/stderr is in `raw/tests.txt`. Source hashes and byte snapshots are in `raw/source-hashes.json` and adjacent files. The post-test check found no drift in the original snapshot files.

## Interpretation and remaining limits

- The disabled-write tests call the real `memory_tool` for `add` on both targets. The host checks target permission before operation dispatch, which supports the intended denial path. These tests do not independently exercise replace, remove, batch, pending approvals, or every other host writer.
- `load_on_disk_store()` still reads preserved file contents into a store object. The disabled flags control prompt inclusion and the tested tool admission, not operating-system access to those bytes. No filesystem isolation claim follows from these tests.
- Restoration means a new process with restored memory configuration. The test does not disable the installed plugin or reset the separate LifeOS ownership configuration. It is not a proof that every plugin hook and admission guard has been returned to a built-in-only lifecycle.
- `skill_manage` remains advertised. The test does not execute skill creation or prove learning completion. The reported skill nudge interval is collected but not asserted.
- `skip_context_files=True` and `skip_background_review=True` deliberately isolate this constructor characterization. Arbitrary workspace context files, background review, retained conversations, compression rotation, and final delivery are outside it.
- There is no full model turn, write through the LifeOS provider, automatic repair, ownership transaction, installer recovery, or fresh ownership activation in this unit.

## Fixture revision and provenance

The parent added the fourth test during review. The final helper captures the actual run_agent warning through a logging handler, then the parent test checks the warning field. Clean controls reject unexpected warnings and require empty stderr. This correctly avoids assuming that the host has a default stderr handler.

The parent's earlier unavailable-provider fixture output is preserved as `raw/primary-memory-host-unavailable.txt` when present. It is historical fixture evidence, not an independent failure of the final snapshot. The parent's final output is saved separately when present and is not counted as my independent test run.

## Review priorities for Adrian

The main decision is the eventual ownership transaction: it must coordinate both explicit host flags with separate LifeOS ownership state and restart or invalidate retained sessions as required. This review supplies constructor-level evidence for that future work. It does not authorize activation or close the broader lifecycle and source inventory gates. No external system or configuration changed during this review; all runtime changes were disposable synthetic fixtures.
