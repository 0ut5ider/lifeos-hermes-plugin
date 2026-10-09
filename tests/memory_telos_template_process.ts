// ABOUTME: Executes all native Telos template readers on a disposable installation.
// ABOUTME: Emits declared results or a sanitized refusal without a personal-data stack trace.
import {pathToFileURL} from 'node:url';
try {
  const module = await import(pathToFileURL(process.argv[2]).href);
  const result = {files: module.getAllTelosData(), context: module.getTelosContext(),
    list: module.getTelosFileList(), count: module.getTelosFileCount()};
  console.log(JSON.stringify(result));
} catch {
  console.error('Telos template data is unavailable');
  process.exit(2);
}
