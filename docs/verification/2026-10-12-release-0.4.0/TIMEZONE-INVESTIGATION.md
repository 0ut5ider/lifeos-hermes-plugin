# 2026-10-12: Integration fixture timezone mismatch

The corrected archive first passes 624 of 625 checks.
The failed Conduit assertion expects the last pending work slug after two captures.
The direct fixture forces UTC. The governed fixture inherits the runner timezone.
The first capture writes 2026-10-13.jsonl under UTC.
The second capture writes 2026-10-12.jsonl under Toronto time.
Both captures contain the correct expected synthetic events.
The fixture sorts day filenames and reads the UTC file last.

The real-process diagnostic repeats both settings against the exact corrected archive.
Mixed UTC and Toronto settings reproduce the same assertion failure.
Uniform UTC settings pass the assertion and preserve event order in one day file.
The release integration runner now supplies TZ=UTC to all test processes.
The official Hermes runner already uses UTC.
The archive, product programs, assertions, and test scope remain unchanged.
The complete suite is repeated with the corrected environment.
The first failing receipt remains under integration-sealed-a87e7ae9-mixed-timezone.*.
