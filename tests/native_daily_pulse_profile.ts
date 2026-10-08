// ABOUTME: Loads the staged daily profile through the native Pulse configuration merger.
// ABOUTME: Executes its selected script jobs through the same native process collector as the daemon.
import { join } from "node:path";

const [source, userPath, jobName] = process.argv.slice(2);
if (!source || !userPath) throw new Error("Choose a native source and a staged user profile");
const { loadConfig, parseConfigToml, resolveModules, spawnScript } = await import(join(source, "LIFEOS/PULSE/lib.ts"));
const systemPath = join(source, "LIFEOS/PULSE");
const config = await loadConfig(systemPath, userPath);
if (jobName) {
  const job = config.jobs.find((entry: { name: string }) => entry.name === jobName);
  if (!job || !job.enabled || job.type !== "script" || !job.command) {
    throw new Error("Choose an enabled script job");
  }
  const output = await spawnScript(job.command, job.timeout_ms);
  console.log(JSON.stringify({ name: job.name, output }));
} else {
  const system = parseConfigToml(await Bun.file(join(systemPath, "PULSE.toml")).text());
  console.log(JSON.stringify({ modules: resolveModules(system, config.userParsed), jobs: config.jobs }));
}
