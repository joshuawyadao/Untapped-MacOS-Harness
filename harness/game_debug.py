"""Explicit proposal/signing for a separate disposable debugger-enabled game copy."""
import argparse
import json
import os
import platform
import plistlib
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from . import game_launch as game
from .asar import HarnessError, sha256

# Complete original tree (file bytes/modes and symlink text), verified locally.
ORIGINAL_TREE_SHA256 = "4892eb6c03ae851fde4f075c5ca75d9db827b84b2c651bcc9b5e62cd41add85e"
SCOPE = "outer-debug-game-copy-only"
APP = "SlayTheSpire2.app"
TEST_SESSION = "UntappedSTS2DebugGameSession"
BASE = "debug-game.json"
RECEIPT = "debug-game-signing.json"
ENTITLEMENTS = {
    "com.apple.security.cs.allow-dyld-environment-variables": True,
    "com.apple.security.cs.allow-jit": True,
    "com.apple.security.cs.allow-unsigned-executable-memory": True,
    "com.apple.security.cs.disable-library-validation": True,
}
DEBUG_ENTITLEMENTS = {**ENTITLEMENTS, "com.apple.security.get-task-allow": True}
SIGNING_FILES = {game.EXECUTABLE, "Contents/_CodeSignature/CodeResources"}


def _command(command):
    try:
        result = subprocess.run(command, capture_output=True, timeout=30, check=False,
                                env={"PATH": "/usr/bin:/bin", "LANG": "C"})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HarnessError("Game signing inspection unavailable or timed out") from exc
    if result.returncode:
        raise HarnessError("Game codesign failed: " + result.stderr.decode(errors="replace")[-1000:])
    return result


def _root(session):
    path = Path(session).absolute()
    if (platform.system() != "Darwin" or os.getuid() == 0 or os.getuid() != os.geteuid()
            or path.resolve(strict=True) != path or path.is_symlink()
            or path.is_relative_to(game.ROOT)):
        raise HarnessError("Game signing requires an unprivileged private disposable session")
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise HarnessError("Game proposal session must be owned and mode 0700")
    return path


def _json(session, name):
    path = session / name
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise HarnessError("Game proposal metadata is missing or redirected")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise HarnessError("Invalid game proposal metadata")
    return value


def _settings(app, expected):
    for arch in ("arm64", "x86_64"):
        raw = _command(["/usr/bin/codesign", "-d", "--entitlements", ":-", "--arch", arch, str(app)])
        if plistlib.loads(raw.stdout) != expected:
            raise HarnessError("Game entitlements differ from exact expected settings")
        raw = _command(["/usr/bin/codesign", "-dvv", "--arch", arch, str(app)])
        if b"runtime)" not in raw.stderr or b"Signature=adhoc" not in raw.stderr:
            raise HarnessError("Game must retain ad-hoc signing and Hardened Runtime")


def _baseline(session):
    manifest = _json(session, BASE)
    if (manifest.get("schema") != 1 or manifest.get("scope") != SCOPE
            or manifest.get("game_version") != game.VERSION or manifest.get("commit") != game.COMMIT
            or manifest.get("original_entitlements") != ENTITLEMENTS
            or not isinstance(manifest.get("source_files"), dict)
            or manifest.get("source_tree_sha256") != ORIGINAL_TREE_SHA256
            or manifest.get("source_tree_sha256") != _tree_hash(manifest["source_files"])
            or manifest["source_files"].get(game.ASSEMBLY, {}).get("sha256") != game.ASSEMBLY_HASH):
        raise HarnessError("Game baseline is not the pinned original build")
    source = Path(manifest["source_app"])
    app = session / APP
    if not source.is_absolute() or source == app or source.is_relative_to(session):
        raise HarnessError("Game baseline source overlaps disposable session")
    return manifest


def _tree_hash(files):
    return sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())


