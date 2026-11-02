#!/bin/sh
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Run the diagnostic in the standard sts2test macOS account.' >&2
  exit 2
fi
transfer=/private/tmp/untapped-sts2-transfer-01
test_code="$HOME/UntappedSTS2Harness"
test_helper="$test_code/harness/game_launch.py"
if [ ! -f "$test_helper" ] || [ -L "$test_helper" ]; then
  echo 'Expected test harness missing or redirected; stop for review.' >&2
  exit 2
fi
umask 077
cp "$transfer/harness/game_launch.py" "$test_helper"
cd "$test_code"
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
"$probe_python" - <<'PY'
import json, os, re, tempfile
from pathlib import Path
from harness.game_launch import launch
report = launch(Path.home() / 'UntappedSTS2GameSession', 60)
log = (Path(report['attempt']) / 'stdout.log').read_text(errors='replace')
lines = [line for line in log.splitlines() if not re.match(r'\s*Index \d+:', line)]
fd, output = tempfile.mkstemp(prefix='sts2test-home-check.', suffix='.json', dir='/private/tmp')
with os.fdopen(fd, 'w') as destination:
    json.dump({'report': report, 'game_log_excerpt': lines[-180:]}, destination, indent=2)
os.chmod(output, 0o644)
print(json.dumps(report, indent=2))
print('Diagnostic file: ' + output)
PY
