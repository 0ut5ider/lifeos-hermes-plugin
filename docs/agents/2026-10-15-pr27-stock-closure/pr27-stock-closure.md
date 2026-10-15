# PR27 stock verifier closure

Date: 2026-10-15

Role: Independent stock provenance closure reviewer

Question: Does the corrected stock verifier reject extra executable source and admit only the exact stock and dashboard archive contents?

Model: gpt-6.1-sol, high reasoning effort

## Verdict

CLEAR for the narrow stock verifier correction. The previous P2 finding is resolved. I found no new actionable issue in this change.

The previous product, qualification closure, and preparation reviews remain separate checkpoints. The exact product program remains `04efe633296eb2b1a1d95561ca6d3e9516cd47dc`, archive SHA-256 `a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813`.

This closure does not establish development acceptance, complete certificate controls, public installation acceptance, or production qualification.

## Original finding and response

The previous verifier compared each archived source file but ignored extra runtime programs. My original exact-archive reproduction added a benign `sitecustomize.py` while leaving all 18,243 archived files unchanged. The validator accepted the modified runtime. A separate Python startup with that runtime on PYTHONPATH executed the extra module.

The primary reproduced the issue and retained the red controls in `stock-source-controls-before.json`. Four of six controls exposed missing refusal: extra startup source, extra link, extra bytecode, and altered dashboard files.

The corrected verifier now:

1. Requires the exact stock source archive SHA-256 and upstream identity.
2. Requires the exact dashboard archive SHA-256.
3. Checks every admitted regular file's bytes and every admitted link's target.
4. Builds the admitted file and link path set from both archives.
5. Walks the entire actual runtime without following directory links.
6. Rejects special files and requires the actual path set to equal the admitted path set.
7. Retains the checks that no manager, native installation, or integration receipt exists.

This addresses the original omitted-extra-program case and the separate frontend omission. Empty extra directories do not contain executable bytes and are not admitted as files or links. An extra directory link is included in the actual path set and refuses.

Reviewed source and control hashes are recorded in `reviewed-source-identities.json`. They remain unchanged when this report is written.

## Independent verification

I reran the actual six archive controls in an isolated review copy with the real immutable source and frontend archives. All six pass:

- Exact source plus exact frontend archives are accepted.
- Extra startup source refuses.
- Extra symlink refuses.
- Extra bytecode refuses.
- Altered stock source refuses.
- Altered dashboard refuses.

I added three independent controls using the actual current verifier's validation prefix. All three pass:

- The original benign `sitecustomize.py` case now refuses at `assert actual==expected`. The separate local Python startup still executes its harmless environment marker, so the original risk is reproduced while the acceptance path correctly refuses it.
- An extra directory symlink refuses at the complete path-set check.
- An extra FIFO refuses at the regular-file-or-link type check. The validator does not try to read the FIFO.

Each independent case first verifies 18,243 archived source files and 66 archived dashboard files. The refusal is therefore the intended full-set or special-file guard, not a missing archive, frontend, or setup failure.

Total independent closure results: **nine passing controls**. No test creates a guest acceptance receipt, release certificate, or substitute completion evidence.

Commands, from the project root:

```text
python docs/agents/2026-10-15-pr27-stock-closure/actual-controls/check_stock_source_controls.py
python docs/agents/2026-10-15-pr27-stock-closure/probe_stock_closure.py
```

The first command's local input copy is retained in `actual-controls.tar.gz`. Extract that review archive before repeating the command.

## Scope and pending state

The primary reports that development operation `86340dd2f6f8473280cc411f5a3e4102` actually rolled back during native Mount preparation and that all three services are active. This stock verifier closure does not investigate or qualify that application failure. Development acceptance and the certificate remain pending. The primary continues the measured repair workflow.

The corrected verifier still reports `public_installation_verified: false`. Its stock source proof is a prerequisite for public installation replay, not that replay's completion.

I made no remote or memory call, read no credential, private map, personal record, or raw narration, and changed no operator or product code. I performed no Git mutation. The only code execution used isolated local archive extractions and validator statements. The benign startup probe only sets an environment marker in its own child process.

## Review history and unresolved objections

Previous report: `docs/agents/2026-10-14-pr27-final-qualification-review/pr27-final-qualification-review.md`.

Previous finding: extra executable stock source is not rejected.

Primary response: exact source and frontend admission plus actual full path-set and special-file checks.

Closure: independently verified. No unresolved objection remains for this narrow finding.

## Artifacts

- `reviewed-source-identities.json`: exact verifier, control, and metadata hashes.
- `actual-controls.tar.gz`: exact local control sources and safe metadata input copy.
- `actual-controls.stdout` and `actual-controls.stderr`: actual six-control output.
- `probe_stock_closure.py`: three independent controls including the original startup reproduction.
- `independent-stock-closure.json`, `.stdout`, and `.stderr`: complete independent results and refusal locations.
