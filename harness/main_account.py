"""Read-only, fixed-field readiness inspection for eventual main-account play."""

import argparse
import hashlib
import itertools
import json
import os
import platform
import pwd
import stat
import sys
from pathlib import Path

from . import game_launch


GAME_RELATIVE = Path("Library/Application Support/Steam/steamapps/common/Slay the Spire 2/SlayTheSpire2.app")
DATA_RELATIVE = Path("Library/Application Support/SlayTheSpire2")
RELEASE_RELATIVE = Path("Contents/Resources/release_info.json")
LIMIT_PER_DIRECTORY = 64
LIMIT_TOTAL = 256
MAX_ASSEMBLY_BYTES = 256 * 1024 * 1024


def _open_directory(path, uid=None):
    """Walk from the filesystem root with no-follow directory descriptors."""
    path = Path(path).absolute()
    descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        if uid is not None and os.fstat(descriptor).st_uid != uid:
            raise PermissionError("Wrong owner")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _directory_status(path, uid=None):
    """Check every component without following a link; open only the final directory."""
    path = Path(path).absolute()
    current = Path(path.anchor)
    info = current.lstat()
    for part in path.parts[1:]:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return "ABSENT"
        except OSError:
            return "INACCESSIBLE"
        if stat.S_ISLNK(info.st_mode):
            return "REDIRECTED"
        if not stat.S_ISDIR(info.st_mode):
            return "UNSUPPORTED"
    if uid is not None and info.st_uid != uid:
        return "WRONG_OWNER"
    try:
        descriptor = _open_directory(path, uid)
        os.close(descriptor)
    except OSError:
        return "INACCESSIBLE"
    return "DIRECTORY"


