"""Private, read-only snapshot of the original Godot progress tree.

The caller owns process quiescence and chooses the source and a new destination.
This module never restores or removes progress. All paths in the receipt remain
inside the private backup; public results contain counts only.
"""

import hashlib
import itertools
import json
import os
from pathlib import Path
import stat

from .asar import HarnessError


MAX_FILES = 20_000
MAX_BYTES = 2 * 1024**3
MAX_DEPTH = 16
MAX_ENTRIES = 40_000
MAX_RECEIPT = 32 * 1024**2
_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
_UID = os.getuid()
_REPO = Path(__file__).resolve().parents[1]
_CHUNK = 1024 * 1024


def _fail():
    raise HarnessError("Progress backup safety check failed")


def _parts(path):
    path = Path(path)
    if not path.is_absolute() or any(p in (".", "..") for p in path.parts):
        _fail()
    return path.parts[1:]


def _open_dir(path, *, owned=False, private=False):
    fd = os.open("/", _FLAGS)
    try:
        for part in _parts(path):
            next_fd = os.open(part, _FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        info = os.fstat(fd)
        if not stat.S_ISDIR(info.st_mode) or (owned and info.st_uid != _UID):
            _fail()
        if private and stat.S_IMODE(info.st_mode) != 0o700:
            _fail()
        return fd
    except BaseException:
        os.close(fd)
        raise


def _meta(info, kind):
    return {"kind": kind, "mode": stat.S_IMODE(info.st_mode),
            "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns,
            "dev": info.st_dev, "ino": info.st_ino,
            "size": info.st_size if kind == "file" else 0}


def _checked(info, kind):
    if info.st_uid != _UID or (kind == "file" and
            (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1)) or (
            kind == "dir" and not stat.S_ISDIR(info.st_mode)):
        _fail()


def _digest(fd, expected_size):
    digest = hashlib.sha256()
    total = 0
    while True:
        chunk = os.read(fd, _CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > expected_size or total > MAX_BYTES:
            _fail()
        digest.update(chunk)
    if total != expected_size:
        _fail()
    return digest.hexdigest()


def _walk(root_fd, *, destination_fd=None):
    """Inventory a tree using held parent descriptors, optionally copying it."""
    records = {}
    counts = {"files": 0, "bytes": 0, "entries": 0}

    def descend(src_fd, dst_fd, prefix, depth):
        before = os.fstat(src_fd)
        _checked(before, "dir")
        if depth > MAX_DEPTH:
            _fail()
        with os.scandir(src_fd) as stream:
            entries = list(itertools.islice(stream, MAX_ENTRIES - counts["entries"] + 1))
        if len(entries) > MAX_ENTRIES - counts["entries"]:
            _fail()
        for entry in sorted(entries, key=lambda item: item.name):
            name = entry.name
            if name in ("", ".", "..") or "/" in name or "\\" in name:
                _fail()
            relative = prefix + name
            counts["entries"] += 1
            if counts["entries"] > MAX_ENTRIES:
                _fail()
            observed = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(observed.st_mode):
                if depth >= MAX_DEPTH:
                    _fail()
                child = os.open(name, _FLAGS, dir_fd=src_fd)
                try:
                    info = os.fstat(child)
                    _checked(info, "dir")
                    if _meta(observed, "dir") != _meta(info, "dir"):
                        _fail()
                    record = _meta(info, "dir")
                    records[relative] = record
                    target = None
                    if dst_fd is not None:
                        os.mkdir(name, 0o700, dir_fd=dst_fd)
                        target = os.open(name, _FLAGS, dir_fd=dst_fd)
                    try:
                        descend(child, target, relative + "/", depth + 1)
                    finally:
                        if target is not None:
                            os.fsync(target)
                            os.close(target)
                    if _meta(os.fstat(child), "dir") != record:
                        _fail()
                finally:
                    os.close(child)
            elif stat.S_ISREG(observed.st_mode):
                counts["files"] += 1
                counts["bytes"] += observed.st_size
                if counts["files"] > MAX_FILES or counts["bytes"] > MAX_BYTES:
                    _fail()
                child = os.open(name, _FILE_FLAGS, dir_fd=src_fd)
                try:
                    info = os.fstat(child)
                    _checked(info, "file")
                    if _meta(observed, "file") != _meta(info, "file"):
                        _fail()
                    record = _meta(info, "file")
                    digest = hashlib.sha256()
                    total = 0
                    out = None
                    if dst_fd is not None:
                        out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                      os.O_NOFOLLOW | os.O_CLOEXEC, 0o600,
                                      dir_fd=dst_fd)
                    try:
                        while True:
                            chunk = os.read(child, _CHUNK)
                            if not chunk:
                                break
                            total += len(chunk)
                            if total > info.st_size or total > MAX_BYTES:
                                _fail()
                            digest.update(chunk)
                            if out is not None:
                                view = memoryview(chunk)
                                while view:
                                    view = view[os.write(out, view):]
                        if total != info.st_size:
                            _fail()
                        if out is not None:
                            os.fsync(out)
                    finally:
                        if out is not None:
                            os.close(out)
                    if _meta(os.fstat(child), "file") != record:
                        _fail()
                    record["sha256"] = digest.hexdigest()
                    records[relative] = record
                finally:
                    os.close(child)
            else:
                _fail()
        if _meta(os.fstat(src_fd), "dir") != _meta(before, "dir"):
            _fail()

    descend(root_fd, destination_fd, "", 0)
    return records, counts


def _payload_matches(fd, records):
    """Check the exact backup tree, including empty directories and modes."""
    actual, counts = _walk(fd)
    if actual.keys() != records.keys():
        _fail()
    for path, source in records.items():
        found = actual[path]
        if found["kind"] != source["kind"] or found["mode"] != (
                0o700 if source["kind"] == "dir" else 0o600):
            _fail()
        if source["kind"] == "file" and (found["size"] != source["size"] or
                                          found["sha256"] != source["sha256"]):
            _fail()
    return counts


def _validate_receipt(data):
    if not isinstance(data, dict) or set(data) != {"schema", "source", "records"} or data["schema"] != 1:
        _fail()
    records = data["records"]
    if not isinstance(records, dict) or len(records) > MAX_ENTRIES:
        _fail()
    for path, record in records.items():
        if not isinstance(path, str) or not path or path.startswith("/") or any(
                p in ("", ".", "..") for p in path.split("/")):
            _fail()
        if not isinstance(record, dict) or record.get("kind") not in ("dir", "file"):
            _fail()
        required = {"kind", "mode", "mtime_ns", "ctime_ns", "dev", "ino", "size"}
        if record["kind"] == "file":
            required.add("sha256")
        if set(record) != required or any(type(record[k]) is not int or record[k] < 0
                                         for k in required - {"kind", "sha256"}):
            _fail()
        if record["kind"] == "file" and (not isinstance(record["sha256"], str) or
             len(record["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in record["sha256"])):
            _fail()
    source = data["source"]
    if not isinstance(source, dict) or set(source) != {"kind", "mode", "mtime_ns", "ctime_ns", "dev", "ino", "size"}:
        _fail()
    return records


def _read_receipt(fd):
    child = os.open("receipt.json", _FILE_FLAGS, dir_fd=fd)
    try:
        info = os.fstat(child)
        _checked(info, "file")
        if stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > MAX_RECEIPT:
            _fail()
        raw = bytearray()
        while len(raw) <= MAX_RECEIPT:
            chunk = os.read(child, min(_CHUNK, MAX_RECEIPT + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        if len(raw) != info.st_size or len(raw) > MAX_RECEIPT or _meta(os.fstat(child), "file") != _meta(info, "file"):
            _fail()
        return json.loads(raw)
    finally:
        os.close(child)


def _verify_open(fd):
    with os.scandir(fd) as entries:
        if sorted(entry.name for entry in itertools.islice(entries, 3)) != ["payload", "receipt.json"]:
            _fail()
    receipt = _read_receipt(fd)
    records = _validate_receipt(receipt)
    payload = os.open("payload", _FLAGS, dir_fd=fd)
    try:
        _checked(os.fstat(payload), "dir")
        if stat.S_IMODE(os.fstat(payload).st_mode) != 0o700:
            _fail()
        counts = _payload_matches(payload, records)
    finally:
        os.close(payload)
    return receipt, {"files": counts["files"], "bytes": counts["bytes"], "verified": True}


def create_backup(source: Path, destination: Path) -> dict:
    """Create a new private backup. A failed copy keeps no valid receipt."""
    try:
        source, destination = Path(source), Path(destination)
        source_parts, dest_parts = _parts(source), _parts(destination)
        repo_parts = _parts(_REPO)
        if not source_parts or not dest_parts or source_parts == dest_parts or (
                source_parts == dest_parts[:len(source_parts)]) or (
                dest_parts == source_parts[:len(dest_parts)]) or (
                dest_parts[:len(repo_parts)] == repo_parts):
            _fail()
        source_fd = _open_dir(source, owned=True)
        try:
            parent_fd = _open_dir(destination.parent, owned=True, private=True)
            try:
                os.mkdir(destination.name, 0o700, dir_fd=parent_fd)
                dest_fd = os.open(destination.name, _FLAGS, dir_fd=parent_fd)
                try:
                    _checked(os.fstat(dest_fd), "dir")
                    os.mkdir("payload", 0o700, dir_fd=dest_fd)
                    payload_fd = os.open("payload", _FLAGS, dir_fd=dest_fd)
                    try:
                        initial, _ = _walk(source_fd)
                        root_meta = _meta(os.fstat(source_fd), "dir")
                        copied, _ = _walk(source_fd, destination_fd=payload_fd)
                        if copied != initial or _meta(os.fstat(source_fd), "dir") != root_meta:
                            _fail()
                        final, _ = _walk(source_fd)
                        if final != initial or _meta(os.fstat(source_fd), "dir") != root_meta:
                            _fail()
                        _payload_matches(payload_fd, initial)
                        os.fsync(payload_fd)
                    finally:
                        os.close(payload_fd)
                    receipt = json.dumps({"schema": 1, "source": root_meta, "records": initial},
                                         sort_keys=True, separators=(",", ":")).encode()
                    if len(receipt) > MAX_RECEIPT:
                        _fail()
                    receipt_fd = os.open("receipt.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                         os.O_NOFOLLOW | os.O_CLOEXEC, 0o600,
                                         dir_fd=dest_fd)
                    try:
                        view = memoryview(receipt)
                        while view:
                            view = view[os.write(receipt_fd, view):]
                        os.fsync(receipt_fd)
                    finally:
                        os.close(receipt_fd)
                    os.fsync(dest_fd)
                    _, summary = _verify_open(dest_fd)
                    return summary
                finally:
                    os.close(dest_fd)
            finally:
                os.close(parent_fd)
        finally:
            os.close(source_fd)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
        raise HarnessError("Progress backup safety check failed") from None


def verify_backup(destination: Path) -> dict:
    """Verify receipt and every backup entry before any launch uses it."""
    try:
        fd = _open_dir(destination, owned=True, private=True)
        try:
            return _verify_open(fd)[1]
        finally:
            os.close(fd)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise HarnessError("Progress backup safety check failed") from None


def assert_source_unchanged(source: Path, destination: Path) -> None:
    """Fail if the original tree differs from the verified prelaunch snapshot."""
    try:
        backup_fd = _open_dir(destination, owned=True, private=True)
        try:
            receipt, _ = _verify_open(backup_fd)
        finally:
            os.close(backup_fd)
        source_fd = _open_dir(source, owned=True)
        try:
            before = _meta(os.fstat(source_fd), "dir")
            records, _ = _walk(source_fd)
            if before != receipt["source"] or records != receipt["records"]:
                _fail()
        finally:
            os.close(source_fd)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise HarnessError("Progress backup safety check failed") from None
