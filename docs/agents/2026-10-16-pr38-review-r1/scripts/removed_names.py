# ABOUTME: Lists import bindings removed between base and head copies of Python files.
# ABOUTME: Reports any remaining load of a removed name in the head file, which would raise NameError.
import ast
import json
import sys
from pathlib import Path


def bindings(tree):
    names = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                name = alias.asname or alias.name.split('.')[0]
                names.setdefault(name, []).append(node.lineno)
    return names


def loads(tree):
    used = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.setdefault(node.id, []).append(node.lineno)
    return used


def main(base, head, files):
    report = []
    for name in files:
        before = ast.parse((Path(base) / name).read_text())
        after = ast.parse((Path(head) / name).read_text())
        removed = sorted(set(bindings(before)) - set(bindings(after)))
        used = loads(after)
        report.append({'file': name, 'removed_imports': removed,
                       'loads_of_removed': {n: used[n] for n in removed if n in used}})
    print(json.dumps(report, indent=1))


main(sys.argv[1], sys.argv[2], sys.argv[3:])
