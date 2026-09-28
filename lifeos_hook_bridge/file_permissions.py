# ABOUTME: Applies Claude Code file rules to paths used by Bash commands.
# ABOUTME: Keeps each rule anchored to the settings source that supplied it.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pathspec import GitIgnoreSpec


def _rule_matches(rule: Any, tool: str, path: str, cwd: str, source: str, action: str) -> bool | None:
    if not isinstance(rule, str):
        return None
    if rule == tool:
        return True
    if not rule.startswith(f"{tool}("):
        return False
    if not rule.endswith(")"):
        return None
    pattern = rule[len(tool) + 1:-1]
    if pattern == "*":
        return True
    anchored = False
    if pattern.startswith("//"):
        anchor = "/"
        pattern = pattern[2:]
        anchored = True
    elif pattern.startswith("~/"):
        anchor = str(Path.home())
        pattern = pattern[2:]
        anchored = True
    elif pattern.startswith("/"):
        anchor = source
        pattern = pattern[1:]
        anchored = True
    else:
        anchor = cwd
        pattern = pattern.removeprefix("./")
    if not pattern:
        return None
    anchor = os.path.normpath(anchor)
    try:
        relative = os.path.relpath(path, anchor)
    except ValueError:
        return False
    if relative == ".." or relative.startswith("../"):
        return False
    if not anchored and action in {"deny", "ask"} and pattern.count("/") == 1 and pattern.endswith("/**"):
        pattern = "**/" + pattern
    if anchored:
        pattern = "/" + pattern
    try:
        return GitIgnoreSpec.from_lines([pattern]).match_file(relative)
    except (TypeError, ValueError):
        return path == os.path.normpath(os.path.join(anchor, pattern)) if action in {"deny", "ask"} else None


def _source_matches(
    settings: Any, action: str, tool: str, paths: tuple[str, ...], cwd: str, source: str,
) -> bool | None:
    if not isinstance(settings, dict):
        return None
    rules = settings.get(action, [])
    if not isinstance(rules, list):
        return None
    matched_rules: list[str] = []
    uncertain = False
    for rule in rules:
        if not isinstance(rule, str):
            uncertain = True
            continue
        negate = rule.startswith(f"{tool}(!")
        if negate and rule.startswith((f"{tool}(!/", f"{tool}(!~/")):
            continue
        candidate = rule.replace(f"{tool}(!", f"{tool}(", 1) if negate else rule
        results = [_rule_matches(candidate, tool, path, cwd, source, action) for path in paths]
        if None in results:
            uncertain = True
        elif (all(results) if action == "allow" else any(results)):
            if negate:
                matched_rules = [prior for prior in matched_rules if prior.startswith(
                    (f"{tool}(/", f"{tool}(~/")
                ) or prior.endswith("/**)")]
            else:
                matched_rules.append(rule)
    return True if matched_rules else None if uncertain else False


def file_target_decision(
    target: str, operation: str, cwd: str, sources: list[tuple[Any, str]], *, host_paths: bool,
) -> str:
    """Return deny, ask, allow, or unknown for one literal Bash file target."""
    if not os.path.isabs(cwd):
        return "unknown"
    requested = os.path.normpath(target if os.path.isabs(target) else os.path.join(cwd, target))
    resolved = os.path.realpath(requested) if host_paths else requested
    paths = (requested,) if resolved == requested else (requested, resolved)
    tools = ("Read", "Edit") if operation == "write" else ("Read",)
    for action in ("deny", "ask"):
        uncertain = False
        for settings, source in sources:
            for tool in tools:
                match = _source_matches(settings, action, tool, paths, cwd, source)
                if match is True:
                    return action
                if match is None:
                    uncertain = True
        if uncertain:
            return "unknown"
    allow_tool = "Edit" if operation == "write" else "Read"
    explicitly_allowed = False
    for settings, source in sources:
        match = _source_matches(settings, "allow", allow_tool, paths, cwd, source)
        if match is True:
            explicitly_allowed = True
        elif match is None:
            return "unknown"
    inside_cwd = requested == cwd or requested.startswith(cwd.rstrip("/") + "/")
    if host_paths and resolved != requested:
        inside_cwd = inside_cwd and (resolved == cwd or resolved.startswith(cwd.rstrip("/") + "/"))
    return "allow" if explicitly_allowed or inside_cwd else "unknown"
