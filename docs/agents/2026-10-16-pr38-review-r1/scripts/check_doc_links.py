# ABOUTME: Checks relative Markdown links and heading anchors in selected files of a source copy.
# ABOUTME: Also reports backticked repository paths that do not exist, as JSON.
import json
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
files = sys.argv[2:]
link = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')
code_path = re.compile(r'`([A-Za-z0-9_./-]+\.(?:py|md|js|cjs|json|yaml|css|ts|txt|patch))`')


def anchors(path):
    result = set()
    for line in path.read_text().splitlines():
        if line.startswith('#'):
            title = line.lstrip('#').strip().lower()
            slug = re.sub(r'[^\w\- ]', '', title).replace(' ', '-')
            result.add(slug)
    return result


report = []
for name in files:
    source = root / name
    text = source.read_text()
    for target in link.findall(text):
        if re.match(r'[a-z]+:', target):
            continue
        path, _, anchor = target.partition('#')
        resolved = (source.parent / path).resolve() if path else source.resolve()
        problem = None
        if not resolved.exists():
            problem = 'missing target'
        elif anchor and resolved.suffix == '.md' and anchor not in anchors(resolved):
            problem = 'missing anchor'
        if problem:
            report.append({'file': name, 'link': target, 'problem': problem})
    for target in code_path.findall(text):
        candidates = [root / target, source.parent / target]
        if '/' in target and not any(p.exists() for p in candidates):
            report.append({'file': name, 'code_path': target, 'problem': 'path not found'})
print(json.dumps(report, indent=1))
