# Ownership requires three service boundaries

Date: 2026-10-05. The read-only check uses the active `lifeos-hermes` account on `.212` through its user systemd manager.

The gateway, dashboard, and `com.lifeos.pulse.service` are active. Their working directories use the Hermes profile, the account home, and the installed native PULSE directory. The gateway uses `KillMode=mixed`. The dashboard and native PULSE use `KillMode=control-group`.

A gateway stop alone does not establish a stopped profile. The ownership coordinator must bind and drain all three services and check any supported detached jobs before configuration changes. It must preserve which services were active, record stop intent before stopping, verify empty service control groups, and restore the selected services after recovery. Native PULSE depends on the authenticated Hermes endpoint, so service restart order also needs acceptance.

The configuration transaction now preserves exact prior settings without restoring native data. Its receipt reports that service verification remains incomplete. This distinction prevents a passing file transaction from becoming a false production activation claim. The raw service properties and command are in the ownership verification directory. No live service or configuration changes.

The shared-memory MCP remains unavailable with its integrity error. This measurement stays in the repository; no hidden memory records or alternate file access is used.
