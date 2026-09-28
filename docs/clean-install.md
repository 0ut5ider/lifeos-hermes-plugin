# Clean install with separate LifeOS and Hermes roots

This sequence was exercised on a separate `.212` Unix account on 2026-09-28. It installs LifeOS under `~/.claude` and Hermes under `~/.hermes`. It does not copy an existing LifeOS user tree. Use the patch order in [README.md](../README.md) before these commands. The patches target the base commits named there. Check each patch with `git apply --check` on your exact checkout.

Run the commands as the new account from its own home directory. Install Bun first and keep it on `PATH`. Set `LIFEOS_SRC` and `HERMES_SRC` to the two patched source checkouts:

```sh
cd "$HOME"
export LIFEOS_SRC="$HOME/workspace/LifeOS"
export HERMES_SRC="$HOME/workspace/hermes-agent"
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
  --ref <full-commit-id> --no-enable
"$HERMES_SRC/.hermes/bin/hermes" plugins enable lifeos-hook-bridge
"$HERMES_SRC/.hermes/bin/hermes" plugins validate \
  "$HOME/.hermes/plugins/lifeos-hook-bridge"
```

Start Hermes from a directory that the account can read. The first clean prompt-hook probe inherited `/home/outsider` as its working directory and all 14 native hook starts failed with permission denied. The same probe from the new account's home returned hook context and created a transcript. Run a native hook test before you configure Discord or start a long-running gateway.

The clean probe verified the mount, plugin installation, registration, and prompt hooks. It did not test a model call because the account had no model credentials. The tested `.212` service account uses the local model and verified a selected-provider child inference call separately. See [the probe record](../notes/2026-09-28-clean-install-probe.md).

## Carrier probe after model setup

Set the Hermes main-loop model and effort to the LifeOS top tier. Select the Fable route in the LifeOS Bridge settings page. Run `hermes --run-file ~/.hermes/plugins/lifeos-hook-bridge/carrier_probe.py --run` after configuring the model and again whenever you change the Fable route. The command creates one real delegated child call and stores its evidence under `~/.claude/LIFEOS/MEMORY/STATE/`. IntegrityCheck rejects evidence older than 30 days. The clean account without model credentials cannot run this probe. The configured `.212` account passed it with the local model.
