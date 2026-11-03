#!/bin/sh
# Review `proposal`; activation and live access require explicit flags.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$script_dir/.."
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
exec "$probe_python" -B -m harness.main_launcher "$@"
