"""Exercise explicit reviewed-build copy and signing with a synthetic app."""

import json
import os
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from harness import game_builds, game_debug, game_launch
from harness.asar import HarnessError
from harness.game_builds import V0_111_1 as PINNED_V0_111_1


class ReviewedBuildTests(unittest.TestCase):
    def setUp(self):
        if os.getuid() == 0:
            self.skipTest("Copied-game signing refuses root")
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / 'Original.app'
        self.session = self.root / 'new-game'
        self.write(game_launch.ASSEMBLY, b'new reviewed assembly')
        self.write(game_launch.EXECUTABLE, b'original executable')
        self.write('Contents/_CodeSignature/CodeResources', b'original seal')
        self.write('Contents/Resources/release_info.json', json.dumps({
            'version': 'v0.111.1', 'commit': 'cc1f9462'}).encode())
        self.write('Contents/Resources/unchanged.dat', b'unchanged')
        self.build = game_builds.GameBuild('v0.111.1', 'cc1f9462',
            game_launch.digest(self.source / game_launch.ASSEMBLY),
            game_debug._tree_hash(game_launch.tree_manifest(self.source)))
        patches = (
            patch.object(game_builds, 'V0_111_1', self.build),
            patch.object(game_debug.platform, 'system', return_value='Darwin'),
            patch.object(game_launch.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stderr='')),
            patch.object(game_debug, '_settings'),
        )
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def write(self, name, data):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def sign_copy(self):
        def sign(command):
            self.assertEqual(command[:4], ['/usr/bin/codesign', '--force', '--sign', '-'])
            app = self.session / game_debug.APP
            (app / game_launch.EXECUTABLE).write_bytes(b'signed executable')
            (app / 'Contents/_CodeSignature/CodeResources').write_bytes(b'signed seal')
        with patch.object(game_debug, '_command', side_effect=sign):
            return game_debug.sign(self.session, approved=True, build=self.build)

    def test_v0111_pin_is_exact_and_immutable(self):
        build = PINNED_V0_111_1
        self.assertEqual((build.version, build.commit), ('v0.111.1', 'cc1f9462'))
        self.assertEqual(build.assembly_sha256,
            '0dba5816282c6483d9305032acbe1a9be1e5e31b505421834ef7d1e786c19abf')
        self.assertEqual(build.tree_sha256,
            'fa13254041eb414bef4bceba413fe23aff3e0a4dbee9a86da8cb5840aeb34be4')
        with self.assertRaises(FrozenInstanceError):
            build.version = 'v0.999'

    def test_prepare_sign_verify_uses_new_build_and_keeps_outer_signing_scope(self):
        with self.assertRaisesRegex(HarnessError, 'Unsupported game build'):
            game_launch.verified_app(self.source)
        proposal = game_debug.prepare(self.source, self.session, build=self.build)
        manifest = json.loads((self.session / game_debug.BASE).read_text())
        self.assertEqual((manifest['game_version'], manifest['commit'], manifest['source_tree_sha256']),
            (self.build.version, self.build.commit, self.build.tree_sha256))
        self.assertEqual(proposal['allowed_changed_files'], sorted(game_debug.SIGNING_FILES))
        with self.assertRaisesRegex(HarnessError, 'approval'):
            game_debug.sign(self.session, build=self.build)
        receipt = self.sign_copy()
        self.assertEqual(receipt['changed_files'], sorted(game_debug.SIGNING_FILES))
        self.assertEqual(game_debug.verify(self.session, build=self.build), receipt['signed_files'])
        with self.assertRaisesRegex(HarnessError, 'pinned original build'):
            game_debug.verify(self.session)

    def test_rejects_changed_release_assembly_and_complete_tree(self):
        for name, contents in (
            ('Contents/Resources/release_info.json', b'{"version":"v0.111.1","commit":"wrong"}'),
            (game_launch.ASSEMBLY, b'changed assembly'),
            ('Contents/Resources/unchanged.dat', b'changed resource'),
        ):
            with self.subTest(name=name):
                target = self.source / name
                original = target.read_bytes()
                target.write_bytes(contents)
                try:
                    with self.assertRaises(HarnessError):
                        game_debug.prepare(self.source, self.session, build=self.build)
                    self.assertFalse(self.session.exists())
                finally:
                    target.write_bytes(original)

    def test_rejects_unreviewed_build_and_signed_copy_mutation(self):
        unreviewed = game_builds.GameBuild(self.build.version, self.build.commit,
                                           self.build.assembly_sha256, '0' * 64)
        with self.assertRaisesRegex(HarnessError, 'Unreviewed game build'):
            game_debug.prepare(self.source, self.session, build=unreviewed)
        game_debug.prepare(self.source, self.session, build=self.build)
        self.sign_copy()
        (self.session / game_debug.APP / 'Contents/Resources/unchanged.dat').write_bytes(b'mutated')
        with self.assertRaisesRegex(HarnessError, 'changed after receipt'):
            game_debug.verify(self.session, build=self.build)

    def test_explicit_build_still_requires_signature_and_exact_entitlements(self):
        with patch.object(game_launch.subprocess, 'run',
                          return_value=SimpleNamespace(returncode=1, stderr='invalid signature')):
            with self.assertRaisesRegex(HarnessError, 'signature verification failed'):
                game_debug.prepare(self.source, self.session, build=self.build)
        self.assertFalse(self.session.exists())
        with patch.object(game_debug, '_settings', side_effect=HarnessError('entitlements changed')):
            with self.assertRaisesRegex(HarnessError, 'entitlements changed'):
                game_debug.prepare(self.source, self.session, build=self.build)
        self.assertFalse(self.session.exists())


if __name__ == '__main__':
    unittest.main()
