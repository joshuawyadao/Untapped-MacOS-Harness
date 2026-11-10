"""Install an offline UI repair derived from the already verified companion copy."""
import argparse
import json
import os
import plistlib
import shutil
import stat
import tempfile
from pathlib import Path

from . import cli, controlled, signing
from .asar import HarnessError, sha256

UPDATE_DIRECTORY = 'companion-ui'
RECEIPT = 'companion-ui.json'
CURRENT_DIRECTORY = 'companion-ui-v2'
CURRENT_RECEIPT = 'companion-ui-v2.json'


def _manifest(session):
    from . import main_launcher
    return main_launcher._read(session / 'manifest.json')


def _matches(manifest, base):
    return (type(manifest.get('ui_assets_version')) is int
            and manifest['ui_assets_version'] in (1, 2)
            and manifest.get('base_patched_asar_sha256') == base.get('patched_asar_sha256')
            and all(manifest.get(key) == base.get(key) for key in (
                'main_steam_guard_version', 'controlled_access_version',
                'controlled_gateway_sha256', 'controlled_network_sha256')))


def selected_session(root):
    """Select only a complete, signed update bound to the retained original."""
    from . import main_launcher
    base = root / 'companion'
    current = root / CURRENT_RECEIPT
    is_current = current.exists() or current.is_symlink()
    receipt = current if is_current else root / RECEIPT
    if not receipt.exists() and not receipt.is_symlink():
        return base
    record = main_launcher._read(receipt)
    version = 2 if is_current else 1
    record_version = record.get('ui_assets_version', None if is_current else 1)
    updated = main_launcher._private(root / (CURRENT_DIRECTORY if is_current else UPDATE_DIRECTORY))
    manifest = _manifest(updated)
    if (type(record_version) is not int or record_version != version
            or manifest.get('ui_assets_version') != version
            or record.get('schema') != 1 or not _matches(manifest, _manifest(base))
            or record.get('patched_asar_sha256') != manifest.get('patched_asar_sha256')
            or record.get('base_patched_asar_sha256') != manifest.get('base_patched_asar_sha256')):
        raise HarnessError('UI update receipt does not match the original companion')
    controlled.proposal(updated)
    main_launcher._read(updated / 'signing.json')
    cli._validate_launch_copy(updated)
    return updated


def _tree(app):
    """Compare copied payloads including symlink targets without following them."""
    result = {}
    for path in app.rglob('*'):
        info = path.lstat()
        relative = str(path.relative_to(app))
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISLNK(info.st_mode):
            result[relative] = ('link', mode, os.readlink(path))
        elif stat.S_ISDIR(info.st_mode):
            result[relative] = ('directory', mode)
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            result[relative] = ('file', mode, sha256(path.read_bytes()))
        else:
            raise HarnessError('Unsupported companion payload')
    return result


def _only_changes(before, after, allowed):
    if before.keys() != after.keys():
        raise HarnessError('UI update changed the companion file set')
    if any(before[name] != after[name] for name in before if name not in allowed):
        raise HarnessError('UI update changed an unrelated companion payload')
    if any(before[name][:2] != after[name][:2] for name in allowed):
        raise HarnessError('UI update changed a payload type or mode')


