"""Portable behavior checks using synthetic archives and reward events only."""
import copy
import json
import os
import plistlib
import shutil
import struct
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from harness.asar import Archive, HarnessError, sha256
from harness import cli, patches


def synthetic_archive(contents=None, extra_entries=None):
    """Construct the small ASAR wire format without using a vendor archive."""
    contents = contents or {"a.txt": b"first", "nested/b.txt": b"second"}
    entries = {}
    payload = bytearray()
    for name, data in contents.items():
        parts = name.split("/")
        folder = entries
        for part in parts[:-1]:
            folder = folder.setdefault(part, {"files": {}})["files"]
        folder[parts[-1]] = {"size": len(data), "offset": str(len(payload))}
        payload.extend(data)
    entries.update(extra_entries or {})
    raw = json.dumps({"files": entries}, separators=(",", ":")).encode("utf-8")
    padding = bytes(-(4 + len(raw)) % 4)
    pickle = struct.pack("<II", 4 + len(raw) + len(padding), len(raw)) + raw + padding
    return struct.pack("<II", 4, len(pickle)) + pickle + payload


def card(identifier, x, upgrade=0, y=0.5):
    return {
        "id": identifier, "upgradeLevel": upgrade, "cx": x, "cy": y,
        "width": 0.12, "height": 0.2,
    }


def reward_events(cards=None):
    names = ["bootstrap", "ready", "window-detected", "attach-attempt", "reader-connected"]
    return [{"event": name} for name in names] + [{"event": "reward", "cards": cards or [card("A", 0.3), card("B", 0.7, 1)]}]


class ArchiveTests(unittest.TestCase):
    def test_rewrite_preserves_untouched_entries_and_updates_integrity(self):
        blob = synthetic_archive(extra_entries={
            "native.node": {"size": 7, "unpacked": True},
            "alias": {"link": "a.txt"},
        })
        original = Archive(blob)
        original.header["files"]["a.txt"]["integrity"] = {
            "algorithm": "SHA256", "hash": sha256(b"first"),
            "blockSize": 4, "blocks": [sha256(b"firs"), sha256(b"t")],
        }
        # Encoding through rewrite models the integrity-bearing input.
        original_with_integrity = Archive(original.rewrite({}))
        replaced = b"a longer replacement"
        rewritten = Archive(original_with_integrity.rewrite({"a.txt": replaced}))
        self.assertEqual(rewritten.read("a.txt"), replaced)
        self.assertEqual(rewritten.read("nested/b.txt"), b"second")
        self.assertEqual(rewritten.files["native.node"], {"size": 7, "unpacked": True})
        self.assertEqual(rewritten.files["alias"], {"link": "a.txt"})
        integrity = rewritten.files["a.txt"]["integrity"]
        self.assertEqual(integrity["hash"], sha256(replaced))
        self.assertEqual(integrity["blocks"], [sha256(replaced[i:i + 4]) for i in range(0, len(replaced), 4)])
        self.assertEqual(original_with_integrity.read("a.txt"), b"first")

    def test_rewrite_refuses_unpacked_link_and_unknown_entries(self):
        archive = Archive(synthetic_archive(extra_entries={
            "native.node": {"size": 7, "unpacked": True}, "alias": {"link": "a.txt"},
        }))
        for name in ("native.node", "alias", "new-file"):
            with self.subTest(name=name), self.assertRaises(HarnessError):
                archive.rewrite({name: b"changed"})

    def test_truncated_archive_and_out_of_bounds_entry_fail_closed(self):
        blob = synthetic_archive()
        with self.assertRaises(HarnessError):
            Archive(blob[:9])
        with self.assertRaises(HarnessError):
            Archive(blob[:-1])
        with self.assertRaises(HarnessError):
            Archive(synthetic_archive(extra_entries={"escape": {"offset": "999", "size": 20}}))
        with self.assertRaises(HarnessError):
            Archive(synthetic_archive(extra_entries={"../secret": {"link": "a.txt"}}))


