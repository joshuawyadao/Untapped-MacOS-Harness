#!/bin/sh
# Stage only after the separately approved copy has been signed and verified.
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Run in the standard sts2test account.' >&2
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
shasum -a 256 -c debug-game01.sha256
for module in game_debug.py game_launch.py reward_probe.py; do
  if [ -L "$test_code/harness/$module" ] || [ -L "$transfer/harness/$module" ] || [ ! -f "$transfer/harness/$module" ]; then
    echo 'Harness source missing or redirected.' >&2
    exit 2
  fi
done
for module in game_debug.py game_launch.py reward_probe.py; do
  cp "$transfer/harness/$module" "$test_code/harness/$module"
done
cd "$test_code"
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
"$probe_python" - <<'PY'
import json, os, subprocess, tempfile
from pathlib import Path
from harness import game_debug, game_launch
_, home, _ = game_launch.test_identity('sts2test', game_launch.PROTECTED_HOME)
if game_launch.running_conflicts():
    raise SystemExit('Close Steam and every STS2 copy before installing the separate debug game.')
destination = home/game_debug.TEST_SESSION
if destination.exists() or destination.is_symlink():
    raise SystemExit('Debug-game session already exists; stop instead of overwriting.')
source = Path(tempfile.mkdtemp(prefix='sts2-debug-transfer-', dir='/private/tmp'))
subprocess.run(['/usr/bin/tar','-xf','/private/tmp/untapped-sts2-transfer-01/debug-game01.tar','-C',str(source)],check=True)
print(json.dumps(game_debug.install(source, destination), indent=2))
PY
