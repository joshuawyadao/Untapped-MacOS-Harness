"""Embed a fixed set of public UI assets in a new, unsigned companion copy."""

import argparse
import base64
import copy
import json
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .asar import Archive, HarnessError, sha256
from . import cli


MAIN = "dist/renderer/assets/Main-DlHDXYoX.js"
SHARED = "dist/renderer/assets/index.esm-CeGqlG_I.js"
GLOBAL = "dist/renderer/assets/index-FOxynWcw.js"
OVERLAY = "dist/renderer/assets/Sts2Overlay-DPeYNPLb.js"
ENTRIES = (MAIN, SHARED, GLOBAL, OVERLAY)
STATIC = "https://static.untapped.gg/"
CHARACTERS = ("ironclad", "silent", "regent", "necrobinder", "defect")
IMAGE_PATHS = (
    *(f"untapped-companion/sts2/icon_{name}.webp" for name in CHARACTERS),
    "untapped-companion/sts2/sts2-logo.webp",
    "untapped-companion/sts2/sts2-key-art.webp",
    "untapped-companion/sts2/sts2-hover-tip.webp",
    "react-components/franchises/hearthstone.png",
    "react-components/franchises/battlegrounds.png",
    "react-components/franchises/mtga.png",
    "react-components/franchises/snap.png",
    "react-components/franchises/ygom.png",
    "react-components/franchises/stormgate.webp",
    "react-components/franchises/pocket.png",
    "react-components/franchises/sts2.png",
    "untapped-companion/snap/snap_icon.webp",
)
CSS_NAMES = ("fontawesome", "light", "regular", "solid", "brands")
CSS_PATHS = tuple(f"fontawesome/css/{name}.min.css" for name in CSS_NAMES)
FONT_URL = re.compile(r'url\(["\']?(\.\./webfonts/[A-Za-z0-9-]+\.(?:woff2|woff|ttf))["\']?\)')
MAX_ITEM = 2 * 1024 * 1024
MAX_TOTAL = 12 * 1024 * 1024
MAX_REQUESTS = 40
MAX_SECONDS = 180
FONT_STEMS = ("fa-brands-400", "fa-light-300", "fa-regular-400", "fa-solid-900")
FONT_PATHS = frozenset(f"fontawesome/webfonts/{stem}.{extension}"
                       for stem in FONT_STEMS for extension in ("woff2", "woff", "ttf"))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_):
        raise HarnessError("Public asset redirect refused")


def _download(url, *, opener=None):
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path.lstrip("/")
    valid_image = path in IMAGE_PATHS
    valid_css = path in CSS_PATHS
    valid_font = path in FONT_PATHS
    if (parsed.scheme != "https" or parsed.netloc != "static.untapped.gg" or
            parsed.query or parsed.fragment or not (valid_image or valid_css or valid_font)):
        raise HarnessError("Public UI asset is outside the fixed allowlist")
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(url, headers={"Accept": "image/*,text/css,font/*",
                                                    "User-Agent": "curl/8.7.1"})
    with opener.open(request, timeout=10) as response:
        if response.geturl() != url or response.status != 200:
            raise HarnessError("Unexpected public UI asset response")
        media = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        expected = ("image/webp" if path.endswith(".webp") else "image/png" if path.endswith(".png")
                    else "text/css" if valid_css else "font/woff2" if path.endswith(".woff2")
                    else "font/woff" if path.endswith(".woff") else "font/ttf")
        if media != expected:
            raise HarnessError("Unexpected public UI asset media type")
        raw = response.read(MAX_ITEM + 1)
    if not raw or len(raw) > MAX_ITEM:
        raise HarnessError("Public UI asset size is unsupported")
    if valid_image and not (raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"
                            if path.endswith(".webp") else raw.startswith(b"\x89PNG\r\n\x1a\n")):
        raise HarnessError("Public UI image format is unsupported")
    if valid_css and (b"\x00" in raw or b"`" in raw or b"${" in raw):
        raise HarnessError("Public UI stylesheet format is unsupported")
    if valid_font and not (raw[:4] in (b"wOF2", b"wOFF", b"\x00\x01\x00\x00")):
        raise HarnessError("Public UI font format is unsupported")
    return raw


