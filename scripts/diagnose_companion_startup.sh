#!/bin/sh
set -eu
if [ "$(id -un)" != "sts2test" ]; then
  echo 'Run this diagnostic in the standard sts2test macOS account.' >&2
  exit 2
fi
transfer=/private/tmp/untapped-sts2-transfer-01
test_code="$HOME/UntappedSTS2Harness"
if [ ! -d "$test_code/harness" ] || [ -L "$test_code" ] || [ -L "$test_code/harness" ]; then
  echo 'Expected test harness missing or redirected; stop for review.' >&2
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
import json, os, plistlib, stat, subprocess, sys, tempfile
from pathlib import Path
from harness import cli, game_launch, reward_probe
# Check the actual test account and absence of Steam/game before staging a new copy.
game_launch.test_identity('sts2test', game_launch.PROTECTED_HOME)
if list(reward_probe._candidates(reward_probe._process_inventory())):
    raise SystemExit('Close the test game and Steam before this startup-only comparison.')
transfer=Path('/private/tmp/untapped-sts2-transfer-01')
session=Path(tempfile.mkdtemp(prefix=f'uc-sts2-{os.getuid()}-',dir='/private/tmp'))
subprocess.run(['/usr/bin/tar','-xf',str(transfer/'companion07.tar'),'-C',str(session)],check=True)
(session/'profile').mkdir(mode=0o700)
report=reward_probe.run_startup(session)
print(json.dumps(report,indent=2))
attempt=Path(report['attempt_dir'])
# Only inert filesystem/plist inspection here; no helper executable is run.
snapshot=r'''
import json,plistlib,stat,sys
from pathlib import Path
app=Path(sys.argv[1]); info=plistlib.loads((app/'Contents/Info.plist').read_bytes())
name=info.get('CFBundleName',''); out={'bundle_name':name,'bundle_executable':info.get('CFBundleExecutable'),'helpers':[]}
for suffix in ('',' (GPU)',' (Plugin)',' (Renderer)'):
    h=app/'Contents/Frameworks'/f'{name} Helper{suffix}.app'/'Contents/MacOS'/f'{name} Helper{suffix}'
    out['helpers'].append({'relative_path':str(h.relative_to(app)),'exists':h.is_file(),'mode':oct(stat.S_IMODE(h.stat().st_mode)) if h.exists() else None})
print(json.dumps(out))
'''
metadata_outside=subprocess.run([sys.executable,'-I','-c',snapshot,str(session/'Companion.app')],cwd=session,capture_output=True,text=True,timeout=5)
environment=cli.launch_environment(session)
environment['UC_TEST_SANDBOX_DIR']=str(attempt/'profile')
environment['TMPDIR']=str(attempt/'profile/temp')
metadata_inside=subprocess.run(['/usr/bin/sandbox-exec','-f',str(attempt/'offline.sb'),sys.executable,'-I','-c',snapshot,str(session/'Companion.app')],cwd=session,env=environment,capture_output=True,text=True,timeout=5)
result={'session':str(session),'report':report,'stdout':(attempt/'stdout.log').read_text(errors='replace')[-20000:], 'outside_layout':{'exit':metadata_outside.returncode,'stdout':metadata_outside.stdout,'stderr':metadata_outside.stderr[-2000:]}, 'inside_layout':{'exit':metadata_inside.returncode,'stdout':metadata_inside.stdout,'stderr':metadata_inside.stderr[-2000:]}}
fd,output=tempfile.mkstemp(prefix='sts2test-companion-startup.',suffix='.json',dir='/private/tmp')
with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2)
os.chmod(output,0o644)
print('Diagnostic file: '+output)
PY
