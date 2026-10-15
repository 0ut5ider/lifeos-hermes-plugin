# Bind checkpoint work to the current owner and frozen view

2026-10-15, LifeOS 0.6.0 deployment. The first development checkpoint refuses before service draining. The operator assumes UID 1000. Development uses UID 1008; daily uses UID 1000. The existing baseline operator already uses the current UID and passes on both servers. The corrected checkpoint operator uses os.getuid() in the guest. Its actual development service drain then passes.

The development guest contains about 166 GiB of used space. Keeping its services stopped during the full off-server copy would cause unnecessary downtime. The installed Proxmox LXC backup source creates and mounts the native vzdump snapshot before copying. The actual snapshot creation follows the checkpoint admission, and its GUID is recorded. After these checks, the owner service controller resumes the live services while the backup continues reading the frozen view. The completed off-server backup remains a prerequisite for release application.

Both actual owner release reviews report native_mount_required false. The native LifeOS program files already match the qualified 0.6.0 package. The update therefore preserves the existing seven-file owner mount instead of generating another mount. Verification binds each current mount journal to its pre-update digest. This result changes the copied restore operator assumption that every complete release needs a new native mount.

The initial refusal, snapshot resume, owner reviews, and current verification state are retained in docs/verification/2026-10-15-release-0.6.0-deployment/. No product package changes occur in these corrections.

Before the update, development already shows Gateway Status: Stopped in the dashboard. Native runtime metadata reports the same live systemd PID, a 30-second heartbeat, gateway_state running, and Discord connected. The strict PID-file lookup returns no PID. This is a measured pre-existing status discrepancy. Its cause is not established. Updated gateway verification checks actual process identity, heartbeat, and adapter connection, and records the strict PID-file result separately.
