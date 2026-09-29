# Clean install with separate LifeOS and Hermes roots

This sequence was exercised on a separate `.212` Unix account on 2026-09-28. It installs LifeOS under `~/.claude` and Hermes under `~/.hermes`. It does not copy an existing LifeOS user tree. The patches target the base commits named in [README.md](../README.md).

Prepare both source trees from repositories that contain the pinned base revisions. Run this from the plugin repository:

```sh
python scripts/prepare_sources.py \
  --hermes-repo "$HOME/workspace/hermes-agent" \
  --lifeos-repo "$HOME/workspace/LifeOS" \
  --output "$HOME/workspace/lifeos-prepared"
```

The command checks each patch against the preceding result and publishes both trees only after all 26 patches pass. It refuses an existing output path and leaves the source repositories untouched. `source-manifest.json` records the base commits and patch hashes. This name matters: Hermes treats a parent `manifest.json` as a packaged PM runtime, so that name prevents source setup from starting. The prepared Git branches contain the applied patches as uncommitted changes for review. A real-source test on `.212` prepared both trees and passed `git diff --check` for each. This step prepares source code; it does not install LifeOS or Hermes into the account.

Run the commands as the new account from its own home directory. Install Bun first and keep it on `PATH`. Set `LIFEOS_SRC` and `HERMES_SRC` to the two patched source checkouts:

```sh
cd "$HOME"
export LIFEOS_SRC="$HOME/workspace/lifeos-prepared/lifeos"
export HERMES_SRC="$HOME/workspace/lifeos-prepared/hermes"
export PATH="$HOME/.local/bin:$PATH"

cd "$HERMES_SRC"
./setup-hermes.sh --runtime-only
mkdir -p "$HOME/.hermes"
cat > "$HOME/.hermes/config.yaml" <<'YAML'
model:
  default: probe-local
YAML

cd "$HOME"
mkdir -p "$HOME/.claude"
cp "$LIFEOS_SRC/LifeOS/install/CLAUDE.template.md" "$HOME/.claude/CLAUDE.md"
for tool in InstallSettings DeployCore ScaffoldUser LinkUser InstallHooks ActivateImports; do
  bun "$LIFEOS_SRC/LifeOS/Tools/$tool.ts" \
    --config-root "$HOME/.claude" \
    --skill-root "$LIFEOS_SRC/LifeOS" \
    --apply
done

export HERMES_HOME="$HOME/.hermes"
export HERMES_WORKSPACE="$HOME/workspace"
bun "$HOME/.claude/LIFEOS/HERMES/Mount.ts"
bun "$HOME/.claude/LIFEOS/HERMES/Mount.ts" --check
"$HERMES_SRC/.hermes/bin/hermes" config check
```

Replace `probe-local` with a model you have configured in Hermes before you run model calls. The runtime-only setup does not create `config.yaml`; `Mount.ts` needs a valid YAML file to patch. `--skill-root` must point to the inner `LifeOS` directory. Without it, `DeployCore` could not find the nested skill payload in the clean probe.

After the plugin branch is published, install a full 40-character commit ID from this repository:

```sh
"$HERMES_SRC/.hermes/bin/hermes" plugins install \
  0ut5ider/lifeos-hermes-plugin/lifeos_hook_bridge \
  --ref <full-commit-id> --no-deps --no-enable
"$HERMES_SRC/.hermes/bin/hermes" plugins enable lifeos-hook-bridge
"$HERMES_SRC/.hermes/bin/hermes" plugins validate \
  "$HOME/.hermes/plugins/lifeos-hook-bridge"
```

For a noninteractive install, `--no-deps --no-enable` first records the plugin without requesting dependency consent. `plugins enable` then installs the pinned dependencies and activates the plugin. A forced install of an existing active plugin without these steps was refused because dependency consent was unavailable; the installed plugin stayed unchanged. Back up and disable an existing plugin before replacing it, then use `--force --no-deps --no-enable` and enable the new version.

Start Hermes from a directory that the account can read. The first clean prompt-hook probe inherited `/home/outsider` as its working directory and all 14 native hook starts failed with permission denied. The same probe from the new account's home returned hook context and created a transcript. Run a native hook test before you configure Discord or start a long-running gateway.

The clean probe now also has a private LAN model configuration. Its prepared Hermes source accepted a real model call and returned `PATCHED-MODEL-212`. The account received only the model section of the `.212` test service configuration and the bridge's local model environment file; it received no LifeOS user data or Discord credentials. The prior configuration is at `~/.hermes/config.yaml.before-local-model-20260928`. The tested `.212` service account verified a selected-provider child inference call separately. See [the probe record](../notes/2026-09-28-clean-install-probe.md) and [the source manifest collision](../notes/2026-09-28-source-manifest-runtime-collision.md).

## Carrier probe after model setup

Set the Hermes main-loop model and effort to the LifeOS top tier. Select the Fable route in the LifeOS Bridge settings page. Run `hermes --run-file ~/.hermes/plugins/lifeos-hook-bridge/carrier_probe.py --run` after configuring the model and again whenever you change the Fable route. The command creates one real delegated child call and stores its evidence under `~/.claude/LIFEOS/MEMORY/STATE/`. IntegrityCheck rejects evidence older than 30 days. The clean account without model credentials cannot run this probe. The configured `.212` account passed it with the local model.
