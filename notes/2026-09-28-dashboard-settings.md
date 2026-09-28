# LifeOS settings needed a dashboard extension

Date: 2026-09-28. The `.212` Hermes Plugins page showed `lifeos-hook-bridge` enabled and said "No dashboard tab." It offered no Settings action. The bridge's `plugin.yaml` already declared nine `config_schema` fields, but that schema drives Hermes's Desktop settings form, not this web dashboard's Plugins page. The README incorrectly directed users to a settings action there.

The plugin now ships a dashboard manifest, a small React UI using Hermes's plugin SDK, and an authenticated FastAPI route. The API calls Hermes's `plugin_settings_fields` and `save_plugin_settings`, so it reads and writes the same `plugins.entries.lifeos-hook-bridge.settings` values that the gateway uses. The page tells users to restart the gateway after saving.

On `.212`, the dashboard mounted `/api/plugins/lifeos-hook-bridge/`, discovered the `/lifeos-bridge` tab, and read all nine fields. An invalid effort returned HTTP 400. Saving `haiku_effort=low` and reading it back succeeded. An unauthenticated HTTP request returned 401. `hermes plugins validate` passed with no warnings. The browser UI itself was not visually checked because the collaborative browser was unavailable in this session; Adrian can inspect it after refreshing the dashboard.
