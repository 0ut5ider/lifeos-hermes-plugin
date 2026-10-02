// ABOUTME: Exercises the installed LifeOS prompt renderer without a model or messaging adapter.
// ABOUTME: Returns native formatting and admission failures from a synthetic installation.
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
const input = JSON.parse(await Bun.stdin.text());
const module = await import(pathToFileURL(resolve(process.argv[2], "LIFEOS/HERMES/RenderSoul.ts")).href);
try {
  const result = input.declared ? module.renderSoulFromSources(input.sources, input.skills, input.options ?? {})
    : {soul: module.renderSoul(input.options ?? {}), constitution: module.renderConstitution(input.options ?? {}),
       identity: module.renderIdentity(), skillRouting: module.renderSkillRouting(),
       skills: module.skillIndex(), launcherName: module.daName()};
  process.stdout.write(JSON.stringify({ok: true, ...result}) + "\n");
} catch (error) {
  process.stdout.write(JSON.stringify({ok: false, message: String(error)}) + "\n");
}