class PatchTests(unittest.TestCase):
    def test_missing_and_duplicate_anchor_refuse_mutation(self):
        with self.assertRaises(HarnessError):
            patches.replace_once("not here", "anchor", "new")
        with self.assertRaises(HarnessError):
            patches.replace_once("anchor anchor", "anchor", "new")
        self.assertEqual(patches.replace_once("one anchor", "anchor", "new"), "one new")

    def test_inspection_rejects_unknown_archive_before_reading_other_bundle_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary) / "Vendor.app"
            asar = app / "Contents/Resources/app.asar"
            asar.parent.mkdir(parents=True)
            asar.write_bytes(synthetic_archive())
            with self.assertRaisesRegex(HarnessError, "Unsupported archive hash"):
                cli.inspect_app(app)

    def test_inspection_rejects_native_binary_or_fuse_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = Path(temporary) / "Vendor.app"
            contents = app / "Contents"
            asar = contents / "Resources/app.asar"
            asar.parent.mkdir(parents=True)
            blob = synthetic_archive({
                patches.OVERLAY: b"overlay fixture", patches.RUNTIME: b"runtime fixture",
            })
            asar.write_bytes(blob)
            (contents / "Info.plist").write_bytes(plistlib.dumps({
                "CFBundleShortVersionString": "synthetic",
            }))
            native = contents / "Resources/app.asar.unpacked" / patches.SCRY
            native.parent.mkdir(parents=True)
            native.write_bytes(b"native")
            framework = contents / "Frameworks/Electron Framework.framework/Versions/A/Electron Framework"
            framework.parent.mkdir(parents=True)
            # Two synthetic slices carrying the expected fuse wire.
            wire = cli.FUSE_SENTINEL + bytes([1, 8]) + b"10110001"
            framework.write_bytes(wire + wire)
            executable = contents / "MacOS/Untapped.gg Companion"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"executable")
            pins = {
                "ASAR_SHA256": sha256(blob), "VERSION": "synthetic",
                "SCRY_SHA256": sha256(b"native"),
                "FRAMEWORK_SHA256": sha256(wire + wire),
                "EXECUTABLE_SHA256": sha256(b"executable"),
            }
            with mock.patch.multiple(cli, **pins), \
                    mock.patch.object(cli, "patched_entries", return_value={}), \
                    mock.patch.object(cli.platform, "system", return_value="Linux"):
                self.assertEqual(cli.inspect_app(app)[0]["electron_fuses"][0]["wire"], "10110001")
                native.write_bytes(b"tampered")
                with self.assertRaisesRegex(HarnessError, "Native reader or Electron binary"):
                    cli.inspect_app(app)
                native.write_bytes(b"native")
                framework.write_bytes(wire + wire[:-1] + b"0")
                with self.assertRaisesRegex(HarnessError, "Native reader or Electron binary"):
                    cli.inspect_app(app)


class BootstrapTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for bootstrap execution test")
    def test_bootstrap_redirects_paths_and_keeps_credentials_and_events_in_memory(self):
        code = textwrap.dedent(r"""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const path = require('node:path');
            const vm = require('node:vm');
            const source = fs.readFileSync(process.argv[1], 'utf8');
            const profile = '/private/tmp/synthetic-profile';
            const lines = [];
            const created = [];
            let nativeKeytarLoads = 0;
            function boot() {
              const paths = {};
              const moduleStub = { _load: (name) => {
                if (name === 'keytar') nativeKeytarLoads++;
                return { name };
              }};
              const electron = {
                app: {
                  setPath: (name, destination) => { paths[name] = destination; },
                  whenReady: () => Promise.resolve(),
                  setLoginItemSettings: () => { throw Error('not blocked'); },
                  setAsDefaultProtocolClient: () => { throw Error('not blocked'); },
                },
                shell: { openExternal: () => { throw Error('not blocked'); } },
              };
              const fsStub = {
                mkdirSync: (destination) => created.push(destination),
                appendFileSync: (destination, content) => {
                  assert.equal(destination, path.join(profile, 'events.jsonl'));
                  lines.push(JSON.parse(content));
                },
              };
              const requireStub = (name) => ({
                'node:fs': fsStub, 'node:path': path, 'node:module': moduleStub,
                electron,
              })[name];
              const globals = {};
              vm.runInNewContext(source, {
                require: requireStub, process: {
                  env: { UC_TEST_SANDBOX_DIR: profile, UNTAPPED_HARNESS_OFFLINE: '1' },
                }, global: globals,
              });
              return { paths, moduleStub, electron, globals };
            }
            (async () => {
              const first = boot();
              await Promise.resolve();
              assert.equal(first.paths.home, profile);
              assert.equal(first.paths.userData, profile);
              assert.equal(first.paths.temp, path.join(profile, 'temp'));
              assert.equal(Object.keys(first.paths).length, 7);
              assert.equal(created.length, 7);
              assert.equal(first.electron.app.setAsDefaultProtocolClient(), false);
              assert.equal(first.electron.app.setLoginItemSettings(), undefined);
              await assert.rejects(first.electron.shell.openExternal('https://example.invalid'));
              const keytar = first.moduleStub._load('keytar');
              assert.equal(nativeKeytarLoads, 0);
              assert.equal(await keytar.getPassword('service', 'person'), null);
              await keytar.setPassword('service', 'person', 'secret');
              assert.equal(await keytar.getPassword('service', 'person'), 'secret');
              assert.deepEqual(Array.from(await keytar.findCredentials('service')), []);
              first.globals.__untappedHarnessEvent('ready');
              first.globals.__untappedHarnessEvent('unapproved-event');
              first.globals.__untappedHarnessEvent('reader-connected');
              first.globals.__untappedHarnessEvent('reader-connected');
              const allCards = Array.from({ length: 22 }, (_, i) => ({
                id: 'ID' + i, upgradeLevel: 0, cx: 0.2, cy: 0.5,
                width: 0.1, height: 0.2, accountToken: 'must not appear',
              }));
              first.globals.__untappedHarnessReward({ source: 'merchant', cards: allCards });
              for (let i = 0; i < 101; i++) {
                first.globals.__untappedHarnessReward({ source: 'cardReward', cards: allCards });
              }
              assert.equal(lines.filter((event) => event.event === 'reward').length, 100);
              assert.equal(lines.find((event) => event.event === 'reward').cards.length, 20);
              assert.equal(lines.some((event) => event.event === 'unapproved-event'), false);
              assert.equal(lines.filter((event) => event.event === 'reader-connected').length, 1);
              assert.equal(JSON.stringify(lines).includes('must not appear'), false);
              const second = boot();
              assert.equal(await second.moduleStub._load('keytar').getPassword('service', 'person'), null);
              assert.equal(nativeKeytarLoads, 0);
            })().catch((error) => { console.error(error); process.exitCode = 1; });
        """)
        result = subprocess.run(
            [shutil.which("node"), "-e", code, str(Path(cli.__file__).with_name("bootstrap.cjs"))],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "Source.app"
        asar = self.app / "Contents/Resources/app.asar"
        asar.parent.mkdir(parents=True)
        self.original_blob = synthetic_archive()
        asar.write_bytes(self.original_blob)
        self.session = self.root / "new-session"

    def test_prepare_changes_only_disposable_copy(self):
        archive = Archive(self.original_blob)
        with mock.patch.object(cli, "inspect_app", return_value=({"companion_version": "synthetic"}, archive, {})), \
                mock.patch.object(cli, "patched_entries", return_value={"a.txt": b"patched"}), \
                mock.patch.object(cli.platform, "system", return_value="Linux"):
            report = cli.prepare(self.app, self.session)
        source_blob = (self.app / "Contents/Resources/app.asar").read_bytes()
        copy_blob = (self.session / "Companion.app/Contents/Resources/app.asar").read_bytes()
        self.assertEqual(source_blob, self.original_blob)
        self.assertEqual(Archive(copy_blob).read("a.txt"), b"patched")
        self.assertEqual(Archive(copy_blob).read("nested/b.txt"), b"second")
        self.assertEqual(report["patched_asar_sha256"], sha256(copy_blob))
        self.assertEqual(json.loads((self.session / "manifest.json").read_text())["game_modified"], False)
        self.assertTrue((self.session / "profile").is_dir())

    def test_existing_session_is_rejected_before_copy(self):
        self.session.mkdir()
        with self.assertRaisesRegex(HarnessError, "must be new"):
            cli.prepare(self.app, self.session)
        self.assertEqual((self.app / "Contents/Resources/app.asar").read_bytes(), self.original_blob)

    def test_repository_session_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=cli.ROOT) as local:
            with self.assertRaisesRegex(HarnessError, "outside the repository"):
                cli.prepare(self.app, Path(local) / "session")

    def test_source_signature_failure_prevents_copy(self):
        archive = Archive(self.original_blob)
        with mock.patch.object(cli, "inspect_app", return_value=({"source_signature_valid": False}, archive, {})), \
                mock.patch.object(cli.platform, "system", return_value="Darwin"):
            with self.assertRaisesRegex(HarnessError, "signature is invalid"):
                cli.prepare(self.app, self.session)
        self.assertFalse(self.session.exists())


