"""Select a signed opt-in credential bridge derived from the retained UI copy."""
import argparse
import json
import os
import plistlib
from pathlib import Path
import shutil
import tempfile
from . import cli, controlled, signing, ui_update, remember_patch
from .asar import Archive, HarnessError, sha256
from .patches import MAIN

DIRECTORY = 'companion-login-v2'
RECEIPT = 'companion-login-v2.json'
LEGACY_DIRECTORY = 'companion-login-v1'
LEGACY_RECEIPT = 'companion-login-v1.json'
LEGACY_HELPER_SHA256 = '26dbd6a0c6473bcf6a4a15610549ea1aa1bbd95655339c6daa5552de8b8e7a6e'


def helper_hash():
    return sha256(Path(__file__).with_name('remember_keytar.cjs').read_bytes())


def _selected(root, source, directory, receipt_name, expected_helper_hash, revision):
    from . import main_launcher
    receipt = root / receipt_name
    if not receipt.exists() and not receipt.is_symlink():
        return None
    record = main_launcher._read(receipt)
    selected = main_launcher._private(root / directory)
    manifest = ui_update._manifest(selected)
    base = ui_update._manifest(source)
    if (type(record.get('schema')) is not int or record['schema'] != 1
            or (revision == 2 and (type(record.get('revision')) is not int
                                  or record['revision'] != 2))
            or type(manifest.get('remember_login_version')) is not int or manifest['remember_login_version'] != 1
            or (revision == 2 and (type(manifest.get('remember_login_revision')) is not int
                                  or manifest['remember_login_revision'] != 2))
            or manifest.get('remember_login_base_sha256') != base.get('patched_asar_sha256')
            or record.get('base_sha256') != manifest.get('remember_login_base_sha256')
            or record.get('patched_asar_sha256') != manifest.get('patched_asar_sha256')
            or manifest.get('remember_login_helper_sha256') != expected_helper_hash
            or any(manifest.get(k) != base.get(k) for k in ('ui_assets_version', 'base_patched_asar_sha256',
                   'main_steam_guard_version', 'controlled_access_version', 'controlled_gateway_sha256',
                   'controlled_network_sha256'))):
        raise HarnessError('Remember-login selection does not match its retained source')
    main_launcher._read(selected / 'signing.json')
    cli._validate_launch_copy(selected)
    controlled.proposal(selected)
    return selected


def selected_session(root):
    source = ui_update.selected_session(root)
    if ((root / DIRECTORY).exists() or (root / DIRECTORY).is_symlink()) and not (
            (root / RECEIPT).exists() or (root / RECEIPT).is_symlink()):
        raise HarnessError('Incomplete remember-login preparation retained')
    current = _selected(root, source, DIRECTORY, RECEIPT, helper_hash(), 2)
    if current is not None:
        return current
    # A retained v1 selection is inspectable for migration, but its helper pin
    # cannot authorize a launch with the new proxy implementation.
    if (root / LEGACY_RECEIPT).exists() or (root / LEGACY_RECEIPT).is_symlink():
        _selected(root, source, LEGACY_DIRECTORY, LEGACY_RECEIPT,
                  LEGACY_HELPER_SHA256, 1)
    return source


def install_main():
    from . import main_launcher
    root, _, _ = main_launcher._prepared()
    if (root / RECEIPT).exists() or (root / RECEIPT).is_symlink():
        selected_session(root)
        return {'remember_login_installed': True, 'already_installed': True}
    destination = root / DIRECTORY
    if destination.exists() or destination.is_symlink():
        raise HarnessError('Incomplete remember-login preparation retained')
    source = ui_update.selected_session(root)
    if (root / LEGACY_RECEIPT).exists() or (root / LEGACY_RECEIPT).is_symlink():
        _selected(root, source, LEGACY_DIRECTORY, LEGACY_RECEIPT,
                  LEGACY_HELPER_SHA256, 1)
    original_manifest = ui_update._manifest(source)
    if original_manifest.get('remember_login_version') == 1:
        if original_manifest.get('remember_login_helper_sha256') != helper_hash():
            raise HarnessError('Remember-login helper changed')
        return {'remember_login_installed': True, 'already_installed': True}
    main_launcher._read(source / 'signing.json')
    cli._validate_launch_copy(source)
    controlled.proposal(source)
    before = ui_update._tree(source / 'Companion.app')
    stage = Path(tempfile.mkdtemp(prefix='login-preparation-', dir=root))
    shutil.copytree(source / 'Companion.app', stage / 'Companion.app', symlinks=True)
    for name in ('manifest.json', 'signing.json'):
        shutil.copy2(source / name, stage / name, follow_symlinks=False)
    ui_update._only_changes(before, ui_update._tree(stage / 'Companion.app'), set())
    target = stage / 'Companion.app/Contents/Resources/app.asar'
    archive = Archive(target.read_bytes())
    patched_main = remember_patch.inject(archive.read(MAIN).decode()).encode()
    result = archive.rewrite({MAIN: patched_main})
    if Archive(result).read(MAIN) != patched_main:
        raise HarnessError("Remember-login archive rewrite did not verify")
    target.write_bytes(result)
    manifest = {**original_manifest, 'patched_asar_sha256': sha256(result),
                'remember_login_version': 1, 'remember_login_helper_sha256': helper_hash(),
                'remember_login_revision': 2,
                'remember_login_base_sha256': original_manifest['patched_asar_sha256']}
    (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (stage / 'signing.json').rename(stage / 'previous-signing.json')
    asar = 'Contents/Resources/app.asar'
    ui_update._only_changes(before, ui_update._tree(stage / 'Companion.app'), {asar})
    signing._entitlements(stage / 'Companion.app')
    entitlements = stage / 'entitlements.plist'
    entitlements.write_bytes(plistlib.dumps(signing.ENTITLEMENTS))
    signing._run_codesign(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                          '--timestamp=none', '--entitlements', str(entitlements), str(stage/'Companion.app')])
    signing.verify_signed_copy(stage)
    ui_update._only_changes(before, ui_update._tree(stage / 'Companion.app'),
                            {asar, 'Contents/'+signing.EXECUTABLE, 'Contents/_CodeSignature/CodeResources'})
    executable_hash = sha256((stage/'Companion.app/Contents'/signing.EXECUTABLE).read_bytes())
    signing._check_payloads(stage, manifest, executable_hash)
    previous = main_launcher._read(stage/'previous-signing.json')
    main_launcher._write(stage/'signing.json', {**previous, 'patched_asar_sha256': manifest['patched_asar_sha256'],
                                             'signed_executable_sha256': executable_hash})
    cli._validate_launch_copy(stage)
    controlled.proposal(stage)
    cli._validate_launch_copy(source)
    ui_update._only_changes(before, ui_update._tree(source/'Companion.app'), set())
    if ui_update.selected_session(root) != source or ui_update._manifest(source) != original_manifest:
        raise HarnessError('Remember-login source changed during preparation')
    main_launcher._write(stage/'selection.json', {'schema': 1, 'revision': 2,
        'base_sha256': original_manifest['patched_asar_sha256'], 'patched_asar_sha256': manifest['patched_asar_sha256']})
    stage.rename(destination)
    (destination/'selection.json').rename(root/RECEIPT)
    selected_session(root)
    return {'remember_login_installed': True, 'effective': 'NEXT_LAUNCH',
            'credentials_saved': False, 'runtime_network_expanded': False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-main', action='store_true', required=True)
    parser.parse_args()
    os.umask(0o077)
    try:
        print(json.dumps(install_main(), indent=2))
        return 0
    except Exception:
        print('Remember-login preparation stopped; private evidence retained.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
