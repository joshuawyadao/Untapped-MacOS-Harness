"""Select an immutable signed companion update for the macOS full-screen overlay."""
import argparse
import json
import os
import plistlib
from pathlib import Path
import re
import shutil
import tempfile

from . import cli, controlled, fullscreen_patch, login_update, signing, ui_update
from .asar import Archive, HarnessError, sha256
from .patches import CORE

DIRECTORY = 'companion-fullscreen-v1'
RECEIPT = 'companion-fullscreen-v1.json'
_ASAR = 'Contents/Resources/app.asar'
_HEX = re.compile(r'[0-9a-f]{64}\Z')


def _canonical(value):
    """Keep bool, integer and float claims distinct when comparing JSON data."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _claimed_version(manifest):
    """A missing claim is old; a malformed or future claim is never old."""
    version = manifest.get('macos_fullscreen_version')
    if version is None and 'macos_fullscreen_version' not in manifest:
        if 'macos_fullscreen_base_sha256' in manifest:
            raise HarnessError('Full-screen base hash has no version')
        return 0
    if type(version) is not int or version != fullscreen_patch.VERSION:
        raise HarnessError('Unsupported macOS full-screen update version')
    base = manifest.get('macos_fullscreen_base_sha256')
    if not isinstance(base, str) or _HEX.fullmatch(base) is None:
        raise HarnessError('Invalid macOS full-screen base hash')
    return version


def _verify_fresh_patch(source):
    """A version claim on an existing source must describe its CORE bytes."""
    core = Archive((source / 'Companion.app' / _ASAR).read_bytes()).read(CORE).decode()
    if (core.count(fullscreen_patch.WINDOW_NEW) != 1
            or fullscreen_patch.WINDOW_OLD in core):
        raise HarnessError('Claimed macOS full-screen patch is absent or duplicated')


def _complete_selection(root, source):
    from . import main_launcher
    record = main_launcher._read(root / RECEIPT)
    selected = main_launcher._private(root / DIRECTORY)
    manifest = ui_update._manifest(selected)
    base = ui_update._manifest(source)
    if (_claimed_version(base) != 0
            or _claimed_version(manifest) != fullscreen_patch.VERSION
            or type(record.get('schema')) is not int or record['schema'] != 1
            or type(record.get('version')) is not int or record['version'] != fullscreen_patch.VERSION
            or manifest.get('macos_fullscreen_base_sha256') != base.get('patched_asar_sha256')
            or record.get('base_sha256') != base.get('patched_asar_sha256')
            or record.get('patched_asar_sha256') != manifest.get('patched_asar_sha256')
            or _canonical({k: v for k, v in manifest.items() if k not in (
                'patched_asar_sha256', 'macos_fullscreen_version', 'macos_fullscreen_base_sha256')}) !=
            _canonical({k: v for k, v in base.items() if k != 'patched_asar_sha256'})
            or _canonical(main_launcher._read(selected / 'previous-signing.json')) !=
            _canonical(main_launcher._read(source / 'signing.json'))):
        raise HarnessError('Full-screen selection does not match its retained source')
    main_launcher._read(selected / 'signing.json')
    cli._validate_launch_copy(selected)
    controlled.proposal(selected)
    return selected


def selected_session(root):
    """Use only a complete, source-bound, signed layer or the signed login source."""
    source = login_update.selected_session(root)
    base = ui_update._manifest(source)
    version = _claimed_version(base)
    directory = root / DIRECTORY
    receipt = root / RECEIPT
    has_directory = directory.exists() or directory.is_symlink()
    has_receipt = receipt.exists() or receipt.is_symlink()
    if has_directory != has_receipt:
        raise HarnessError('Incomplete macOS full-screen preparation retained')
    if has_receipt:
        return _complete_selection(root, source)
    if version:
        # A freshly prepared source may already contain this repair.
        from . import main_launcher
        main_launcher._read(source / 'signing.json')
        cli._validate_launch_copy(source)
        controlled.proposal(source)
        _verify_fresh_patch(source)
    return source


def install_main():
    """Copy, repair and reseal the selected companion; publish only after checks."""
    from . import main_launcher
    root, _, _ = main_launcher._prepared()
    destination = root / DIRECTORY
    receipt = root / RECEIPT
    if receipt.exists() or receipt.is_symlink():
        selected_session(root)
        return {'macos_fullscreen_installed': True, 'already_installed': True}
    if destination.exists() or destination.is_symlink():
        raise HarnessError('Incomplete macOS full-screen preparation retained')
    source = login_update.selected_session(root)
    original_manifest = ui_update._manifest(source)
    version = _claimed_version(original_manifest)
    main_launcher._read(source / 'signing.json')
    cli._validate_launch_copy(source)
    controlled.proposal(source)
    if version:
        _verify_fresh_patch(source)
        return {'macos_fullscreen_installed': True, 'already_installed': True}
    before = ui_update._tree(source / 'Companion.app')
    stage = Path(tempfile.mkdtemp(prefix='fullscreen-preparation-', dir=root))
    shutil.copytree(source / 'Companion.app', stage / 'Companion.app', symlinks=True)
    for name in ('manifest.json', 'signing.json'):
        shutil.copy2(source / name, stage / name, follow_symlinks=False)
    ui_update._only_changes(before, ui_update._tree(stage / 'Companion.app'), set())
    target = stage / 'Companion.app' / _ASAR
    archive = Archive(target.read_bytes())
    patched_core = fullscreen_patch.patch_core(archive.read(CORE).decode()).encode()
    result = archive.rewrite({CORE: patched_core})
    if Archive(result).read(CORE) != patched_core:
        raise HarnessError('Full-screen archive rewrite did not verify')
    target.write_bytes(result)
    manifest = {**original_manifest,
                'patched_asar_sha256': sha256(result),
                'macos_fullscreen_version': fullscreen_patch.VERSION,
                'macos_fullscreen_base_sha256': original_manifest['patched_asar_sha256']}
    (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (stage / 'signing.json').rename(stage / 'previous-signing.json')
    ui_update._only_changes(before, ui_update._tree(stage / 'Companion.app'), {_ASAR})
    signing._entitlements(stage / 'Companion.app')
    entitlements = stage / 'entitlements.plist'
    entitlements.write_bytes(plistlib.dumps(signing.ENTITLEMENTS))
    signing._run_codesign(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                           '--timestamp=none', '--entitlements', str(entitlements),
                           str(stage / 'Companion.app')])
    signing.verify_signed_copy(stage)
    ui_update._only_changes(before, ui_update._tree(stage / 'Companion.app'),
                            {_ASAR, 'Contents/' + signing.EXECUTABLE,
                             'Contents/_CodeSignature/CodeResources'})
    executable_hash = sha256((stage / 'Companion.app/Contents' / signing.EXECUTABLE).read_bytes())
    signing._check_payloads(stage, manifest, executable_hash)
    previous = main_launcher._read(stage / 'previous-signing.json')
    main_launcher._write(stage / 'signing.json', {**previous,
        'patched_asar_sha256': manifest['patched_asar_sha256'],
        'signed_executable_sha256': executable_hash})
    cli._validate_launch_copy(stage)
    controlled.proposal(stage)
    cli._validate_launch_copy(source)
    ui_update._only_changes(before, ui_update._tree(source / 'Companion.app'), set())
    if (login_update.selected_session(root) != source
            or _canonical(ui_update._manifest(source)) != _canonical(original_manifest)
            or _canonical(main_launcher._read(source / 'signing.json')) != _canonical(previous)):
        raise HarnessError('Full-screen source changed during preparation')
    main_launcher._write(stage / 'selection.json', {
        'schema': 1, 'version': fullscreen_patch.VERSION,
        'base_sha256': original_manifest['patched_asar_sha256'],
        'patched_asar_sha256': manifest['patched_asar_sha256']})
    stage.rename(destination)
    (destination / 'selection.json').rename(receipt)
    selected_session(root)
    return {'macos_fullscreen_installed': True, 'effective': 'NEXT_LAUNCH',
            'game_modified': False, 'credentials_saved': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-main', action='store_true', required=True)
    parser.parse_args()
    os.umask(0o077)
    try:
        print(json.dumps(install_main(), indent=2))
        return 0
    except Exception:
        print('Full-screen preparation stopped; private evidence retained.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
