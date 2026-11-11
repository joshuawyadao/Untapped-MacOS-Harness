"""Offline checks for publishing the native launcher and its source snapshot."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from harness import desktop_install
from harness.asar import HarnessError


class DesktopInstallTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.repo = self.root / 'source'
        harness = self.repo / 'harness'
        harness.mkdir(parents=True)
        self.sources = {
            '__init__.py': b'package = True\n',
            'desktop_launcher.py': b'worker = True\n',
            'helper.c': b'int helper(void) { return 1; }\n',
            'bridge.cjs': b'module.exports = 1;\n',
        }
        for name, content in self.sources.items():
            (harness / name).write_bytes(content)
        (harness / 'notes.txt').write_text('not a runtime source')
        launcher = self.repo / 'launcher'
        launcher.mkdir()
        (launcher / 'Launcher.swift').write_text('import Cocoa\n')
        (launcher / 'LauncherOutcome.swift').write_text('enum LauncherOutcome {}\n')

        self.game = self.root / 'prepared' / 'game' / 'SlayTheSpire2.app' / 'Contents'
        (self.game / 'Resources').mkdir(parents=True)
        (self.game / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleIconFile': 'GameIcon'}))
        (self.game / 'Resources' / 'GameIcon.icns').write_bytes(b'local icon')
        self.destination = self.root / 'Applications' / desktop_install.NAME
        self.destination.parent.mkdir()

    def build(self, run):
        with patch.object(desktop_install, 'REPO', self.repo), \
             patch.object(desktop_install.main_launcher, '_prepared',
                          return_value=(self.game.parents[2], None, None)), \
             patch.object(desktop_install.ui_update, 'selected_session') as selected, \
             patch.object(desktop_install.subprocess, 'run', side_effect=run) as commands:
            result = desktop_install.build(self.destination)
        selected.assert_called_once_with(self.game.parents[2])
        return result, commands

    @staticmethod
    def fake_commands(command, **kwargs):
        assert kwargs['check'] is True
        if command[0] == '/usr/bin/swiftc':
            Path(command[command.index('-o') + 1]).write_bytes(b'native executable')
        return subprocess.CompletedProcess(command, 0)

    def test_build_publishes_complete_private_runtime_snapshot(self):
        result, commands = self.build(self.fake_commands)
        app = self.destination
        runtime = app / 'Contents/Resources/runtime/harness'
        self.assertEqual({p.name: p.read_bytes() for p in runtime.iterdir()}, self.sources)
        self.assertEqual(result, {'installed_app': str(app), 'runtime_files': len(self.sources),
                                  'launches_game_during_install': False})
        self.assertEqual((app / 'Contents/Resources/Launcher.icns').read_bytes(), b'local icon')
        info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
        self.assertEqual(info['CFBundleIconFile'], 'Launcher.icns')
        config = json.loads((app / 'Contents/Resources/config.json').read_text())
        self.assertEqual(config, {'python': str(Path(os.sys.executable).resolve(strict=True))})
        executable = app / 'Contents/MacOS/STS2Launcher'
        self.assertEqual(executable.read_bytes(), b'native executable')
        self.assertEqual(executable.stat().st_mode & 0o777, 0o700)
        self.assertEqual(runtime.stat().st_mode & 0o777, 0o700)
        self.assertEqual((runtime / '__init__.py').stat().st_mode & 0o777, 0o600)
        compile_command = commands.call_args_list[0].args[0]
        self.assertIn(str(self.repo / 'launcher/Launcher.swift'), compile_command)
        self.assertIn(str(self.repo / 'launcher/LauncherOutcome.swift'), compile_command)
        self.assertEqual([call.args[0][:2] for call in commands.call_args_list[1:]],
                         [['/usr/bin/codesign', '--force'], ['/usr/bin/codesign', '--verify']])

        # Editing the checkout after installation must not change the published copy.
        (self.repo / 'harness/__init__.py').write_bytes(b'changed\n')
        self.assertEqual((runtime / '__init__.py').read_bytes(), self.sources['__init__.py'])

    def test_compile_and_signature_failures_leave_destination_absent(self):
        for failing_command in ('/usr/bin/swiftc', '--force', '--verify'):
            with self.subTest(failing_command=failing_command):
                destination = self.root / 'Applications' / (failing_command.strip('-/').replace('/', '-') + '.app')
                self.destination = destination

                def fail_at(command, **kwargs):
                    if failing_command in command:
                        raise subprocess.CalledProcessError(1, command)
                    return self.fake_commands(command, **kwargs)

                with self.assertRaises(subprocess.CalledProcessError):
                    self.build(fail_at)
                self.assertFalse(destination.exists())

    def test_existing_destination_is_preserved_before_build_steps(self):
        self.destination.mkdir()
        marker = self.destination / 'existing.txt'
        marker.write_bytes(b'keep existing app')
        with patch.object(desktop_install, 'REPO', self.repo), \
             patch.object(desktop_install.main_launcher, '_prepared',
                          return_value=(self.game.parents[2], None, None)), \
             patch.object(desktop_install.ui_update, 'selected_session') as selected, \
             patch.object(desktop_install.subprocess, 'run') as commands:
            with self.assertRaisesRegex(HarnessError, 'already exists'):
                desktop_install.build(self.destination)
        self.assertEqual(marker.read_bytes(), b'keep existing app')
        commands.assert_not_called()
        selected.assert_called_once()


if __name__ == '__main__':
    unittest.main()
