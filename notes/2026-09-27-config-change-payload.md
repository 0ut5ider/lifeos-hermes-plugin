# ConfigChange payload mismatch

Date: 2026-09-27

The first idle ConfigChange probe on the isolated `.212` account reported no changed filename in LifeOS's audit log. The bridge had fired the hook. The native `EventLogger.hook.ts` reads `config_path`, while the [Claude Code hook reference](https://code.claude.com/docs/en/hooks) documents `file_path` for ConfigChange. When `config_path` is absent, LifeOS logs the fallback string `settings.json`.

The bridge now sends both fields with the same absolute path. A second probe changed a synthetic project `settings.local.json` while no prompt or tool call was running. The installed logger recorded that filename within one watcher interval. The fixture was temporary and contained no personal LifeOS data.
