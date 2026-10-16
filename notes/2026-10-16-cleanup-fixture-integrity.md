# Environment flags do not preserve a Hermes fixture

During the October 16 code cleanup, I set `PYTHONDONTWRITEBYTECODE=1` for the frozen Python test runner. The extracted 0.7.2 program tree still acquired 519 files: 518 bytecode files and `.bytecode-fingerprint`. Hermes has an explicit checkout-fingerprint writer. I did not attribute every bytecode write to a specific child process, so the result supports a narrower conclusion: the environment setting does not keep this test fixture unchanged.

I compared the extracted tree with the immutable archive. All 21,170 archived regular files retained their contents and modes. The archive SHA-256 stayed `293cfa2c6593b597c327fb8ad11f458d3e374352552dfbe7f4dbba5cd7e67265`. Removing only the archive-unlisted generated files and 95 empty cache directories restored the regular-file map. Directory modification times remain changed.

Future source checks should use disposable copies of the program and dependency inputs, with file-map checks before and after. The shared archive and extracted qualification source should remain reference inputs. The [cleanup verification record](../docs/agents/2026-10-16-codebase-cleanup/codebase-cleanup.md) retains the failed initial integrity check, the bounded cleanup, and the passing final comparison.
