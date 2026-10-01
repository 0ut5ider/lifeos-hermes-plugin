# Memory collection and HTTP admission need separate entry points

Date: 2026-10-01. Disposable native and authenticated dashboard listeners reproduce the boundary.

Protecting the native PULSE HTTP handler changes anonymous reads from 200 to 401. It also changes the plugin's authenticated snapshots to 503. The plugin's trusted projection worker calls that same HTTP handler without a browser credential. The handler correctly refuses it.

The fix exports a native collector for four views. The plugin invokes that collector only after its owner and physical-source checks. Public HTTP always uses incoming credentials, including when the process has `LIFEOS_MEMORY_INTERNAL=1`. No bypass flag or administrative process token is added.

A Chromium session uses the actual Hermes login form. Cookies permit four native reads on another localhost port. Cross-origin fetch fails. Logout changes the next native read to 401. This result relies on the root cookie path and the same host. It does not prove a prefixed cookie, Secure LAN transport, or the complete PULSE frontend.

Transport checks also find that JSON syntax alone accepts a truncated body with a larger declared Content-Length. Exact declared-length validation makes that response unavailable. The relay binds successful responses to the configured profile, root, and principal. Its browser login link uses a separate configured public URL, because a server's loopback destination does not identify a laptop-accessible address.
