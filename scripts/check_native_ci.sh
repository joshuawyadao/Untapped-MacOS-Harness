#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_root=$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/untapped-native-ci.XXXXXXXX")
trap 'rm -rf -- "$build_root"' EXIT HUP INT TERM

/usr/bin/swiftc -swift-version 5 -module-cache-path "$build_root/modules" \
  -framework Cocoa \
  "$repo_root/launcher/Launcher.swift" \
  "$repo_root/launcher/LauncherOutcome.swift" \
  -o "$build_root/Untapped Launcher"
/usr/bin/swiftc -swift-version 5 -module-cache-path "$build_root/modules" \
  -framework Security \
  "$repo_root/launcher/KeychainHelper.swift" \
  -o "$build_root/KeychainHelper"

for executable in "$build_root/Untapped Launcher" "$build_root/KeychainHelper"; do
  /usr/bin/codesign --force --sign - --timestamp=none "$executable"
  /usr/bin/codesign --verify --strict "$executable"
done
