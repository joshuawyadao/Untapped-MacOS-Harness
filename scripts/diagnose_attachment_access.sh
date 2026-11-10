#!/bin/sh
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Run this original-fixture diagnostic in the standard sts2test macOS account.' >&2
  exit 2
fi
transfer=/private/tmp/untapped-sts2-transfer-01
test_code="$HOME/UntappedSTS2Harness"
if [ ! -d "$test_code/harness" ] || [ -L "$test_code" ] || [ -L "$test_code/harness" ]; then
  echo 'Expected private test harness missing or redirected.' >&2
  exit 2
fi
umask 077
for module in attachment_diagnostic.py attachment_target.c attachment_inspector.c; do
  if [ -L "$transfer/harness/$module" ] || [ ! -f "$transfer/harness/$module" ] || [ -L "$test_code/harness/$module" ]; then
    echo 'Original fixture source missing or redirected.' >&2
    exit 2
  fi
done
for module in attachment_diagnostic.py attachment_target.c attachment_inspector.c; do
  cp "$transfer/harness/$module" "$test_code/harness/$module"
done
cd "$test_code"
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
"$probe_python" - <<'PY'
import json, os, tempfile
from harness import attachment_diagnostic, game_launch
# Verify the standard account before signing or launching any original fixture.
game_launch.test_identity('sts2test', game_launch.PROTECTED_HOME)
report = attachment_diagnostic.run()
print(json.dumps(report, indent=2))
fd, output = tempfile.mkstemp(prefix='sts2test-attachment-access.', suffix='.json', dir='/private/tmp')
with os.fdopen(fd, 'w') as stream:
    json.dump(report, stream, indent=2)
os.chmod(output, 0o644)
print('Diagnostic file: ' + output)
PY
