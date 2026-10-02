# Staged mount and authenticated remount acceptance

Date: 2026-10-02

## Publication and recovery

The native mount can write prepared outputs into a private staging directory. The plugin validates the prepared configuration before publication.

The plugin journals the previous contents, digests, and permissions for each target. It publishes the prompt, configuration, environment file, guard files, and optional VersionDrift baseline. It verifies the native mount and Hermes configuration before it records completion.

Recovery checks every target before it restores any target. A later edit causes recovery to stop. Recovery does not overwrite that edit.

A real process-kill test exposed an intermediate recovery state. Atomic restoration creates a file with mode 0600 before recovery restores its previous permissions. A second process can die in that interval. Recovery now accepts the original digest at mode 0600 only while its journal records restoration. It restores and synchronizes the previous permissions.

The focused recovery gate passes 23 cases without skips in `recovery-final.txt`. These cases use native Bun mounting, the actual Hermes configuration checker, real password sessions, and process kills. Systemd operations remain component boundaries in these tests.

## HTTP admission

Native PULSE remount requests use a fixed authenticated local Hermes route. The route uses the verified dashboard account and current installation owner binding. It accepts no account, path, or configuration override. Cross-origin requests are refused. Connector loss does not enable a raw mount fallback.

The plugin page shows `Restore interrupted mount` when the mount journal requires recovery. The owner can recover through that authenticated control.

## Verification limits

The earlier combined selection contains two incorrect module names in `combined.txt`. The corrected selection passes 76 cases with one skipped native TaskGovernance case in `combined-corrected.txt`. The full gate sets the required native hook path and must execute that case.

Live service and browser acceptance is the next gate. This document does not claim complete memory ownership setup, full PULSE interface governance, or the complete release gate. Ownership remains disabled on running installations.
