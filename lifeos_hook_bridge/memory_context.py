# ABOUTME: Builds memory contexts from host identities, destinations, and provider routes.
# ABOUTME: Keeps unknown audiences and scheduled authors outside private memory grants.

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Mapping
from urllib.parse import urlsplit

from .memory_policy import SessionContext


def route_identity(provider: str, model: str, base_url: str, api_mode: str) -> str:
    if any(not isinstance(value, str) or not value for value in (provider, model, base_url, api_mode)):
        return "unknown"
    try:
        endpoint = urlsplit(base_url)
        if endpoint.scheme not in ("http", "https") or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
            return "unknown"
    except ValueError:
        return "unknown"
    return hashlib.sha256(json.dumps([provider, model, base_url.rstrip("/"), api_mode], separators=(",", ":")).encode()).hexdigest()


def host_context(configuration: dict[str, Any], metadata: Mapping[str, str], *, model_route: str,
                 hermes_home: str, author_id: str | None = None, audience_lookup=None) -> SessionContext:
    transport = metadata.get("HERMES_SESSION_PLATFORM", "")
    author = metadata.get("HERMES_SESSION_USER_ID", "") if author_id is None else author_id
    destination = metadata.get("HERMES_SESSION_CHAT_ID", "")
    thread = metadata.get("HERMES_SESSION_THREAD_ID", "")
    visibility = "private" if metadata.get("HERMES_SESSION_CHAT_TYPE") in ("dm", "private") else "unknown"
    if transport in ("cli", "tui"):
        transport, author, destination, thread, visibility = "terminal", str(os.getuid()), hermes_home, "", "private"
    if metadata.get("HERMES_CRON_SESSION") == "1":
        transport = metadata.get("HERMES_CRON_AUTO_DELIVER_PLATFORM", "")
        destination = metadata.get("HERMES_CRON_AUTO_DELIVER_CHAT_ID", "")
        thread = metadata.get("HERMES_CRON_AUTO_DELIVER_THREAD_ID", "")
        author, visibility = "", "unknown"
    if thread:
        destination += "/" + thread
    principal = configuration.get("accounts", {}).get(f"{transport}:{author}", "")
    participants = (principal,) if principal and visibility == "private" else ()
    if (transport == 'discord' and visibility == 'unknown' and principal
            and metadata.get('HERMES_CRON_SESSION') != '1'):
        from .discord_audience import ChannelAudience, resolve_audience
        audience = (audience_lookup or resolve_audience)(configuration, dict(metadata, HERMES_SESSION_USER_ID=author))
        if (isinstance(audience, ChannelAudience) and audience.channel == destination
                and audience.owner == author and audience.principal == principal):
            visibility, participants = 'private', (principal,)
    return SessionContext(transport, author, destination, visibility, participants, model_route,
                          metadata.get("HERMES_SESSION_ID", ""))


def parse_context(value: Any) -> SessionContext:
    fields = {'transport', 'author', 'destination', 'visibility', 'participants', 'model_route', 'session_id'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('Native memory requires host-bound conversation metadata')
    if any(not isinstance(content, str) for key, content in value.items() if key != 'participants'):
        raise ValueError('Invalid native conversation metadata')
    participants = value['participants']
    if not isinstance(participants, list) or any(not isinstance(person, str) for person in participants):
        raise ValueError('Invalid native conversation audience')
    return SessionContext(**dict(value, participants=tuple(participants)))


def current_host_metadata() -> dict[str, str] | None:
    try:
        from gateway.session_context import get_session_env
    except ImportError:
        return None
    keys = ('PLATFORM', 'USER_ID', 'CHAT_ID', 'THREAD_ID', 'CHAT_TYPE', 'SCOPE_ID', 'ID')
    metadata = {f'HERMES_SESSION_{key}': get_session_env(f'HERMES_SESSION_{key}') for key in keys}
    for key in ('HERMES_CRON_SESSION', 'HERMES_CRON_AUTO_DELIVER_PLATFORM',
                'HERMES_CRON_AUTO_DELIVER_CHAT_ID', 'HERMES_CRON_AUTO_DELIVER_THREAD_ID'):
        metadata[key] = get_session_env(key)
    return metadata