def _data_uri(raw, mime):
    return "data:" + mime + ";base64," + base64.b64encode(raw).decode("ascii")


def _replace_once(value, old, new):
    if value.count(old) != 1:
        raise HarnessError("Pinned UI asset anchor changed")
    return value.replace(old, new, 1)


def _patch(archive, download=_download):
    contents = {name: archive.read(name).decode("utf-8") for name in ENTRIES}
    started = time.monotonic()
    requests = 0

    def get_asset(path):
        nonlocal requests
        requests += 1
        if requests > MAX_REQUESTS or time.monotonic() - started > MAX_SECONDS:
            raise HarnessError("Public UI asset request budget exceeded")
        value = download(STATIC + path)
        if time.monotonic() - started > MAX_SECONDS:
            raise HarnessError("Public UI asset deadline exceeded")
        return value

    image_assets = {}
    total = 0
    hashes = {}
    for path in IMAGE_PATHS:
        raw = get_asset(path)
        total += len(raw)
        if total > MAX_TOTAL:
            raise HarnessError("Public UI assets exceed total size")
        hashes[path] = sha256(raw)
        image_assets[path] = _data_uri(raw, "image/webp" if path.endswith(".webp") else "image/png")
    main = contents[MAIN]
    shared = contents[SHARED]
    overlay = contents[OVERLAY]
    for path in IMAGE_PATHS:
        url = STATIC + path
        target = MAIN if url in main else SHARED if url in shared else OVERLAY
        if url not in contents[target]:
            raise HarnessError("Pinned UI image reference changed")
        contents[target] = _replace_once(contents[target], url, image_assets[path])
    # The STS2 overlay builds its current-character icon URL dynamically.
    dynamic = '"https://static.untapped.gg/untapped-companion/sts2/icon_${currentColor}.webp"'
    choices = ",".join(json.dumps(name) + ":" + json.dumps(image_assets[f"untapped-companion/sts2/icon_{name}.webp"])
                       for name in CHARACTERS)
    contents[OVERLAY] = _replace_once(contents[OVERLAY], "`" + dynamic[1:-1] + "`",
        "({" + choices + "})[currentColor] || \"\"")
    # A checked box must remain legible even if a decorative icon font is absent.
    check = 'React.createElement(Check, { className: "fal fa-check", color: checkColor, disabled })'
    fallback = 'React.createElement(Check, { color: checkColor, disabled, "aria-hidden": true, children: "✓" })'
    contents[SHARED] = _replace_once(contents[SHARED], check, fallback)
    # Always paint a readable panel under the vendor's decorative nine-slice image.
    contents[OVERLAY] = _replace_once(contents[OVERLAY],
        'const HoverTipBackground = qe.div`\n\tposition: absolute;',
        'const HoverTipBackground = qe.div`\n\tbackground-color: #161a1d;\n\tborder: 1px solid #a99465;\n\tborder-radius: 8px;\n\tposition: absolute;')
    css_parts = []
    font_assets = {}
    for css_path in CSS_PATHS:
        raw = get_asset(css_path)
        total += len(raw)
        if total > MAX_TOTAL:
            raise HarnessError("Public UI assets exceed total size")
        hashes[css_path] = sha256(raw)
        css = raw.decode("utf-8")
        for relative in sorted(set(FONT_URL.findall(css))):
            font_path = "fontawesome/" + relative[3:]
            if font_path not in font_assets:
                font = get_asset(font_path)
                total += len(font)
                if total > MAX_TOTAL:
                    raise HarnessError("Public UI assets exceed total size")
                font_assets[font_path] = font
                hashes[font_path] = sha256(font)
            mime = "font/woff2" if font_path.endswith("woff2") else "font/woff" if font_path.endswith("woff") else "font/ttf"
            css = css.replace(relative, _data_uri(font_assets[font_path], mime))
        if re.search(r'url\((?!["\']?data:)', css) or "@import" in css:
            raise HarnessError("Public UI stylesheet has an unsupported dependency")
        css_parts.append(css)
    global_css = contents[GLOBAL]
    for css_path in CSS_PATHS:
        global_css = _replace_once(global_css, "@import url('" + STATIC + css_path + "');", "")
    if "`" in "".join(css_parts) or "${" in "".join(css_parts):
        raise HarnessError("Public UI stylesheet is not safe to embed")
    css = "\n".join(css_parts).replace("\\", "\\\\")
    contents[GLOBAL] = global_css
    # Insert beside the original font imports, inside the existing CSS template.
    marker = "\t@import url('https://cdn.jsdelivr.net/npm/keyrune@latest/css/keyrune.css');"
    at = contents[GLOBAL].find(marker)
    if at < 0 or contents[GLOBAL].count(marker) != 1:
        raise HarnessError("Pinned global stylesheet anchor changed")
    at += len(marker)
    contents[GLOBAL] = contents[GLOBAL][:at] + "\n\t" + css + contents[GLOBAL][at:]
    return {name: value.encode("utf-8") for name, value in contents.items()}, hashes


