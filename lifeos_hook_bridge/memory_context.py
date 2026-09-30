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
                 hermes_home: str, author_id: str | None = None) -> SessionContext:
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
    return SessionContext(transport, author, destination, visibility, participants, model_route,
                          metadata.get("HERMES_SESSION_ID", ""))
