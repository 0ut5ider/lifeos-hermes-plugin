# 2026-09-27: Hermes Git installer accepts the plugin package

The isolated `.212` account cannot reach the public download hosts. A first installer probe used a new temporary Hermes home and a local Git clone. Hermes cloned the package and scanned it, but its package manager could not download the Python runtime for that new home. The failure was independent of the plugin layout.

The scan classified the package as `CAUTION`. It found the bridge's expected child process execution and several matches in test files and notes about synthetic approval cases. The scan did not classify the package as dangerous. A noninteractive install stopped at the caution consent step.

A second probe used the existing isolated Hermes profile with a temporary plugin name in a local Git commit. It supplied the full commit ID, `--no-enable`, `--no-deps`, and `--force` after review of the caution findings. Hermes installed the package as a disabled plugin. `hermes plugins remove` then removed the probe directory. The active LifeOS bridge was not replaced. This verifies the Git package and scan path, not a public GitHub download or runtime activation from the new install.

A third probe put only the runtime files in a Git subdirectory. Hermes installed that subdirectory with a safe scan verdict and no `--force`, again under a disabled probe name. The probe was removed. The public repository now keeps runtime files in `lifeos_hook_bridge/` and directs installs to that subdirectory.
