// ABOUTME: Records an exact native write destination before a governed upgrade publishes it.
// ABOUTME: Flushes private recovery metadata without scanning or deleting unrelated files.
import { closeSync, existsSync, fsyncSync, lstatSync, openSync, readFileSync, realpathSync, renameSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, relative, resolve } from "node:path";
import { randomUUID } from "node:crypto";

function object(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function observePublication(root: string, journal: string, destination: string): void {
  const expected = resolve(root, "LIFEOS/MEMORY/STATE/memory-operation.json");
  const info = lstatSync(journal);
  if (resolve(journal) !== expected || !info.isFile() || info.isSymbolicLink()
      || info.uid !== process.getuid?.() || (info.mode & 0o077) !== 0) {
    throw new Error("The native publication journal needs the fixed private owner path");
  }
  const path = resolve(destination);
  const parent = realpathSync(dirname(path));
  const upgrades = realpathSync(resolve(root, "LIFEOS/MEMORY/UPGRADES"));
  const user = realpathSync(resolve(root, "../.config/LIFEOS/USER"));
  if (!upgrades.startsWith(user + "/")) throw new Error("The upgrade store leaves native user data");
  if (!parent.startsWith(upgrades + "/") && parent !== upgrades) {
    throw new Error("The upgrade publication leaves its governed store");
  }
  if (existsSync(path) && lstatSync(path).isSymbolicLink()) throw new Error("Upgrade publication must not follow a file symlink");
  const name = relative(resolve(root), path);
  if (isAbsolute(name) || name.startsWith("../") || !name.startsWith("LIFEOS/MEMORY/UPGRADES/")) {
    throw new Error("The upgrade publication has an invalid native reference");
  }
  const operation: unknown = JSON.parse(readFileSync(journal, "utf8"));
  if (!object(operation) || !Array.isArray(operation.copies)) throw new Error("Invalid native publication journal");
  if (operation.copies.some((copy: unknown) => object(copy) && copy.path === name)) return;
  operation.copies.push({path: name, data: existsSync(path) ? readFileSync(path).toString("base64") : null});
  const temporary = journal + "." + randomUUID();
  const fd = openSync(temporary, "wx", 0o600);
  try {
    writeFileSync(fd, JSON.stringify(operation));
    fsyncSync(fd);
  } finally { closeSync(fd); }
  renameSync(temporary, journal);
  const directory = openSync(dirname(journal), "r");
  try { fsyncSync(directory); } finally { closeSync(directory); }
}
