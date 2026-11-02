#!/bin/sh
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Run the reader in the standard sts2test macOS account.' >&2
  exit 2
fi
transfer=/private/tmp/untapped-sts2-transfer-01
test_code="$HOME/UntappedSTS2Harness"
if [ ! -d "$test_code/harness" ] || [ -L "$test_code" ] || [ -L "$test_code/harness" ]; then
  echo 'Expected private test setup missing or redirected; stop for review.' >&2
  exit 2
fi
umask 077
cd "$transfer"
shasum -a 256 -c companion07.sha256
for module in cli.py reward_probe.py process_identity.py target_identity.c; do
  if [ -L "$test_code/harness/$module" ] || [ -L "$transfer/harness/$module" ] || [ ! -f "$transfer/harness/$module" ]; then
    echo 'Harness source missing or redirected; stop for review.' >&2
    exit 2
  fi
done
for module in cli.py reward_probe.py process_identity.py target_identity.c; do
  cp "$transfer/harness/$module" "$test_code/harness/$module"
done
cd "$test_code"
probe_python=/opt/homebrew/bin/python3
if [ ! -x "$probe_python" ]; then probe_python=/usr/bin/python3; fi
"$probe_python" - <<'PY'
import json, os, subprocess, tempfile
from pathlib import Path
from harness import cli, game_launch, reward_probe
_, home, _ = game_launch.test_identity('sts2test', game_launch.PROTECTED_HOME)
expected = home/'UntappedSTS2GameSession/SlayTheSpire2.app'/game_launch.EXECUTABLE
# Fail before extracting if the owner is not already at the intended live game.
reward_probe.select_target(reward_probe._process_inventory(), expected, os.getuid())
session=Path(tempfile.mkdtemp(prefix=f'uc-sts2-{os.getuid()}-',dir='/private/tmp'))
subprocess.run(['/usr/bin/tar','-xf','/private/tmp/untapped-sts2-transfer-01/companion07.tar','-C',str(session)],check=True)
(session/'profile').mkdir(mode=0o700)
report=reward_probe.run(session)
print(json.dumps(report,indent=2))
attempt=Path(report['attempt_dir'])
core=attempt/'profile/log.log'
result={'session':str(session),'report':report,
        'stdout':(attempt/'stdout.log').read_text(errors='replace')[-20000:],
        'events':cli.load_events(attempt),
        'core_log_excerpt':core.read_text(errors='replace')[-20000:] if core.exists() else ''}
fd, output=tempfile.mkstemp(prefix='sts2test-reward-probe.',suffix='.json',dir='/private/tmp')
with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2)
os.chmod(output,0o644)
print('Diagnostic file: '+output)
PY
