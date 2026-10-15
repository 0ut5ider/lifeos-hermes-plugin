# Managed Python loses dependencies in a direct child

2026-10-15, disposable guest 192.168.8.244, checkpoint 5ef88e93.

The installed browser activation preparation stops after creating its private backup. An authenticated read-only ownership preview passes from the package venv. A diagnostic detached preparation also passes from that venv. The browser apply then stops before the ownership journal exists. Those results rule out a failed archive or corrupt backup as the measured cause.

The dashboard uses the package manager's Python 3.14 interpreter. Hermes adds its dependency generation during bootstrap. The route helper starts another isolated interpreter directly and adds only the Hermes source path. That child cannot import `dotenv` or `ruamel`. The installed runtime regression returns FAIL with `route_child_missing_dotenv: true`. This explains both the browser preparation and apply failures without changing memory or model routing.

The correction uses `hermes_cli._launchers.runtime_command` for the route child. The helper retains isolated execution, the exact selected profile, and configuration checks before and after resolution. Existing route and permission controls and the installed runtime regression must pass before this correction is accepted. No production server changes.
