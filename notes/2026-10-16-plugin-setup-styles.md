# 2026-10-16: Plugin setup controls lost their visual boundary

Adrian reported that setup actions looked like body text. The running development dashboard confirms the problem. The enabled HTTP review, import review, reverse export review, and pending change review buttons each have a transparent background, a zero-width border, and zero padding. The page loads no LifeOS stylesheet. Both plugin manifests omit the optional `css` asset, although the current Hermes plugin loader supports that field.

The problem extends beyond button spacing. Existing utility classes depend on the host build, and older theme variables do not match the current host. Browser measurements show that `--primary`, `--primary-foreground`, and `--border` are absent. The host's `--foreground` resolves to transparent. Current `--color-*` variables exist. Adding more utility classes would retain the dependency on an unrelated host build.

The selected change gives each plugin a scoped stylesheet through the supported manifest field. It also separates forms, approvals, routine settings, and recovery controls. Verification must use the running compiled Hermes host, inspect actual computed styles, and preserve every existing action and policy boundary. A temporary browser preview changes no installed release. Production still requires a qualified release.