def prepare(session, *, download=_download):
    session = Path(session).resolve(strict=True)
    if session.is_relative_to(cli.ROOT) or session.is_symlink():
        raise HarnessError("UI assets require a disposable companion")
    manifest_path = session / "manifest.json"
    archive_path = session / "Companion.app/Contents/Resources/app.asar"
    if manifest_path.is_symlink() or archive_path.is_symlink():
        raise HarnessError("UI asset target must not be redirected")
    if stat.S_IMODE(session.stat().st_mode) != 0o700 or session.stat().st_uid != os.getuid():
        raise HarnessError("UI asset session must be private and owned")
    signed = (session / "signing.json").exists()
    if signed:
        cli._validate_launch_copy(session)
    manifest = cli.read_json(manifest_path)
    before = archive_path.read_bytes()
    old_hash = sha256(before)
    if (manifest.get("schema") != 1 or manifest.get("main_steam_guard_version") != 1 or
            manifest.get("patched_asar_sha256") != old_hash or manifest.get("ui_assets_version") is not None):
        raise HarnessError("UI asset base copy is unsupported")
    archive = Archive(before)
    replacements, hashes = _patch(archive, download)
    result = archive.rewrite(replacements)
    rewritten = Archive(result)
    for name, content in replacements.items():
        if rewritten.read(name) != content:
            raise HarnessError("UI asset rewrite failed validation")
    updated = copy.deepcopy(manifest)
    updated.update(ui_assets_version=1, base_patched_asar_sha256=old_hash,
                   patched_asar_sha256=sha256(result), ui_asset_sha256=hashes,
                   patched_entries=sorted(set(manifest["patched_entries"]) | set(ENTRIES)))
    temporary = archive_path.with_suffix(".ui-temp")
    with temporary.open("xb") as output:
        output.write(result)
    temporary.chmod(stat.S_IMODE(archive_path.stat().st_mode))
    os.replace(temporary, archive_path)
    cli.write_json(manifest_path, updated)
    if signed:
        prior = session / "signing.json"
        prior.replace(session / "previous-signing.json")
    return {"ui_assets_version": 1, "asset_count": len(hashes), "patched_asar_sha256": updated["patched_asar_sha256"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(args.session), indent=2))
        return 0
    except (HarnessError, OSError, UnicodeError, ValueError, KeyError, urllib.error.URLError):
        print("UI asset preparation stopped: pinned copy or public asset could not be validated", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
