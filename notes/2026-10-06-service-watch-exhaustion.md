# Service recovery under an exhausted inotify limit

Date: 2026-10-06. The broad regression run fails one originally-inactive service recovery control. Admission correctly refuses a service in `failed` state. A dedicated repeat reproduces the failure and records the actual systemd properties and journal. The stopped Pulse fixture has MainPID zero and result `timeout`. Its journal reports `No space left on device` when systemd tries to create control-group and memory watches.

The workstation has 138,625 visible inotify watches against a per-user limit of 138,629. One Zed remote server owns 138,522 watches. Disk usage is 71 percent, with 145 GB available. The ENOSPC message concerns watches, not disk space. Earlier speculation about a transient start-limit failure has no supporting evidence.

The next control uses the same service tests on the isolated development container and its separate user manager. This preserves the product's stable-state admission rule and the workstation editor. A successful repeat will establish that the service behavior works with the required manager resources available. It will not prove that every earlier manager refusal has the same cause.

Raw refusal data remains in `/home/outsider/.cache/lifeos-step1-20261006/service-state-trace/refusals.jsonl`. The earlier full run remains failed. No product change or kernel setting is made from this result.
