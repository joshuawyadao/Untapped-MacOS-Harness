#!/bin/sh
# Stage only after copy08 signing and the controlled-access proposal are approved.
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Run in the standard sts2test account.' >&2
  exit 2
fi
observe=
if [ "${1-}" = "--observe-debug-game" ] && [ "$#" -eq 1 ]; then
  observe=--observe-debug-game
elif [ "$#" -ne 0 ]; then
  echo 'Usage: controlled_sign_in.sh [--observe-debug-game]' >&2
  exit 2
fi
transfer=/private/tmp/untapped-sts2-transfer-01
test_code="$HOME/UntappedSTS2Harness"
if [ ! -d "$test_code/harness" ] || [ -L "$test_code" ] || [ -L "$test_code/harness" ]; then
  echo 'Private test harness missing or redirected.' >&2
  exit 2
fi
umask 077
cd "$transfer"
shasum -a 256 -c companion08.sha256
for module in asar.py patches.py signing.py cli.py process_identity.py target_identity.c game_launch.py game_debug.py reward_probe.py controlled.py gateway.py controlled_network.cjs; do
  if [ -L "$transfer/harness/$module" ] || [ ! -f "$transfer/harness/$module" ] || [ -L "$test_code/harness/$module" ]; then
    echo 'Harness source missing or redirected.' >&2
    exit 2
  fi
done
for module in asar.py patches.py signing.py cli.py process_identity.py target_identity.c game_launch.py game_debug.py reward_probe.py controlled.py gateway.py controlled_network.cjs; do
  cp "$transfer/harness/$module" "$test_code/harness/$module"
done
cd "$test_code"
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
session=$("$probe_python" - <<'PY'
import os,tempfile
from harness import game_launch
# Validate before extracting/starting any vendor application.
game_launch.test_identity('sts2test',game_launch.PROTECTED_HOME)
print(tempfile.mkdtemp(prefix=f'uc-sts2-{os.getuid()}-',dir='/private/tmp'))
PY
)
# Preserve recorded signed modes while keeping the containing root private.
tar -xpf "$transfer/companion08.tar" -C "$session"
# The expansion is either empty or the fixed literal flag selected above.
"$probe_python" -m harness.controlled "$session" --approve-controlled-access $observe
