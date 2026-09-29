# ABOUTME: Replaces exact LifeOS-owned hook registrations during a staged update.
# ABOUTME: Preserves unrelated hooks and refuses edited or ambiguous old entries.

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any


class HookUpdateConflict(ValueError):
    pass


def _validate_manifest(manifest: Any) -> None:
    if not isinstance(manifest, dict):
        raise HookUpdateConflict("Hook manifest is invalid")
    for event, groups in manifest.items():
        if not isinstance(event, str) or not event or not isinstance(groups, list):
            raise HookUpdateConflict("Hook manifest is invalid")
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise HookUpdateConflict("Hook manifest is invalid")
            if not group["hooks"] or any(not isinstance(hook, dict) or not hook for hook in group["hooks"]):
                raise HookUpdateConflict("Hook manifest is invalid")


def _metadata(group: dict) -> dict:
    return {key: value for key, value in group.items()
            if key != "hooks" and not (key == "matcher" and value in ("", None))}


def _identity(event: str, group: dict, hook: dict) -> tuple:
    kind = hook.get("type")
    command = hook.get("command") if kind == "command" else hook.get("url")
    if not isinstance(command, str) or not command:
        command = json.dumps(hook, sort_keys=True, separators=(",", ":"))
    return event, group.get("matcher") or "", kind, command


def replace_owned_hooks(current: dict, old: dict, new: dict) -> tuple[dict, dict]:
    """Replace the exact old LifeOS hooks while keeping other settings and hooks."""
    _validate_manifest(old)
    _validate_manifest(new)
    if not isinstance(current, dict) or not isinstance(current.get("hooks"), dict):
        raise HookUpdateConflict("Current hook settings are invalid")
    _validate_manifest(current["hooks"])

    updated = deepcopy(current)
    current_hooks = updated["hooks"]
    removed: dict[str, dict[int, set[int]]] = {}
    first_index: dict[str, int] = {}
    old_count = 0
    for event, groups in old.items():
        installed_groups = current_hooks.get(event, [])
        for old_group in groups:
            for old_hook in old_group["hooks"]:
                matches = [
                    (group_index, hook_index)
                    for group_index, group in enumerate(installed_groups)
                    if _metadata(group) == _metadata(old_group)
                    for hook_index, installed_hook in enumerate(group["hooks"])
                    if installed_hook == old_hook
                ]
                if not matches:
                    raise HookUpdateConflict(f"LifeOS hook is missing or edited: {event} {_identity(event, old_group, old_hook)[-1]}")
                if len(matches) != 1:
                    raise HookUpdateConflict(f"LifeOS hook is ambiguous: {event} {_identity(event, old_group, old_hook)[-1]}")
                group_index, hook_index = matches[0]
                if hook_index in removed.setdefault(event, {}).setdefault(group_index, set()):
                    raise HookUpdateConflict(f"LifeOS hook manifest repeats an entry: {event}")
                removed[event][group_index].add(hook_index)
                first_index[event] = min(first_index.get(event, group_index), group_index)
                old_count += 1

    foreign_count = 0
    retained: dict[str, list[dict]] = {}
    for event, groups in current_hooks.items():
        remaining = []
        for index, group in enumerate(groups):
            hooks = [hook for hook_index, hook in enumerate(group["hooks"])
                     if hook_index not in removed.get(event, {}).get(index, set())]
            if hooks:
                remaining.append((index, {**group, "hooks": hooks}))
                foreign_count += len(hooks)
        retained[event] = remaining

    foreign_identities = {
        _identity(event, group, hook)
        for event, groups in retained.items()
        for _, group in groups for hook in group["hooks"]
    }
    new_identities = set()
    new_count = 0
    for event, groups in new.items():
        for group in groups:
            for hook in group["hooks"]:
                identity = _identity(event, group, hook)
                if identity in foreign_identities or identity in new_identities:
                    raise HookUpdateConflict(f"New LifeOS hook collides with another hook: {event} {identity[-1]}")
                new_identities.add(identity)
                new_count += 1

    result_hooks = {}
    for event in dict.fromkeys((*current_hooks, *new)):
        groups = retained.get(event, [])
        additions = deepcopy(new.get(event, []))
        if event in first_index:
            insertion = sum(index < first_index[event] for index, _ in groups)
            merged = [group for _, group in groups]
            merged[insertion:insertion] = additions
        else:
            merged = [group for _, group in groups] + additions
        if merged:
            result_hooks[event] = merged
    updated["hooks"] = deepcopy(current_hooks) if old == new else result_hooks
    return updated, {"old_hooks": old_count, "new_hooks": new_count, "foreign_hooks": foreign_count}
