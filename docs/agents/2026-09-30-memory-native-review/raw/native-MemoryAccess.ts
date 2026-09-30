// ABOUTME: Delegates native memory operations to an optional governed local service.
// ABOUTME: Retains reviewer snapshot revisions and refuses invalid service responses.

import { existsSync, lstatSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { isAbsolute, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const revisions = new Map<string, string>();

export function memoryObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function hasMemoryAccess(): boolean {
  return process.env.LIFEOS_MEMORY_INTERNAL !== "1" && existsSync(resolve(homedir(), ".claude/LIFEOS/USER/CONFIG/memory-access.json"));
}

export function observedMemoryRevision(path: string): string {
  return revisions.get(resolve(path)) ?? "";
}

export function memoryAccess<T>(operation: string, arguments_: Record<string, unknown>,
                                valid: (value: unknown) => value is T): T | undefined {
  if (!hasMemoryAccess()) return undefined;
  const path = resolve(homedir(), ".claude/LIFEOS/USER/CONFIG/memory-access.json");
  const info = lstatSync(path);
  if (!info.isFile() || info.isSymbolicLink() || info.uid !== process.getuid?.() || (info.mode & 0o077) !== 0) {
    throw new Error("The native memory service configuration needs private owner permissions");
  }
  const configuration: unknown = JSON.parse(readFileSync(path, "utf8"));
  if (!memoryObject(configuration) || configuration.version !== 1 || !Array.isArray(configuration.command)) {
    throw new Error("Unsupported native memory service configuration");
  }
  const command: string[] = [];
  for (const argument of configuration.command) {
    if (typeof argument !== "string" || argument.length === 0) throw new Error("Invalid native memory service command");
    command.push(argument);
  }
  const executable = command.shift();
  if (!executable || !isAbsolute(executable)) throw new Error("The native memory service requires an absolute executable");
  const result = spawnSync(executable, command, {input: JSON.stringify({operation, arguments: arguments_}),
                                               encoding: "utf8", timeout: 40_000, maxBuffer: 4 * 1024 * 1024});
  if (result.error || result.status !== 0) throw new Error("The native memory service is unavailable");
  const response: unknown = JSON.parse(result.stdout);
  if (!valid(response)) throw new Error("The native memory service returned an invalid result");
  if (operation === "read" && memoryObject(response) && typeof response.revision === "string" && typeof arguments_.path === "string") {
    revisions.set(resolve(arguments_.path), response.revision);
  }
  return response;
}
