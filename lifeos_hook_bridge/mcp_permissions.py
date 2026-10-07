# ABOUTME: Applies MCP tool and server permission rules across admitted settings sources.
# ABOUTME: Preserves deny and ask precedence when an allow or malformed source also exists.
import re
from typing import Any


def _matches(rule: Any, tool: str, action: str) -> bool | None:
    if not isinstance(rule, str):
        return None
    if action in {'deny', 'ask'} and '*' in rule and '(' not in rule and ')' not in rule:
        return re.fullmatch(re.escape(rule).replace(r'\*', '.*'), tool) is not None
    if not rule.startswith('mcp__'):
        return False
    # Claude Code skips parameter rules for MCP tools when it loads settings files.
    if '(' in rule or ')' in rule:
        return False
    if not re.fullmatch(r'mcp__[A-Za-z0-9_.*-]+', rule):
        return None
    if '*' not in rule:
        return tool == rule or ('__' not in rule[5:] and tool.startswith(rule + '__'))
    server, separator, pattern = rule[5:].partition('__')
    if not separator or not server or '*' in server:
        return None
    return re.fullmatch(re.escape('mcp__' + server + '__' + pattern).replace(r'\*', '.*'), tool) is not None


def permission_decision(tool: str, sources: list[Any]) -> str:
    matches = {'deny': False, 'ask': False, 'allow': False}
    malformed = False
    for settings in sources:
        if not isinstance(settings, dict):
            malformed = True
            continue
        for action in matches:
            rules = settings.get(action, [])
            if not isinstance(rules, list):
                malformed = True
                continue
            for rule in rules:
                verdict = _matches(rule, tool, action)
                if verdict is None:
                    malformed = True
                elif verdict:
                    matches[action] = True
    if matches['deny']:
        return 'deny'
    if malformed:
        return 'unknown'
    if matches['ask']:
        return 'ask'
    return 'allow' if matches['allow'] else 'none'
