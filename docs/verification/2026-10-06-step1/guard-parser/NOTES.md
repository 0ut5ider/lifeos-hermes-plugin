# Literal shell path investigation

Date: 2026-10-06. Agent: Cerebo.

The first native matrix has one parser failure among 42 write-shape combinations. The failing shape is a Python `-c` argument produced by standard shell quoting. Seven forms, two content classes, and three zones make the failure reproducible. A separate control confirms that the allowed command changes the protected target to the deny token.

The initial bridge public-clean control also scans the wrong repository. Its caller supplies `cwd`, but the terminal callback derives its workspace from `workdir`. Using the real terminal argument fixes that fixture. This is separate from the native parser defect.

The literal correction decodes adjacent quote segments for path discovery. It leaves original command scanning intact. All 42 write-shape combinations then pass. The test also retains the existing indirect-content limit. A copy command can reference a separate file containing restricted content without exposing that content to this inline scanner.
