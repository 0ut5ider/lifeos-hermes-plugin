# ABOUTME: Applies the measured onboarding admission change to the retained public source clone.
# ABOUTME: Refreshes both packaged patch copies from the exact native source diff.
from pathlib import Path
import subprocess

repository = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
source = Path('/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos')
path = source / 'LifeOS/install/LIFEOS/PULSE/Observability/observability.ts'
text = path.read_text()
text = text.replace('function telosPersonalized(): boolean {\n  try {\n    const sections = parseTelosUnified()',
                    'function telosPersonalized(read = readMd): boolean {\n  try {\n    const sections = parseTelosUnified(read)')
text = text.replace('sections[key] || readMd(join(TELOS_DIR, legacyFile))',
                    'sections[key] || read(join(TELOS_DIR, legacyFile))')
text = text.replace('function handleOnboardingState(): Response {',
                    'function handleOnboardingState(read = readMd, exists = existsSafe): Response {')
text = text.replace('const markerExists = existsSafe(markerPath)', 'const markerExists = exists(markerPath)')
text = text.replace('!telosPersonalized()', '!telosPersonalized(read)')
text = text.replace('if (existsSafe(daIdentityPath)) {\n      const content = readFileSync(daIdentityPath, "utf-8")',
                    'if (exists(daIdentityPath)) {\n      const content = read(daIdentityPath)')
anchor = 'export function renderBusinessView('
assert text.count(anchor) == 1
addition = '''export function onboardingViewSources(): string[] {
  return ["TELOS", "MISSION", "GOALS", "PROBLEMS", "STRATEGIES", "CHALLENGES"]
    .map(name => "LIFEOS/USER/TELOS/" + name + ".md")
    .concat(["LIFEOS/USER/.template-mode", "LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md"]);
}

export function renderOnboardingView(sources: ReadonlyArray<{relative: string; content: string}>): Response {
  const allowed = new Set(onboardingViewSources());
  if (sources.length > allowed.size || sources.some(source => !allowed.has(source.relative))
      || new Set(sources.map(source => source.relative)).size !== sources.length) {
    throw new Error("Choose fixed onboarding sources");
  }
  const contents = new Map(sources.map(source => [join(dirname(LIFEOS_DIR), source.relative), source.content]));
  const read = (path: string): string => {
    if (!allowed.has(path.slice(dirname(LIFEOS_DIR).length + 1))) throw new Error("Choose fixed onboarding sources");
    return contents.get(path) ?? "";
  };
  return handleOnboardingState(read, path => contents.has(path));
}

'''
text = text.replace(anchor, addition + anchor)
anchor = '  if (hasManagedMemoryHTTP() && pathname === "/api/user-index") {'
assert text.count(anchor) == 1
addition = '''  if (hasManagedMemoryHTTP() && pathname === "/api/onboarding/state") {
    const headers = {"cache-control": "no-store"};
    if (method !== "GET") return Response.json({error: "Onboarding views require GET"}, {status: 405, headers});
    if (url.search) return Response.json({error: "Onboarding views require fixed routes"}, {status: 400, headers});
    const origin = req.headers.get("origin");
    if (origin && origin !== url.origin) return Response.json({error: "Onboarding views require the current origin"}, {status: 403, headers});
    try { return memoryHTTPResponse(req, "life", pathname); }
    catch { return Response.json({error: "Authenticated memory is unavailable"}, {status: 503, headers}); }
  }

'''
text = text.replace(anchor, addition + anchor)
path.write_text(text)
filename = 'LifeOS/install/LIFEOS/PULSE/Observability/observability.ts'
section = subprocess.check_output(['git', 'diff', 'HEAD', '--', filename], cwd=source, text=True)
start = 'diff --git a/' + filename + ' b/' + filename + '\n'
for patch in (repository / 'patches/lifeos-memory-access.patch',
              repository / 'lifeos_hook_bridge/patches/lifeos-memory-access.patch'):
    content = patch.read_text()
    begin = content.index(start)
    end = content.find('\ndiff --git ', begin + len(start))
    assert end >= 0
    patch.write_text(content[:begin] + section.rstrip() + '\n' + content[end + 1:])