def install_main():
    """Explicit owner-requested UI repair; no game process or save operations."""
    from . import main_launcher, ui_assets
    root, _, _ = main_launcher._prepared()
    if not (root / 'activation.json').is_file():
        raise HarnessError('Activate the existing main setup before installing a UI update')
    source = selected_session(root)
    if _manifest(source).get('ui_assets_version') == ui_assets.VERSION:
        return {'ui_update_installed': True, 'already_installed': True}
    destination = root / CURRENT_DIRECTORY
    if destination.exists() or destination.is_symlink():
        raise HarnessError('An incomplete UI update exists; preserve it for inspection')
    base = root / 'companion'
    base_manifest = _manifest(base)
    controlled.proposal(base)
    cli._validate_launch_copy(base)
    controlled.proposal(source)
    main_launcher._read(source / 'signing.json')
    cli._validate_launch_copy(source)
    before = _tree(source / 'Companion.app')
    stage = Path(tempfile.mkdtemp(prefix='ui-preparation-', dir=root))
    # Failed preparations remain private and never become the selected companion.
    shutil.copytree(source / 'Companion.app', stage / 'Companion.app', symlinks=True)
    for name in ('manifest.json', 'signing.json'):
        shutil.copy2(source / name, stage / name, follow_symlinks=False)
    _only_changes(before, _tree(stage / 'Companion.app'), set())
    ui_assets.prepare(stage)
    manifest = _manifest(stage)
    if manifest.get('ui_assets_version') != ui_assets.VERSION or not _matches(manifest, base_manifest):
        raise HarnessError('UI assets changed the controlled policy or base binding')
    asar = 'Contents/Resources/app.asar'
    _only_changes(before, _tree(stage / 'Companion.app'), {asar})
    # The source is an already locally signed, verified copy. Preserve exactly its
    # five reviewed entitlements, native payloads and runtime flags when resealing.
    signing._entitlements(stage / 'Companion.app')
    entitlements = stage / 'companion-entitlements.plist'
    entitlements.write_bytes(plistlib.dumps(signing.ENTITLEMENTS))
    entitlements.chmod(0o600)
    signing._run_codesign(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
        '--timestamp=none', '--entitlements', str(entitlements), str(stage / 'Companion.app')])
    signing.verify_signed_copy(stage)
    _only_changes(before, _tree(stage / 'Companion.app'), {
        asar, 'Contents/' + signing.EXECUTABLE, 'Contents/_CodeSignature/CodeResources'})
    signed_hash = sha256((stage / 'Companion.app/Contents' / signing.EXECUTABLE).read_bytes())
    signing._check_payloads(stage, manifest, signed_hash)
    receipt = {'schema': 1, 'scope': signing.SCOPE,
        'original_executable_sha256': signing.EXECUTABLE_SHA256,
        'patched_asar_sha256': manifest['patched_asar_sha256'],
        'signed_executable_sha256': signed_hash, 'entitlements': signing.ENTITLEMENTS,
        'signature': 'ad-hoc', 'hardened_runtime': True,
        'game_modified': False, 'nested_code_resigned': False}
    # The asset preparer must archive the previous receipt before modifying ASAR.
    main_launcher._write(stage / 'signing.json', receipt)
    cli._validate_launch_copy(stage)
    controlled.proposal(stage)
    # Revalidate the source after the potentially slow public-asset downloads.
    cli._validate_launch_copy(source)
    controlled.proposal(source)
    _only_changes(before, _tree(source / 'Companion.app'), set())
    cli._validate_launch_copy(base)
    controlled.proposal(base)
    if _manifest(base) != base_manifest or selected_session(root) != source:
        raise HarnessError('UI update source changed during preparation')
    # A separate immutable receipt leaves the legacy selection available until
    # the complete version-2 payload and receipt are published. Directory rename
    # also prevents concurrent preparations from replacing the same destination.
    main_launcher._write(stage / 'selection.json', {'schema': 1,
        'ui_assets_version': ui_assets.VERSION,
        'base_patched_asar_sha256': manifest['base_patched_asar_sha256'],
        'patched_asar_sha256': manifest['patched_asar_sha256']})
    stage.rename(destination)
    if (root / CURRENT_RECEIPT).exists() or (root / CURRENT_RECEIPT).is_symlink():
        raise HarnessError('UI update selection already exists')
    (destination / 'selection.json').rename(root / CURRENT_RECEIPT)
    selected_session(root)
    return {'ui_update_installed': True, 'ui_assets_version': ui_assets.VERSION, 'effective': 'NEXT_MAIN_LAUNCH',
            'current_session_changed': False, 'game_or_saves_modified': False,
            'runtime_network_expanded': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-main', action='store_true', required=True)
    parser.parse_args()
    os.umask(0o077)
    try:
        print(json.dumps(install_main(), indent=2))
    except Exception:
        print('UI update was not activated. Private preparation is retained for inspection.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
