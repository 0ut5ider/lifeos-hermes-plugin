#!/bin/bash
# ABOUTME: Sets a disposable dashboard password on the rehearsal clone, logs in, and calls the owner APIs.
# ABOUTME: Runs as the service account; the password stays in a private file and is never printed.
set -eu
cd ~; H=~/.hermes; export XDG_RUNTIME_DIR=/run/user/$(id -u)
umask 077; [ -f ~/rehearsal-password ] || python3 -c "import secrets; print(secrets.token_urlsafe(18))" > ~/rehearsal-password
HASH=$($H/tools/python-3.14.7+20260901-linux-x64/bin/python3 -I -c "import sys; sys.path.insert(0, '$H/hermes-agent'); sys._hermes_pin_default_home = True; import hermes_bootstrap; from plugins.dashboard_auth.basic import hash_password; print(hash_password(open('$HOME/rehearsal-password').read().strip()))")
python3 - "$H/config.yaml" "$HASH" <<'PY'
import re, sys
path, value = sys.argv[1:3]
text = open(path).read()
new, count = re.subn(r'(?m)^(    password_hash:)[^\n]*(\n      scrypt\S*)?', lambda m: m.group(1) + ' ' + value, text)
assert count == 1, count
f = open(path, 'r+'); f.write(new); f.truncate(); f.close()
PY
systemctl --user restart hermes-dashboard; sleep 12
B=http://127.0.0.1:18819; HOSTH="Host: lifeos-daily.tail682dd.ts.net"; J=~/rehearsal-cookies; rm -f $J
python3 -c "import json; print(json.dumps({'provider':'basic','username':'adrian','password':open('$HOME/rehearsal-password').read().strip()}))" > ~/rehearsal-login.json
curl -s -o /dev/null -w "login %{http_code}\n" -c $J -H "$HOSTH" -H "Content-Type: application/json" -H "Origin: https://lifeos-daily.tail682dd.ts.net" --data @$HOME/rehearsal-login.json $B/auth/password-login
rm -f ~/rehearsal-login.json
curl -s -b $J -H "$HOSTH" $B/api/auth/me | head -c 200; echo
for p in lifeos-release-manager/installation lifeos-release-manager/compatibility lifeos-release-manager/operations lifeos-hook-bridge/memory/http/settings lifeos-hook-bridge/memory; do
  printf '%s ' "$p"; curl -s -b $J -H "$HOSTH" -w " [%{http_code}]" $B/api/plugins/$p | head -c 260; echo
done
