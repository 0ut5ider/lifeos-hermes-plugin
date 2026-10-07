# Batch and concurrent evaluation controls

Date: 2026-10-06. Target: isolated development accounts on `192.168.8.252`.

Two functional controls pass. The batch control applies two sentinel edits. The concurrency control applies four sentinel edits in parallel. Hermes dispatches its actual file tool and installed PostToolUse hooks. The native comparison applies the same file tool changes and sends the corresponding payloads to the actual native hooks. These controls do not claim native CLI batch dispatch.

Each side completes one evaluation through the real ConfigEvalOnChange, EvalRunner, and Inference programs. The child calls private FlashNext at medium effort and returns `PAIR_EVAL_READY`. The controls check the published score, trial output, changed files, hook count, valid fire state, and removed evaluation lock. All hook calls have empty stderr. [wire-proof.json](wire-proof.json) retains verified request and response hashes for four actual inference calls. Full wire bodies stay private on the development server.

Sixteen concurrent native hook processes expose a shared temporary-file race. Fifteen produce an `ENOENT` rename error before the correction. [evaluation-publication-before.json](evaluation-publication-before.json) retains those errors. The patch uses a process identifier and random UUID for each temporary file, creates it exclusively, and retains the atomic rename. [evaluation-publication-after.json](evaluation-publication-after.json) records all sixteen processes with empty output and zero exit status. This unit control measures state publication; its terminating runner supplies no model evidence.

Earlier real operation runs remain on the development server. One uses a native executable that the fixture user cannot traverse. A later run has extra relay requests with broken-pipe errors. Another completes the evaluations but exposes the native rename race. Those runs remain failed. The final source-bound repeat has none of those errors.

The native executable copy has the same bytes as the pinned `2.1.272` executable. [source-identity.json](source-identity.json) binds its digest, native source programs, plugin files, and frozen runners. The final source contains eleven Hermes patch groups and fifteen LifeOS patches. These controls complete the batch and concurrent evaluation scenarios; they do not complete unrelated file-effect groups.
