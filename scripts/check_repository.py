#!/usr/bin/env python3
"""Check tracked-file hygiene and simple inline Markdown file links using only stdlib."""

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 5 * 1024 * 1024
PRIVATE_KEY = re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^\s)]+)\)")
LOCAL_DIRECTORIES = {
    ".aws", ".ssh", ".codex", ".claude", ".venv", "venv",
    "node_modules", "__pycache__", "DerivedData", "xcuserdata",
    "captures", "game-data", "untapped-data",
}
PRIVATE_SUFFIXES = {
    ".pem", ".key", ".p12", ".pfx", ".mobileprovision", ".provisionprofile",
}


def check_file(path: Path) -> list:
    relative = path.relative_to(ROOT)
    errors = []
    if path.is_symlink():
        return [f"{relative}: tracked symlinks need an explicit policy before use"]
    if not path.is_file():
        return [f"{relative}: tracked file is missing or is not a regular file"]
    is_environment = path.name == ".env" or path.name.startswith(".env.")
    if is_environment and path.name != ".env.example":
        errors.append(f"{relative}: local environment file must not be tracked")
    if LOCAL_DIRECTORIES.intersection(relative.parts) or path.suffix.lower() in PRIVATE_SUFFIXES:
        errors.append(f"{relative}: sensitive or local-only path must not be tracked")
    if path.stat().st_size > MAX_FILE_BYTES:
        return errors + [f"{relative}: exceeds the 5 MiB source-file limit; use release assets"]
    content = path.read_bytes()
    if PRIVATE_KEY.search(content):
        errors.append(f"{relative}: private-key material detected")
    if path.suffix.lower() == ".md":
        errors.extend(check_markdown_links(path, content.decode("utf-8")))
    return errors


def check_markdown_links(path: Path, content: str) -> list:
    errors = []
    for link in MARKDOWN_LINK.findall(content):
        target = urlsplit(link)
        if target.scheme or target.netloc or not target.path:
            continue
        destination = (path.parent / unquote(target.path)).resolve()
        if not destination.is_relative_to(ROOT) or not destination.exists():
            errors.append(f"{path.relative_to(ROOT)}: missing or out-of-repository link: {link}")
    return errors


def main() -> int:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    files = [ROOT / name for name in tracked.decode("utf-8").split("\0") if name]
    errors = [error for path in files for error in check_file(path)]
    if errors:
        print("Repository checks failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Repository checks passed ({len(files)} tracked files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
