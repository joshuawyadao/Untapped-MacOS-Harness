#!/bin/sh
# At most two fixed-data HTTPS requests; no app launch or real account data.
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Run in the standard sts2test account.' >&2
  exit 2
fi
if [ "$#" -ne 0 ]; then
  echo 'Usage: diagnose_account_transport.sh' >&2
  exit 2
fi
umask 077
cd /private/tmp/untapped-sts2-transfer-01
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
exec "$probe_python" -m harness.transport_diagnostic