def prepare(source, session):
    source = Path(source).absolute()
    session = Path(session).absolute()
    if (platform.system() != "Darwin" or os.getuid() == 0 or os.getuid() != os.geteuid()
            or session.exists() or session.is_symlink() or session.resolve() != session
            or session.is_relative_to(game.ROOT) or session.is_relative_to(source)
            or source.is_relative_to(session)):
        raise HarnessError("Use a fresh separate disposable game session outside the repository")
    files = game.verified_app(source)
    if _tree_hash(files) != ORIGINAL_TREE_SHA256:
        raise HarnessError("Original game tree differs from the complete pinned source")
    _settings(source, ENTITLEMENTS)
    session.mkdir(mode=0o700)
    shutil.copytree(source, session / APP, symlinks=True)
    if game.verified_app(session / APP) != files or game.tree_manifest(source) != files:
        raise HarnessError("New game copy or source changed during preparation")
    manifest = {"schema": 1, "scope": SCOPE, "game_version": game.VERSION, "commit": game.COMMIT,
                "source_app": str(source), "source_files": files,
                "source_tree_sha256": _tree_hash(files), "original_entitlements": ENTITLEMENTS}
    game.write_json(session / BASE, manifest)
    return proposal(session)


def proposal(session):
    session = _root(session)
    if (session / RECEIPT).exists() or (session / RECEIPT).is_symlink() or (session / "manifest.json").exists() or (session / "manifest.json").is_symlink():
        raise HarnessError("Proposal requires an unsigned, uninstalled new game copy")
    manifest = _baseline(session)
    app = session / APP
    if game.verified_app(app) != manifest["source_files"]:
        raise HarnessError("Unsigned game copy differs from its original baseline")
    _settings(app, ENTITLEMENTS)
    path = session / "debug-game-entitlements.plist"
    if path.is_symlink() or (path.exists() and path.stat().st_nlink != 1):
        raise HarnessError("Entitlement proposal is redirected")
    temporary = session / "debug-game-entitlements.plist.tmp"
    with temporary.open("xb") as stream:
        stream.write(plistlib.dumps(DEBUG_ENTITLEMENTS))
    os.replace(temporary, path)
    path.chmod(0o600)
    return {"schema": 1, "scope": SCOPE, "target": str(app),
            "command": ["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime",
                        "--timestamp=none", "--entitlements", str(path), str(app)],
            "source_tree_sha256": manifest["source_tree_sha256"],
            "original_entitlements": ENTITLEMENTS, "proposed_entitlements": DEBUG_ENTITLEMENTS,
            "signing_executed": False, "requires_explicit_owner_approval": True,
            "allowed_changed_files": sorted(SIGNING_FILES),
            "installed_game_modified": False, "nested_code_resigned": False}


def _allowed_changes(original, signed):
    if original.keys() != signed.keys():
        raise HarnessError("Signing added or removed a game entry")
    changed = {name for name in original if original[name] != signed[name]}
    if not changed or not changed <= SIGNING_FILES or game.EXECUTABLE not in changed:
        raise HarnessError("Game changes exceed the outer signing scope")
    for name in changed:
        if (set(original[name]) != {"sha256", "mode"} or set(signed[name]) != {"sha256", "mode"}
                or original[name]["mode"] != signed[name]["mode"]):
            raise HarnessError("Game signing changed file type or mode")
    return sorted(changed)


def sign(session, *, approved=False):
    if not approved:
        raise HarnessError("Explicit owner approval required for this game-copy signing")
    proposed = proposal(session)
    session = _root(session)
    manifest = _baseline(session)
    _command(proposed["command"])
    files = game.verified_app(session / APP)
    _settings(session / APP, DEBUG_ENTITLEMENTS)
    changed = _allowed_changes(manifest["source_files"], files)
    receipt = {"schema": 1, "scope": SCOPE, "source_tree_sha256": manifest["source_tree_sha256"],
               "entitlements": DEBUG_ENTITLEMENTS, "hardened_runtime": True,
               "nested_code_resigned": False, "changed_files": changed, "signed_files": files}
    with (session / RECEIPT).open("x") as stream:
        json.dump(receipt, stream, indent=2)
    (session / RECEIPT).chmod(0o600)
    return receipt