class IsolationTests(unittest.TestCase):
    def test_launch_environment_drops_inherited_credentials_and_overrides(self):
        session = Path("/private/tmp/harness-fixture")
        with mock.patch.dict(os.environ, {
            "SUDO_USER": "another-user", "NODE_OPTIONS": "--require=bad.js",
            "UC_TEST_API_BASE_URL": "https://example.invalid", "AWS_SECRET_ACCESS_KEY": "secret",
        }):
            environment = cli.launch_environment(session)
        for key in ("SUDO_USER", "NODE_OPTIONS", "UC_TEST_API_BASE_URL", "AWS_SECRET_ACCESS_KEY", "HOME"):
            self.assertNotIn(key, environment)
        self.assertEqual(environment["UC_TEST_SANDBOX_DIR"], str(session / "profile"))
        self.assertEqual(environment["UNTAPPED_HARNESS_OFFLINE"], "1")
        self.assertEqual(environment["NODE_ENV"], "production")

    def test_policy_limits_network_keychain_and_real_home_access(self):
        session = Path("/private/tmp/harness-fixture")
        home = Path("/Users/person")
        policy = cli.sandbox_profile(session, home)
        self.assertIn("(deny network*)", policy)
        self.assertIn("(deny file-write*)", policy)
        self.assertIn('(deny file-read* (subpath "/Users/person"))', policy)
        self.assertIn('(allow file-read* file-write* (subpath "/private/tmp/harness-fixture"))', policy)
        self.assertIn("com.apple.securityd", policy)
        self.assertNotIn("example.invalid", policy)


class RewardTests(unittest.TestCase):
    def test_ordered_reward_matches_only_when_ids_upgrades_positions_match(self):
        actual = reward_events()
        expected = {"cards": [card("B", 0.705, 1), card("A", 0.295)]}
        result = cli.compare_reward(actual, expected, 0)
        self.assertTrue(result["matches"])
        self.assertEqual(result["overlay"], "UNTESTED_REQUIRES_VISUAL_CHECK")
        self.assertEqual(result["recommendations"], "UNTESTED")

    def test_each_meaningful_mismatch_fails(self):
        cases = {
            "id": [card("WRONG", 0.3), card("B", 0.7, 1)],
            "upgrade": [card("A", 0.3, 1), card("B", 0.7, 1)],
            "position": [card("A", 0.4), card("B", 0.7, 1)],
            "count": [card("A", 0.3)],
        }
        for name, cards in cases.items():
            with self.subTest(name=name):
                self.assertFalse(cli.compare_reward(reward_events(), {"cards": cards}, 0)["matches"])

    def test_missing_connection_evidence_is_not_a_reward_success(self):
        events = [event for event in reward_events() if event["event"] != "reader-connected"]
        with self.assertRaisesRegex(HarnessError, "preceding"):
            cli.compare_reward(events, {"cards": [card("A", 0.3), card("B", 0.7, 1)]}, 0)
        with self.assertRaisesRegex(HarnessError, "No reward"):
            cli.compare_reward(reward_events(), {"cards": [card("A", 0.3)]}, 1)

    def test_invalid_geometry_and_upgrade_cannot_be_verified(self):
        invalid = [
            {**card("A", 0.3), "cx": float("nan")},
            {**card("A", 0.3), "width": 0},
            {**card("A", 0.3), "upgradeLevel": True},
            {**card("A", 0.3), "cy": 1.2},
        ]
        for entry in invalid:
            with self.subTest(entry=entry), self.assertRaises(HarnessError):
                cli.compare_reward(reward_events(), {"cards": [entry]}, 0)


if __name__ == "__main__":
    unittest.main()
