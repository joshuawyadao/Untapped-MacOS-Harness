#!/bin/sh
# Run manually from Terminal in the dedicated standard macOS test account.
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Log into the standard sts2test macOS account before running this script.' >&2
  exit 2
fi
transfer=/private/tmp/untapped-sts2-transfer-01
test_code="$HOME/UntappedSTS2Harness"
test_session="$HOME/UntappedSTS2GameSession"
if [ -e "$test_code" ] || [ -e "$test_session" ]; then
  echo 'Test directories already exist; stop for review rather than overwrite.' >&2
  exit 2
fi
umask 077
cd "$transfer"
shasum -a 256 -c game.sha256
mkdir "$test_code"
cp -R "$transfer/harness" "$test_code/harness"
mkdir "$test_code/source"
tar -xf "$transfer/game.tar" -C "$test_code/source"
cd "$test_code"
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
"$probe_python" -m harness.game_launch prepare "$test_code/source/SlayTheSpire2.app" "$test_session" --original-home /Users/joshuawyadao --test-user sts2test
"$probe_python" -m harness.game_launch launch "$test_session" --seconds 60
