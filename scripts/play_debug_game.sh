#!/bin/sh
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Run in the standard sts2test account.' >&2
  exit 2
fi
seconds=60
manual_play=
if [ "${1-}" = "--manual-play" ] && [ "$#" -eq 1 ]; then
  seconds=900
  manual_play=--manual-play
elif [ "$#" -ne 0 ]; then
  echo 'Usage: play_debug_game.sh [--manual-play]' >&2
  exit 2
fi
transfer=/private/tmp/untapped-sts2-transfer-01
test_code="$HOME/UntappedSTS2Harness"
if [ ! -d "$test_code/harness" ] || [ -L "$test_code" ] || [ -L "$test_code/harness" ]; then
  echo 'Private test harness missing or redirected.' >&2
  exit 2
fi
for module in game_debug.py game_launch.py; do
  if [ -L "$test_code/harness/$module" ] || [ -L "$transfer/harness/$module" ] || [ ! -f "$transfer/harness/$module" ]; then
    echo 'Harness source missing or redirected.' >&2
    exit 2
  fi
done
for module in game_debug.py game_launch.py; do
  cp "$transfer/harness/$module" "$test_code/harness/$module"
done
cd "$test_code"
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
# This expansion is either empty or the one fixed literal flag above.
"$probe_python" -m harness.game_launch launch "$HOME/UntappedSTS2DebugGameSession" --debug-game --seconds "$seconds" $manual_play
