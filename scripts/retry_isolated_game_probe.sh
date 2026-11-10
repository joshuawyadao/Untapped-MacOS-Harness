#!/bin/sh
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Run this retry in the standard sts2test macOS account.' >&2
  exit 2
fi
transfer=/private/tmp/untapped-sts2-transfer-01
test_code="$HOME/UntappedSTS2Harness"
test_session="$HOME/UntappedSTS2GameSession"
test_helper="$test_code/harness/game_launch.py"
if [ ! -f "$test_session/manifest.json" ] || [ ! -f "$test_helper" ] || [ -L "$test_helper" ]; then
  echo 'Expected existing private test setup not found; stop for review.' >&2
  exit 2
fi
cp "$transfer/harness/game_launch.py" "$test_helper"
cd "$test_code"
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
"$probe_python" -m harness.game_launch launch "$test_session" --seconds 60
