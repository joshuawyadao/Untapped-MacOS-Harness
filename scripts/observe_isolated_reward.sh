#!/bin/sh
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Run the reader in the standard sts2test macOS account.' >&2
  exit 2
fi
transfer=/private/tmp/untapped-sts2-transfer-01
test_code="$HOME/UntappedSTS2Harness"
companion_session="$HOME/UntappedSTS2CompanionSession"
if [ ! -d "$test_code/harness" ] || [ -L "$companion_session" ]; then
  echo 'Expected private test setup missing or redirected; stop for review.' >&2
  exit 2
fi
umask 077
if [ ! -e "$companion_session" ]; then
  cd "$transfer"
  shasum -a 256 -c companion06.sha256
  mkdir "$companion_session"
  tar -xf "$transfer/companion06.tar" -C "$companion_session"
  mkdir "$companion_session/profile"
fi
cp "$transfer/harness/reward_probe.py" "$test_code/harness/reward_probe.py"
cd "$test_code"
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
"$probe_python" -m harness.reward_probe "$companion_session"
