"""Build a standalone native launcher with a private snapshot of the harness."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
from . import main_launcher, ui_update
from .asar import HarnessError

NAME = 'Slay the Spire 2 + Untapped.app'
REPO = Path(__file__).resolve().parents[1]


def build(destination):
    os.umask(0o077)
    root, home, _ = main_launcher._prepared()
    ui_update.selected_session(root)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise HarnessError('Launcher destination already exists; preserve the installed app')
    if not destination.parent.is_dir() or destination.parent.resolve() != destination.parent:
        raise HarnessError('Launcher destination parent must be a real directory')
    stage = Path(tempfile.mkdtemp(prefix='desktop-build-', dir=destination.parent))
    app = stage / NAME
    contents = app / 'Contents'
    executable = contents / 'MacOS/STS2Launcher'
    resources = contents / 'Resources'
    executable.parent.mkdir(parents=True)
    runtime = resources / 'runtime'
    (runtime / 'harness').mkdir(parents=True)
    for source in sorted((REPO / 'harness').iterdir()):
        if source.suffix in ('.py', '.c', '.cjs'):
            if source.is_symlink() or not source.is_file():
                raise HarnessError('Unexpected runtime source')
            shutil.copyfile(source, runtime / 'harness' / source.name)
    python = str(Path(sys.executable).resolve(strict=True))
    (resources / 'config.json').write_text(json.dumps({'python': python}))
    info = {'CFBundleExecutable': 'STS2Launcher', 'CFBundleIdentifier': 'local.untapped.sts2.launcher',
            'CFBundleName': 'Slay the Spire 2 + Untapped', 'CFBundlePackageType': 'APPL',
            'CFBundleShortVersionString': '1.0', 'CFBundleVersion': '1',
            'NSHighResolutionCapable': True, 'LSMinimumSystemVersion': '13.0'}
    # Reuse the owner's local game icon, without checking vendor artwork into Git.
    game = root / 'game/SlayTheSpire2.app/Contents'
    game_info = plistlib.loads((game / 'Info.plist').read_bytes())
    icon = game_info.get('CFBundleIconFile')
    if isinstance(icon, str) and Path(icon).name == icon:
        icon = icon if icon.endswith('.icns') else icon + '.icns'
        source = game / 'Resources' / icon
        if source.is_file() and not source.is_symlink():
            shutil.copyfile(source, resources / 'Launcher.icns')
            info['CFBundleIconFile'] = 'Launcher.icns'
    (contents / 'Info.plist').write_bytes(plistlib.dumps(info))
    subprocess.run(['/usr/bin/swiftc', '-swift-version', '5', '-module-cache-path', str(stage / 'modules'),
                    '-framework', 'Cocoa', str(REPO / 'launcher/Launcher.swift'), '-o', str(executable)], check=True)
    for p in app.rglob('*'):
        p.chmod(0o700 if p.is_dir() or p == executable else 0o600)
    app.chmod(0o700)
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', '--timestamp=none', str(app)], check=True)
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    runtime_count = len(list((runtime / 'harness').glob('*')))
    app.rename(destination)
    # The source snapshot is independent of future branch changes.
    return {'installed_app': str(destination), 'runtime_files': runtime_count,
            'launches_game_during_install': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.destination), indent=2))
        return 0
    except Exception:
        print('Launcher build stopped; existing apps were preserved.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