def verify(session):
    session = _root(session)
    manifest = _baseline(session)
    receipt = _json(session, RECEIPT)
    if (receipt.get("schema") != 1 or receipt.get("scope") != SCOPE
            or receipt.get("source_tree_sha256") != manifest["source_tree_sha256"]
            or receipt.get("entitlements") != DEBUG_ENTITLEMENTS
            or receipt.get("hardened_runtime") is not True or receipt.get("nested_code_resigned") is not False
            or not isinstance(receipt.get("signed_files"), dict)):
        raise HarnessError("Debug-game signing receipt does not match baseline")
    changed = _allowed_changes(manifest["source_files"], receipt["signed_files"])
    if receipt.get("changed_files") != changed:
        raise HarnessError("Debug-game changed-file receipt is invalid")
    if game.verified_app(session / APP) != receipt["signed_files"]:
        raise HarnessError("Signed debug game changed after receipt")
    _settings(session / APP, DEBUG_ENTITLEMENTS)
    return receipt["signed_files"]


def install(source, session):
    name, home, original = game.test_identity("sts2test", game.PROTECTED_HOME)
    source = _root(source)
    session = game.private_path(session, home)
    if session != home / TEST_SESSION or session.exists() or session.is_symlink():
        raise HarnessError("Install only into the new dedicated debug-game session")
    files = verify(source)
    session.mkdir(mode=0o700)
    shutil.copytree(source / APP, session / APP, symlinks=True)
    for filename in (BASE, RECEIPT):
        shutil.copyfile(source / filename, session / filename)
    if verify(session) != files:
        raise HarnessError("Installed debug game differs from signed transfer")
    manifest = {"schema": 1, "game_version": game.VERSION, "commit": game.COMMIT,
                "test_user": name, "test_uid": os.getuid(), "test_home": str(home),
                "original_home": str(original), "source_app": str(source / APP), "files": files,
                "game_modified": True, "game_signed": True, "debug_game": True}
    game.write_json(session / "manifest.json", manifest)
    return {"session": str(session), "file_count": len(files), "debug_game": True}


def verify_launch(session, manifest, home):
    session = game.private_path(session, home)
    if (session != home / TEST_SESSION or manifest.get("debug_game") is not True
            or manifest.get("game_signed") is not True or manifest.get("game_modified") is not True
            or manifest.get("test_uid") != os.getuid() or manifest.get("test_home") != str(home)
            or manifest.get("test_user") != "sts2test"
            or manifest.get("original_home") != str(game.PROTECTED_HOME.resolve(strict=True))):
        raise HarnessError("Debug-game launch requires the exact installed test session and identity")
    files = verify(session)
    if manifest.get("files") != files:
        raise HarnessError("Debug-game launch manifest differs from signing receipt")
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("source", type=Path); prep.add_argument("session", type=Path)
    for name in ("proposal", "sign", "verify"):
        command = sub.add_parser(name); command.add_argument("session", type=Path)
        if name == "sign": command.add_argument("--approve-debug-game-signing", action="store_true")
    command = sub.add_parser("install")
    command.add_argument("source", type=Path); command.add_argument("session", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare": result = prepare(args.source, args.session)
        elif args.command == "proposal": result = proposal(args.session)
        elif args.command == "sign":
            receipt = sign(args.session, approved=args.approve_debug_game_signing)
            result = {"scope": SCOPE, "receipt": str(args.session / RECEIPT),
                      "changed_files": receipt["changed_files"],
                      "signed_file_count": len(receipt["signed_files"]),
                      "entitlements": receipt["entitlements"], "hardened_runtime": True}
        elif args.command == "install": result = install(args.source, args.session)
        else: result = {"verified": True, "file_count": len(verify(args.session))}
        print(json.dumps(result, indent=2))
        return 0
    except (HarnessError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print("Debug-game operation stopped: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
