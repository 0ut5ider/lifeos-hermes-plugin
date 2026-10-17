# ABOUTME: Checks relative Markdown links, heading anchors, git tracking, and U+2014 in given files.
# ABOUTME: Run from the repository root with python3 -I and pass Markdown paths as arguments.
import json
import os
import re
import subprocess
import sys

LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')


def slug(heading):
    s = heading.strip().lower()
    s = re.sub(r'[^\w\- ]', '', s)
    return s.replace(' ', '-')


def anchors(path):
    out = set()
    with open(path, encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^#{1,6}\s+(.*?)\s*#*\s*$', line)
            if m:
                out.add(slug(m.group(1)))
    return out


tracked = set(subprocess.run(['git', 'ls-files'], capture_output=True, text=True).stdout.splitlines())
result = {'files': {}, 'totals': {'relative_links': 0, 'broken': 0, 'untracked': 0, 'bad_anchors': 0, 'em_dash': 0}}
for md in sys.argv[1:]:
    text = open(md, encoding='utf-8').read()
    rec = {'relative_links': 0, 'problems': [], 'em_dash': text.count(chr(0x2014))}
    for target in LINK.findall(text):
        if re.match(r'^[a-z]+:', target) or target.startswith('#') and False:
            continue
        path, _, frag = target.partition('#')
        rec['relative_links'] += 1
        full = os.path.normpath(os.path.join(os.path.dirname(md), path)) if path else md
        if not os.path.exists(full):
            rec['problems'].append({'target': target, 'issue': 'broken'})
            continue
        if os.path.isfile(full) and full not in tracked:
            rec['problems'].append({'target': target, 'issue': 'untracked'})
        if frag and full.endswith('.md') and frag not in anchors(full):
            rec['problems'].append({'target': target, 'issue': 'bad_anchor'})
    result['files'][md] = rec
    t = result['totals']
    t['relative_links'] += rec['relative_links']
    t['em_dash'] += rec['em_dash']
    for p in rec['problems']:
        t[{'broken': 'broken', 'untracked': 'untracked', 'bad_anchor': 'bad_anchors'}[p['issue']]] += 1
print(json.dumps(result, indent=2))
