"""Synthetic UI asset rewrite checks; never fetch or bundle vendor bytes."""

import json
import io
import base64
import re
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
               '`https://sts2json.untapped.gg/art/intents/${assetName}.webp` '
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
    def test_all_damage_icon_variants_are_embedded_without_changing_surrounding_logic(self):
        source = 'before(' + ui_assets.INTENT_ANCHOR + ')after'
        calls = []
        def download(url):
            calls.append(url)
            return fake_download(url) + url.encode()
        patched, hashes = ui_assets._patch_intents(source, download)
        self.assertEqual(calls, [ui_assets.INTENT_ORIGIN + p for p in ui_assets.INTENT_PATHS])
        self.assertEqual(set(hashes), set(ui_assets.INTENT_PATHS))
        match = re.fullmatch(r'before\((\(.*\)\[assetName\])\)after', patched)
        self.assertIsNotNone(match)
        assets = json.loads(match[1][1:-len(')[assetName]')])
        self.assertEqual(set(assets), {f'intent_attack_{i}' for i in range(1, 6)})
        for path in ui_assets.INTENT_PATHS:
            data = assets[Path(path).stem]
            self.assertTrue(data.startswith('data:image/webp;base64,'))
            self.assertEqual(base64.b64decode(data.split(',', 1)[1]),
                             fake_download(ui_assets.INTENT_ORIGIN + path) + (ui_assets.INTENT_ORIGIN + path).encode())

    def test_intent_upgrade_preserves_existing_assets_original_binding_and_failure_state(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory).resolve()
            session.chmod(0o700)
            target = session / 'Companion.app/Contents/Resources/app.asar'
            target.parent.mkdir(parents=True)
            original = synthetic_archive({ui_assets.OVERLAY: ui_assets.INTENT_ANCHOR.encode(),
                                          'existing-ui': b'embedded artwork'})
            target.write_bytes(original)
            manifest = {'schema': 1, 'main_steam_guard_version': 1, 'ui_assets_version': 1,
                        'patched_asar_sha256': sha256(original), 'base_patched_asar_sha256': 'original-base',
                        'ui_asset_sha256': {'legacy.webp': 'legacy-hash'}, 'patched_entries': ['existing-ui']}
            manifest_path = session / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest))
            before_manifest = manifest_path.read_bytes()
            with self.assertRaises(OSError):
                ui_assets.prepare(session, download=lambda _: (_ for _ in ()).throw(OSError('offline')))
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(manifest_path.read_bytes(), before_manifest)
            calls = []
            def download(url):
                calls.append(url)
                return fake_download(url)
            ui_assets.prepare(session, download=download)
            saved = json.loads(manifest_path.read_text())
            self.assertEqual(saved['ui_assets_version'], 2)
            self.assertEqual(saved['base_patched_asar_sha256'], 'original-base')
            self.assertEqual(saved['ui_asset_sha256']['legacy.webp'], 'legacy-hash')
            self.assertEqual(set(saved['patched_entries']), {'existing-ui', ui_assets.OVERLAY})
            self.assertEqual(Archive(target.read_bytes()).read('existing-ui'), b'embedded artwork')
            self.assertEqual(calls, [ui_assets.INTENT_ORIGIN + p for p in ui_assets.INTENT_PATHS])
            with self.assertRaises(HarnessError):
                ui_assets.prepare(session, download=download)

    def test_intent_anchor_changes_fail_before_any_download(self):
        for source in ('unrelated', ui_assets.INTENT_ANCHOR * 2):
            with patch.object(ui_assets, '_download') as download, self.assertRaises(HarnessError):
                ui_assets._patch_intents(source, download)
            download.assert_not_called()

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
        self.assertEqual(len(hashes), len(ui_assets.IMAGE_PATHS) + len(ui_assets.CSS_PATHS) + len(ui_assets.INTENT_PATHS) + 1)
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
                    ui_assets.INTENT_ORIGIN + "art/intents/intent_attack_6.webp",
                    ui_assets.INTENT_ORIGIN + ui_assets.IMAGE_PATHS[0],
                    ui_assets.STATIC + ui_assets.INTENT_PATHS[0],
                    ui_assets.INTENT_ORIGIN + ui_assets.INTENT_PATHS[0] + '?account=secret',
                    ui_assets.STATIC + ui_assets.IMAGE_PATHS[0] + "?uid=1",
                    ui_assets.STATIC + "fontawesome/webfonts/fa-unknown-400.woff2",
                    "http://static.untapped.gg/" + ui_assets.IMAGE_PATHS[0]):
            with self.subTest(url=url), self.assertRaises(HarnessError):
                ui_assets._download(url, opener=object())

    def test_fixed_intent_urls_use_validated_public_download(self):
        for path in ui_assets.INTENT_PATHS:
            url = ui_assets.INTENT_ORIGIN + path
            response = io.BytesIO(fake_download(url))
            response.status = 200
            response.headers = {'Content-Type': 'image/webp'}
            response.geturl = lambda: url
            with patch('urllib.request.OpenerDirector.open', return_value=response):
                self.assertEqual(ui_assets._download(url), fake_download(url))

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
