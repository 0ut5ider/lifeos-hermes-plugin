# SessionEnd documentation integrity effect

Date: 2026-09-27

On isolated `.212`, the bridge dispatched the installed `DocIntegrity.hook.ts` at SessionEnd with a disposable LifeOS root and no inventory document. The native `MemoryDirIntegrity` handler emitted one `doc.integrity.memory_dir` finding to the temporary `MEMORY/STATE/events.jsonl`. The model-backed integrity pass was disabled, as it is by default on SessionEnd.

The probe did not demonstrate schema regeneration. `GenerateKnowledgeSchemaDoc.ts` derives its output from the account home directory rather than `LIFEOS_DIR`; the actual installed schema matched its render and retained a timestamp from before the probe. No live schema file was changed. A drift test would need stronger isolation before altering that target.
