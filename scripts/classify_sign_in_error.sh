#!/bin/sh
# Read saved private errors only; no application launch or network access.
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Run in the standard sts2test account.' >&2
  exit 2
fi
if [ "$#" -ne 1 ]; then
  echo 'Usage: classify_sign_in_error.sh PRIVATE_ATTEMPT_DIRECTORY' >&2
  exit 2
fi
umask 077
cd /private/tmp/untapped-sts2-transfer-01
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
exec "$probe_python" -m harness.auth_diagnostic "$1"
