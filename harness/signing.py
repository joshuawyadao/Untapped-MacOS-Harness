"""Explicitly opt-in local resealing of one prepared companion copy.

The agent must obtain owner approval before invoking sign_copy with approved=True.
A receipt records a local operation, not an authorization credential or vendor trust.
"""
import json
import os
import platform
import plistlib
import re
import subprocess
from pathlib import Path

from .asar import HarnessError, sha256
from .patches import (ASAR_SHA256, EXECUTABLE_SHA256, FRAMEWORK_SHA256,
                      SCRY, SCRY_SHA256)

ENTITLEMENTS = {
    "com.apple.security.cs.allow-dyld-environment-variables": True,
    "com.apple.security.cs.allow-jit": True,
    "com.apple.security.cs.allow-unsigned-executable-memory": True,
    "com.apple.security.cs.debugger": True,
    "com.apple.security.cs.disable-library-validation": True,
}
EXECUTABLE = "MacOS/Untapped.gg Companion"
FRAMEWORK = "Frameworks/Electron Framework.framework/Versions/A/Electron Framework"
SCOPE = "outer-companion-only"
ROOT = Path(__file__).resolve().parents[1]


def _run_codesign(command):
    try:
        return subprocess.run(command, capture_output=True, check=True)
    except subprocess.CalledProcessError as error:
        detail = error.stderr or error.stdout or f"exit status {error.returncode}"
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        raise HarnessError("codesign failed: " + detail[:2000].strip()) from error


def _session(session):
    session = session.resolve(strict=True)
    app = session / "Companion.app"
    if session.is_relative_to(ROOT) or app.resolve(strict=True) != app:
        raise HarnessError("Signing target must be a disposable app outside the repository")
    for relative in ("Contents/MacOS/Untapped.gg Companion", "Contents/_CodeSignature",
                     "Contents/_CodeSignature/CodeResources",
                     "Contents/Info.plist", "Contents/Resources/app.asar"):
        path = app / relative
        if not path.resolve(strict=True).is_relative_to(app) or path.is_symlink():
            raise HarnessError("Signing target escapes disposable copy")
        if path.is_file() and path.stat().st_nlink != 1:
            raise HarnessError("Signing target must not share hard-linked source files")
    return session


def _entitlements(app):
    if platform.system() != "Darwin":
        raise HarnessError("Companion signing requires macOS")
    for arch in ("arm64", "x86_64"):
        result = _run_codesign(
            ["/usr/bin/codesign", "-d", "--entitlements", ":-", "--arch", arch, str(app)])
        try:
            actual = plistlib.loads(result.stdout)
        except (ValueError, plistlib.InvalidFileException) as error:
            raise HarnessError("Cannot read original companion entitlements") from error
        if actual != ENTITLEMENTS:
            raise HarnessError("Companion entitlements differ from the five inspected originals")


def _check_payloads(session, manifest, executable_hash):
    if (manifest.get("schema") != 1 or manifest.get("app_asar_sha256") != ASAR_SHA256
            or manifest.get("source_signature_valid") is not True):
        raise HarnessError("Signing requires a verified pinned-source preparation")
    contents = session / "Companion.app/Contents"
    pins = {
        "Resources/app.asar": manifest["patched_asar_sha256"],
        EXECUTABLE: executable_hash, FRAMEWORK: FRAMEWORK_SHA256,
        "Resources/app.asar.unpacked/" + SCRY: SCRY_SHA256,
    }
    for relative, expected in pins.items():
        if sha256((contents / relative).read_bytes()) != expected:
            raise HarnessError("Prepared payload changed: " + relative)


def signing_proposal(session):
    session = _session(session)
    if (session / "launch.json").exists() or (session / "signing.json").exists():
        raise HarnessError("Use a fresh unlaunched, unsigned prepared session")
    manifest = json.loads((session / "manifest.json").read_text())
    _check_payloads(session, manifest, EXECUTABLE_SHA256)
    _entitlements(session / "Companion.app")
    entitlements_path = session / "companion-entitlements.plist"
    # An ordinary, reviewable preparation file; this does not change the app.
    if entitlements_path.is_symlink():
        raise HarnessError("Entitlements proposal must not be a symlink")
    temporary = session / "companion-entitlements.plist.tmp"
    with temporary.open("xb") as output:
        output.write(plistlib.dumps(ENTITLEMENTS))
    os.replace(temporary, entitlements_path)
    entitlements_path.chmod(0o600)
    command = [
        "/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime",
        "--timestamp=none", "--entitlements", str(entitlements_path), str(session / "Companion.app"),
    ]
    return {"scope": SCOPE, "target": str(session / "Companion.app"), "command": command,
            "entitlements": ENTITLEMENTS, "signing_executed": False,
            "requires_explicit_owner_approval": True,
            "vendor_identity": "Replaced by a local ad-hoc identity only if approved"}


def verify_signed_copy(session):
    app = session / "Companion.app"
    _run_codesign(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)])
    _entitlements(app)


def sign_copy(session, approved=False):
    if not approved:
        raise HarnessError("Explicit owner approval required before ad-hoc companion signing")
    proposal = signing_proposal(session)
    session = _session(session)
    manifest = json.loads((session / "manifest.json").read_text())
    # No recursive signing, user signing identity, administrator access, or OS exception.
    _run_codesign(proposal["command"])
    verify_signed_copy(session)
    signed_hash = sha256((session / "Companion.app/Contents" / EXECUTABLE).read_bytes())
    _check_payloads(session, manifest, signed_hash)
    receipt = {
        "schema": 1, "scope": SCOPE, "original_executable_sha256": EXECUTABLE_SHA256,
        "patched_asar_sha256": manifest["patched_asar_sha256"],
        "signed_executable_sha256": signed_hash, "entitlements": ENTITLEMENTS,
        "signature": "ad-hoc", "hardened_runtime": True,
        "game_modified": False, "nested_code_resigned": False,
    }
    path = session / "signing.json"
    with path.open("x") as output:
        json.dump(receipt, output, indent=2)
        output.write("\n")
    path.chmod(0o600)
    return receipt


def expected_executable_hash(session, manifest):
    receipt_path = session / "signing.json"
    if not receipt_path.exists():
        return EXECUTABLE_SHA256
    if receipt_path.is_symlink():
        raise HarnessError("Signing receipt must remain inside the disposable session")
    receipt = json.loads(receipt_path.read_text())
    if not isinstance(receipt, dict):
        raise HarnessError("Signing receipt must be an object")
    signed_hash = receipt.get("signed_executable_sha256")
    if (receipt.get("schema") != 1 or receipt.get("scope") != SCOPE
            or receipt.get("original_executable_sha256") != EXECUTABLE_SHA256
            or receipt.get("patched_asar_sha256") != manifest.get("patched_asar_sha256")
            or receipt.get("entitlements") != ENTITLEMENTS
            or receipt.get("signature") != "ad-hoc" or receipt.get("hardened_runtime") is not True
            or receipt.get("game_modified") is not False or receipt.get("nested_code_resigned") is not False
            or not isinstance(signed_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", signed_hash)):
        raise HarnessError("Signing receipt does not match this prepared companion")
    return receipt["signed_executable_sha256"]
