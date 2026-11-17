"""Publish an exact reviewed game copy without replacing legacy activation data."""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from . import game_debug, main_account
from .asar import HarnessError, sha256
from .game_builds import V0_111_1

BUILD = V0_111_1
DIRECTORY = 'game-v0.111.1'
RECEIPT = 'game-v0.111.1.json'
BASE_RECORDS = ('main-launch.json', 'main-proposal.json', 'activation.json',
                'game/debug-game.json', 'game/debug-game-signing.json')


def _metadata_hash(path):
    from . import main_launcher
    value = main_launcher._read(path)
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=True).encode())


def _lineage(root):
    return {name: _metadata_hash(root / name) for name in BASE_RECORDS}


def selected_game(root):
    """Resolve fixed paths and receipt lineage; callers verify the selected payload."""
    from . import main_launcher
    root = main_launcher._private(Path(root))
    selected = root / DIRECTORY
    receipt = root / RECEIPT
    directory_present = selected.exists() or selected.is_symlink()
    receipt_present = receipt.exists() or receipt.is_symlink()
    if directory_present != receipt_present:
        raise HarnessError('Incomplete reviewed game update retained')
    if not receipt_present:
        return root / 'game', None
    main_launcher._private(selected)
    record = main_launcher._read(receipt)
    expected = {'schema': 1, 'approved': True, 'game_version': BUILD.version,
                'commit': BUILD.commit, 'source_tree_sha256': BUILD.tree_sha256,
                'lineage': _lineage(root),
                'signed_receipt_sha256': _metadata_hash(selected / game_debug.RECEIPT),
                'baseline_sha256': _metadata_hash(selected / game_debug.BASE)}
    # Canonical JSON retains bool/int/float distinctions in schema and lineage.
    if (type(record.get('schema')) is not int or record.get('approved') is not True
            or json.dumps(record, sort_keys=True, separators=(',', ':')) !=
            json.dumps(expected, sort_keys=True, separators=(',', ':'))):
        raise HarnessError('Reviewed game update receipt or retained lineage changed')
    return selected, BUILD


def verify_selected_game(root):
    selected, build = selected_game(root)
    if build is None:
        game_debug.verify(selected)
    else:
        game_debug.verify(selected, build=build)
    return selected, build


def install_main(*, approved=False):
    """Copy/sign the reviewed build; publish its receipt last under the desktop lock."""
    if not approved:
        raise HarnessError('Explicit approval required for the reviewed game-copy update')
    from . import desktop_launcher, main_launcher
    os.umask(0o077)
    uid, home = main_launcher.account()
    root = main_launcher._private(home / main_launcher.WORKSPACE_RELATIVE)
    with desktop_launcher.session_lock(root):
        main_launcher._closed()
        binding = main_launcher._binding(root, uid, home)
        steam_id, profile = main_launcher._progress(home / main_account.DATA_RELATIVE, binding.get('profile'))
        if steam_id != binding.get('steam_id') or profile != binding.get('profile'):
            raise HarnessError('Existing Steam/profile binding changed')
        activation = main_launcher._read(root / 'activation.json')
        main_launcher._read(root / 'main-proposal.json')
        if (type(activation.get('schema')) is not int or activation['schema'] != 1
                or activation.get('copied_apps_signed') is not True
                or activation.get('proposal_sha256') != sha256((root / 'main-proposal.json').read_bytes())):
            raise HarnessError('Retained activation does not match its proposal')
        selected, build = selected_game(root)
        if build is not None:
            verify_selected_game(root)
            main_launcher._source(home, build=BUILD)
            return {'game_update_installed': True, 'already_installed': True,
                    'game_version': BUILD.version, 'progress_modified': False}
        game_debug.verify(selected)
        source = main_launcher._source(home, build=BUILD)
        lineage = _lineage(root)
        stage = Path(tempfile.mkdtemp(prefix='game-update-', dir=root))
        try:
            payload = stage / 'payload'
            game_debug.prepare(source, payload, build=BUILD)
            game_debug.sign(payload, approved=True, build=BUILD)
            game_debug.verify(payload, build=BUILD)
            main_launcher._source(home, build=BUILD)
            main_launcher._closed()
            if _lineage(root) != lineage:
                raise HarnessError('Retained launch records changed during game preparation')
            record = {'schema': 1, 'approved': True, 'game_version': BUILD.version,
                      'commit': BUILD.commit, 'source_tree_sha256': BUILD.tree_sha256,
                      'lineage': lineage,
                      'signed_receipt_sha256': _metadata_hash(payload / game_debug.RECEIPT),
                      'baseline_sha256': _metadata_hash(payload / game_debug.BASE)}
            main_launcher._write(stage / 'selection.json', record)
            if any(path.exists() or path.is_symlink() for path in (root / DIRECTORY, root / RECEIPT)):
                raise HarnessError('Game update publication destination already exists')
            payload.rename(root / DIRECTORY)
            (stage / 'selection.json').rename(root / RECEIPT)
            verify_selected_game(root)
        finally:
            shutil.rmtree(stage)
    return {'game_update_installed': True, 'already_installed': False,
            'game_version': BUILD.version, 'progress_modified': False,
            'installed_game_modified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-main', action='store_true', required=True)
    parser.add_argument('--approve-debug-game-signing', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(install_main(approved=args.approve_debug_game_signing), indent=2))
        return 0
    except Exception:
        print('Reviewed game update stopped; existing game/progress were preserved.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