def _read_vendor_file(app, relative, *, limit, digest=False):
    """Read only fixed vendor files through directory descriptors without links."""
    descriptor = _open_directory(app)
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                  dir_fd=descriptor)
        try:
            info = os.fstat(file_descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
                raise ValueError("Unsupported vendor file")
            with os.fdopen(file_descriptor, "rb", closefd=False) as source:
                if not digest:
                    return source.read(limit + 1)
                value = hashlib.sha256()
                total = 0
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    total += len(block)
                    if total > limit:
                        raise ValueError("Unsupported vendor file")
                    value.update(block)
                return value.hexdigest()
        finally:
            os.close(file_descriptor)
    finally:
        os.close(descriptor)


def _game_build(app):
    status = _directory_status(app)
    if status != "DIRECTORY":
        return status
    try:
        release_bytes = _read_vendor_file(app, RELEASE_RELATIVE, limit=8192)
        if len(release_bytes) > 8192:
            return "UNSUPPORTED"
        release = json.loads(release_bytes.decode("utf-8"))
        if (not isinstance(release, dict) or release.get("version") != game_launch.VERSION
                or release.get("commit") != game_launch.COMMIT):
            return "MISMATCH"
        assembly_hash = _read_vendor_file(app, Path(game_launch.ASSEMBLY),
                                          limit=MAX_ASSEMBLY_BYTES, digest=True)
        return "MATCH" if assembly_hash == game_launch.ASSEMBLY_HASH else "MISMATCH"
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        return "UNREADABLE"


def _scan_directory(path, uid, budget):
    """Enumerate bounded immediate child metadata; never open child files."""
    if budget[0] <= 0:
        return [], True, True
    rows = []
    incomplete = False
    truncated = False
    descriptor = _open_directory(path, uid)
    try:
        capacity = min(LIMIT_PER_DIRECTORY, budget[0])
        with os.scandir(descriptor) as entries:
            for index, entry in enumerate(itertools.islice(entries, capacity)):
                budget[0] -= 1
                if index + 1 == capacity:
                    truncated = True
                try:
                    info = entry.stat(follow_symlinks=False)
                    if stat.S_ISLNK(info.st_mode):
                        incomplete = True
                    elif stat.S_ISDIR(info.st_mode):
                        if info.st_uid != uid:
                            incomplete = True
                        else:
                            rows.append((entry.name, path / entry.name))
                except OSError:
                    incomplete = True
    finally:
        os.close(descriptor)
    return rows, truncated, incomplete


def _namespace(root, uid, budget):
    status = _directory_status(root, uid)
    result = {"status": status, "user_directories": 0, "profile_directories": 0,
              "modded_profile_directories": 0,
              "inventory_limit_reached": False, "inventory_incomplete": False}
    if status != "DIRECTORY":
        result["inventory_incomplete"] = status not in {"ABSENT"}
        return result
    try:
        rows, truncated, incomplete = _scan_directory(root, uid, budget)
        result["inventory_limit_reached"] = truncated
        result["inventory_incomplete"] = incomplete
        # Steam IDs are numeric; local IDs may be arbitrary. Names remain private.
        if root.name == "steam":
            ids = [(name, path) for name, path in rows if name.isascii() and name.isdecimal()]
            result["inventory_incomplete"] |= len(ids) != len(rows)
        else:
            ids = rows
        result["user_directories"] = len(ids)
        for _, path in ids:
            if _directory_status(path, uid) != "DIRECTORY":
                result["inventory_incomplete"] = True
                continue
            profiles, limit, bad = _scan_directory(path, uid, budget)
            result["inventory_limit_reached"] |= limit
            result["inventory_incomplete"] |= bad
            result["profile_directories"] += sum(
                name.startswith("profile") and name[7:].isascii() and name[7:].isdecimal()
                for name, _ in profiles)
            modded = next((child for name, child in profiles if name == "modded"), None)
            if modded is not None:
                if _directory_status(modded, uid) != "DIRECTORY":
                    result["inventory_incomplete"] = True
                else:
                    modded_profiles, limit, bad = _scan_directory(modded, uid, budget)
                    result["inventory_limit_reached"] |= limit
                    result["inventory_incomplete"] |= bad
                    result["modded_profile_directories"] += sum(
                        name.startswith("profile") and name[7:].isascii() and name[7:].isdecimal()
                        for name, _ in modded_profiles)
    except OSError:
        result["inventory_incomplete"] = True
    return result


def inspect_readiness(game_app, data_root, uid):
    """Return bounded metadata only. Fixture paths are accepted only here, not by CLI."""
    data_status = _directory_status(data_root, uid)
    budget = [LIMIT_TOTAL]
    if data_status == "DIRECTORY":
        steam = _namespace(Path(data_root) / "steam", uid, budget)
        local = _namespace(Path(data_root) / "default", uid, budget)
    else:
        steam = _namespace(Path(data_root) / "steam", uid, [0]) if data_status == "ABSENT" else {
            "status": "NOT_INSPECTED", "user_directories": 0, "profile_directories": 0,
            "modded_profile_directories": 0,
            "inventory_limit_reached": False, "inventory_incomplete": True}
        local = dict(steam)
    return {"schema": 1, "mode": "MAIN_ACCOUNT_READINESS",
            "target": "EXISTING_STEAM_PROGRESS", "account_context": "PROTECTED_MAIN_ACCOUNT",
            "game_build": _game_build(game_app),
            "data_root": data_status, "steam_data": steam, "local_data": local,
            "steam_namespace": ("AMBIGUOUS" if steam["user_directories"] > 1 else
                                "SINGLE" if steam["user_directories"] == 1 else "NONE")
            if steam["status"] == "DIRECTORY" and not steam["inventory_incomplete"]
            and not steam["inventory_limit_reached"] else "UNVERIFIED",
            "steam_cloud_state": "UNVERIFIED", "main_launch_enabled": False,
            "save_contents_read": False, "network_requests_made": False,
            "files_written": False, "signing_performed": False,
            "credentials_persisted": False,
            "blockers": ["MAIN_LAUNCH_REQUIRES_SEPARATE_ACTIVATION", "STEAM_GAME_ATTACHMENT_UNVERIFIED",
                         "LIVE_SAVE_CLOUD_BEHAVIOR_UNVERIFIED", "LIVE_LONG_SESSION_UNVERIFIED",
                         "TIER_VALUES_UNRESOLVED"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inspect"])
    args = parser.parse_args(argv)
    try:
        uid = os.getuid()
        account = pwd.getpwuid(uid)
        home = Path(account.pw_dir)
        if (platform.system() != "Darwin" or uid == 0 or os.geteuid() != uid
                or home != game_launch.PROTECTED_HOME or account.pw_name != home.name
                or _directory_status(home, uid) != "DIRECTORY"):
            raise ValueError("Unsupported account")
        result = inspect_readiness(home / GAME_RELATIVE, home / DATA_RELATIVE, uid)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print("Main-account readiness inspection stopped.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
