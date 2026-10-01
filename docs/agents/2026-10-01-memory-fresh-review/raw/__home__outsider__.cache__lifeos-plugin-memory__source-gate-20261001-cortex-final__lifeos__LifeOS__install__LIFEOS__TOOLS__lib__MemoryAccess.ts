// ABOUTME: Delegates native memory operations to an optional governed local service.
// ABOUTME: Retains reviewer snapshot revisions and refuses invalid service responses.

import { lstatSync, readFileSync, realpathSync } from "node:fs";
import { homedir } from "node:os";
import { isAbsolute, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const revisions = new Map<string, string>();

export function memoryObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function hasMemoryAccess(): boolean {
  if (process.env.LIFEOS_MEMORY_INTERNAL === "1") return false;
  try {
    lstatSync(resolve(homedir(), ".claude/LIFEOS/USER/CONFIG/memory-access.json"));
    return true;
  } catch (error: unknown) {
    if (memoryObject(error) && error.code === "ENOENT") return false;
    throw error;
  }
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


export function readMemorySource(path: string): string {
  const governed = memoryAccess("read_source", {path: resolve(path)},
    (value): value is Record<string, unknown> => memoryObject(value) && typeof value.ok === "boolean");
  if (governed === undefined) return readFileSync(path, "utf8");
  if (governed.ok !== true || typeof governed.content !== "string" || governed.excluded !== false) {
    throw new Error("The retained native source is excluded or unavailable");
  }
  return governed.content;
}

export function readMemoryDiagnostic(path: string): string {
  const governed = memoryAccess("read_diagnostic", {path: resolve(path)},
    (value): value is Record<string, unknown> => memoryObject(value) && typeof value.ok === "boolean");
  if (governed === undefined) return readFileSync(path, "utf8");
  if (governed.ok !== true || typeof governed.content !== "string" || governed.excluded !== false) {
    throw new Error("Memory diagnostics are unavailable under the current policy");
  }
  return governed.content;
}

export function checkMemoryDiagnostic(path: string, report = false): void {
  const governed = memoryAccess(report ? "check_diagnostic_report" : "check_diagnostic", {path: resolve(path)},
    (value): value is Record<string, unknown> => memoryObject(value) && typeof value.ok === "boolean");
  if (governed !== undefined && governed.ok !== true) {
    throw new Error("Memory diagnostics are unavailable under the current policy");
  }
}

export function canReadMemoryDiagnostics(root: string): boolean {
  try {
    if (!canReadMemorySources()) return false;
    return !hasMemoryAccess() || realpathSync(root) === realpathSync(resolve(homedir(), ".claude"));
  } catch {
    return false;
  }
}

interface HotMemoryDiagnostic {
  dropped_invalid: Array<{entry: string; reason: "malformed" | "overlength"}>;
}

export function diagnoseMemoryFile(path: string): HotMemoryDiagnostic | undefined {
  const response = memoryAccess("diagnose_hot", {path: resolve(path)},
    (value): value is Record<string, unknown> => memoryObject(value) && typeof value.ok === "boolean");
  if (response === undefined) return undefined;
  const valid = (value: unknown): value is HotMemoryDiagnostic => memoryObject(value)
    && Array.isArray(value.dropped_invalid) && value.dropped_invalid.every(row => memoryObject(row)
      && typeof row.entry === "string" && (row.reason === "malformed" || row.reason === "overlength"));
  if (response.ok !== true || !valid(response)) throw new Error("Hot-memory diagnostics are unavailable under the current policy");
  return response;
}

function sameDiagnosticShape(value: unknown, source: unknown): boolean {
  if (Array.isArray(source)) {
    return Array.isArray(value) && value.length === source.length
      && source.every((item, index) => sameDiagnosticShape(value[index], item));
  }
  if (memoryObject(source)) {
    return memoryObject(value) && Object.keys(value).length === Object.keys(source).length
      && Object.entries(source).every(([key, item]) => Object.hasOwn(value, key) && sameDiagnosticShape(value[key], item));
  }
  return source === null ? value === null : typeof value === typeof source;
}

export function filterMemoryDiagnostic<T>(report: T, timestamp: string): T {
  const content = JSON.stringify(report);
  const governed = memoryAccess("filter_diagnostic", {content, timestamp},
    (value): value is Record<string, unknown> => memoryObject(value) && typeof value.ok === "boolean");
  if (governed === undefined) return report;
  if (governed.ok !== true || typeof governed.content !== "string") {
    throw new Error("Memory diagnostic details are unavailable under the current policy");
  }
  const filtered: unknown = JSON.parse(governed.content);
  const source: unknown = JSON.parse(content);
  const valid = (value: unknown): value is T => sameDiagnosticShape(value, source);
  if (!valid(filtered)) throw new Error("The native diagnostic service returned an invalid result");
  return filtered;
}


export function filterMemorySource(content: string, timestamp: string): string | null {
  const governed = memoryAccess("filter_source", {content, timestamp},
    (value): value is Record<string, unknown> => memoryObject(value) && typeof value.content === "string" && typeof value.excluded === "boolean");
  if (governed === undefined) return content;
  return governed.excluded ? null : String(governed.content);
}


export function checkMemorySource(path: string): void {
  const governed = memoryAccess("check_source", {path: resolve(path)},
    (value): value is Record<string, unknown> => memoryObject(value) && typeof value.ok === "boolean");
  if (governed !== undefined && governed.ok !== true) throw new Error("The native source path is excluded or unavailable");
}


export function canReadMemorySources(): boolean {
  try {
    if (!hasMemoryAccess()) return true;
    const governed = memoryAccess("check_sources", {},
      (value): value is Record<string, unknown> => memoryObject(value) && typeof value.ok === "boolean");
    return governed?.ok === true;
  } catch {
    return false;
  }
}
