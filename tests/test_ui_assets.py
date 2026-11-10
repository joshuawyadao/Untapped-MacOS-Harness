"""Synthetic UI asset rewrite checks; never fetch or bundle vendor bytes."""

import json
import io
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from harness.asar import Archive, HarnessError, sha256
from harness import ui_assets
from tests.test_harness import synthetic_archive


def fixture():
    main = " ".join(ui_assets.STATIC + path for path in ui_assets.IMAGE_PATHS
                    if path != "untapped-companion/sts2/sts2-hover-tip.webp")
    shared = ('React.createElement(Check, { className: "fal fa-check", color: checkColor, disabled })')
    overlay = ('`https://static.untapped.gg/untapped-companion/sts2/icon_${currentColor}.webp` '
               'const backgroundUrl = "https://static.untapped.gg/untapped-companion/sts2/sts2-hover-tip.webp"; '
               'const HoverTipBackground = qe.div`\n\tposition: absolute;')
    css = "const css = `\n\t@import url('https://fonts.googleapis.com/css2?x');\n" + "\n".join(
        "\t@import url('" + ui_assets.STATIC + path + "');" for path in ui_assets.CSS_PATHS)
    css += "\n\t@import url('https://cdn.jsdelivr.net/npm/keyrune@latest/css/keyrune.css');"
    return Archive(synthetic_archive({ui_assets.MAIN: main.encode(), ui_assets.SHARED: shared.encode(),
                                      ui_assets.OVERLAY: overlay.encode(), ui_assets.GLOBAL: css.encode(),
                                      "other.txt": b"untouched"}))


def fake_download(url):
    path = url.removeprefix(ui_assets.STATIC)
    if path.endswith(".webp"):
        return b"RIFF" + b"\x04\x00\x00\x00" + b"WEBPdata"
    if path.endswith(".png"):
        return b"\x89PNG\r\n\x1a\ndata"
    if path.endswith(".css"):
        return b'@font-face{src:url("../webfonts/fa-light-300.woff2")}'
    return b"wOF2font"


class AssetsTests(unittest.TestCase):
    def test_prepare_preserves_archive_mode_and_previous_signed_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory).resolve()
            session.chmod(0o700)
            target = session / "Companion.app/Contents/Resources/app.asar"
            target.parent.mkdir(parents=True)
            target.write_bytes(fixture().data)
            target.chmod(0o600)
            manifest = {"schema": 1, "main_steam_guard_version": 1,
                        "patched_asar_sha256": sha256(target.read_bytes()), "patched_entries": []}
            (session / "manifest.json").write_text(json.dumps(manifest))
            (session / "signing.json").write_text("previous receipt")
            with patch.object(ui_assets.cli, "_validate_launch_copy") as verify:
                ui_assets.prepare(session, download=fake_download)
            verify.assert_called_once_with(session)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertFalse((session / "signing.json").exists())
            self.assertEqual((session / "previous-signing.json").read_text(), "previous receipt")
            saved = json.loads((session / "manifest.json").read_text())
            self.assertEqual(saved["base_patched_asar_sha256"], manifest["patched_asar_sha256"])
            self.assertEqual(saved["patched_asar_sha256"], sha256(target.read_bytes()))

    def test_rewrite_keeps_unrelated_entry_and_removes_broken_ui_urls(self):
        original = fixture()
        replacements, hashes = ui_assets._patch(original, fake_download)
        rewritten = Archive(original.rewrite(replacements))
        self.assertEqual(rewritten.read("other.txt"), b"untouched")
        self.assertEqual(len(hashes), len(ui_assets.IMAGE_PATHS) + len(ui_assets.CSS_PATHS) + 1)
        self.assertIn(b"data:image/webp;base64,", rewritten.read(ui_assets.OVERLAY))
        self.assertIn(b"background-color: #161a1d", rewritten.read(ui_assets.OVERLAY))
        self.assertIn('children: "✓"'.encode(), rewritten.read(ui_assets.SHARED))
        self.assertIn(b"data:font/woff2;base64,", rewritten.read(ui_assets.GLOBAL))
        self.assertNotIn(b"static.untapped.gg/fontawesome/css", rewritten.read(ui_assets.GLOBAL))
        rendered = rewritten.read(ui_assets.GLOBAL)
        self.assertLess(rendered.find(b"keyrune.css"), rendered.find(b"@font-face"))

    def test_public_download_rejects_redirect_status_media_magic_and_size(self):
        url = ui_assets.STATIC + "untapped-companion/sts2/icon_silent.webp"
        good = b"RIFF\x04\x00\x00\x00WEBPdata"

        class Reply(io.BytesIO):
            def __init__(self, body, *, final=url, status=200, media="image/webp"):
                super().__init__(body)
                self.final, self.status = final, status
                self.headers = {"Content-Type": media}

            def geturl(self):
                return self.final

        class Opener:
            def __init__(self, response):
                self.response = response

            def open(self, request, timeout):
                self.request, self.timeout = request, timeout
                return self.response

        for label, reply in (
            ("redirect", Reply(good, final=ui_assets.STATIC + "other.webp")),
            ("status", Reply(good, status=204)),
            ("media", Reply(good, media="text/html")),
            ("magic", Reply(b"<!doctype html>")),
            ("size", Reply(good + b"a" * ui_assets.MAX_ITEM)),
        ):
            with self.subTest(label=label), self.assertRaises(HarnessError):
                ui_assets._download(url, opener=Opener(reply))
        opener = Opener(Reply(good))
        self.assertEqual(ui_assets._download(url, opener=opener), good)
        self.assertEqual(opener.timeout, 10)
        self.assertEqual(opener.request.get_header("User-agent"), "curl/8.7.1")

    def test_download_refuses_unreviewed_destinations_before_network(self):
        for url in ("https://evil.example/icon.png", ui_assets.STATIC + "other.png",
                    ui_assets.STATIC + ui_assets.IMAGE_PATHS[0] + "?uid=1",
                    ui_assets.STATIC + "fontawesome/webfonts/fa-unknown-400.woff2",
                    "http://static.untapped.gg/" + ui_assets.IMAGE_PATHS[0]):
            with self.subTest(url=url), self.assertRaises(HarnessError):
                ui_assets._download(url, opener=object())

    def test_pinned_anchor_and_asset_bounds_fail_closed(self):
        archive = fixture()
        with self.assertRaises(HarnessError):
            ui_assets._patch(archive, lambda _: b"x" * (ui_assets.MAX_TOTAL + 1))
        broken = Archive(synthetic_archive({**{name: archive.read(name) for name in ui_assets.ENTRIES},
                                           "other.txt": b"untouched"}))
        changed = broken.read(ui_assets.SHARED).replace(b"fal fa-check", b"far fa-check")
        broken = Archive(broken.rewrite({ui_assets.SHARED: changed}))
        with self.assertRaises(HarnessError):
            ui_assets._patch(broken, fake_download)


if __name__ == "__main__":
    unittest.main()
