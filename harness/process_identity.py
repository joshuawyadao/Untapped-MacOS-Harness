"""Build an unprivileged, same-user Darwin process identity probe privately."""

import hashlib
import os
import platform
import stat
import subprocess
import tempfile
from pathlib import Path

from .asar import HarnessError


def _private_directory(profile):
    path = Path(profile)
    try:
        if not path.is_absolute() or path.resolve(strict=True) != path:
            raise HarnessError("Identity profile must be a canonical directory")
        entry = path.lstat()
    except (OSError, RuntimeError) as exc:
        raise HarnessError("Identity profile is unavailable") from exc
    if (not stat.S_ISDIR(entry.st_mode) or entry.st_uid != os.getuid()
            or stat.S_IMODE(entry.st_mode) != 0o700):
        raise HarnessError("Identity profile must be owned and mode 0700")
    return path


def _safe_output(path):
    try:
        entry = path.lstat()
    except OSError as exc:
        raise HarnessError("Compiler did not create identity helper") from exc
    if (not stat.S_ISREG(entry.st_mode) or entry.st_uid != os.getuid()
            or entry.st_nlink != 1 or entry.st_size == 0):
        raise HarnessError("Compiler produced an unsafe identity helper")


def prepare_identity_probe(profile):
    """Compile and atomically add a fresh helper; return its path and SHA-256."""
    if platform.system() != "Darwin":
        raise HarnessError("Identity helper requires macOS")
    if os.getuid() == 0 or os.getuid() != os.geteuid():
        raise HarnessError("Identity helper requires an unprivileged user")
    profile = _private_directory(profile)
    destination = profile / "target-identity"
    if destination.exists() or destination.is_symlink():
        raise HarnessError("Identity helper destination already exists")
    source = Path(__file__).with_name("target_identity.c")
    if not source.is_file() or source.is_symlink():
        raise HarnessError("Identity helper source is unavailable")

    try:
        with tempfile.TemporaryDirectory(prefix="identity-build-", dir=profile) as temporary:
            build_dir = Path(temporary)
            output = build_dir / "target-identity"
            environment = {"PATH": "/usr/bin:/bin", "LANG": "C", "TMPDIR": temporary}
            try:
                result = subprocess.run(
                    ["/usr/bin/clang", "-Wall", "-Wextra", "-Werror", "-Os",
                     str(source), "-o", str(output)],
                    cwd=temporary, env=environment, capture_output=True,
                    timeout=30, check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise HarnessError("Identity helper compilation timed out") from exc
            except OSError as exc:
                raise HarnessError("Identity helper compiler unavailable") from exc
            if result.returncode != 0:
                detail = result.stderr.decode("utf-8", "replace")[-300:].strip()
                raise HarnessError("Identity helper compilation failed: " + detail)
            _safe_output(output)
            output.chmod(0o700)
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            _private_directory(profile)
            try:
                # Hard-link creation is atomic and refuses an existing destination.
                os.link(output, destination, follow_symlinks=False)
            except FileExistsError as exc:
                raise HarnessError("Identity helper destination already exists") from exc
            except OSError as exc:
                raise HarnessError("Cannot install identity helper") from exc
        _safe_output(destination)
        if stat.S_IMODE(destination.stat().st_mode) != 0o700:
            raise HarnessError("Installed identity helper has unsafe mode")
        return {"path": str(destination), "sha256": digest}
    except HarnessError:
        raise
    except OSError as exc:
        raise HarnessError("Cannot build identity helper privately") from exc
