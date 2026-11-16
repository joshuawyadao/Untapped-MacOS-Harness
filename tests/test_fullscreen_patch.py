"""Execute the patched native-window options using an inert Electron boundary."""
import json
import shutil
import subprocess
import unittest

from harness.asar import HarnessError
from harness import fullscreen_patch, patches


SOURCE = '''class Overlay {
  constructor(routerPath) { this.routerPath = routerPath; }
  create() {
    const window = Services.createWindow(`/overlay/${this.routerPath}`, {
      title: "Untapped.gg Overlay",
      frame: false,
      transparent: true,
      alwaysOnTop: true,
      show: false,
      focusable: true,
      fullscreenable: false,
      webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true }
    });
    if (process.platform === "darwin") {
      window.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    }
    window.setIgnoreMouseEvents(true, { forward: true });
    return window;
  }
}
new Overlay(route).create();
'''


class FullscreenPatchTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for native option behavior')
    def test_actual_constructor_patch_changes_only_darwin_sts2(self):
        script = '''const vm = require('node:vm');
const [source, platform, route] = JSON.parse(process.argv[1]);
const calls = [];
const context = { process: { platform }, route,
  Services: { createWindow: (url, options) => ({url, options,
    setVisibleOnAllWorkspaces: (...args) => calls.push(['workspaces', ...args]),
    setIgnoreMouseEvents: (...args) => calls.push(['ignore', ...args])}) }
};
const win = vm.runInNewContext(source, context);
console.log(JSON.stringify({url:win.url, options:win.options, calls}));
'''

        def create(source, platform, route):
            result = subprocess.run([shutil.which('node'), '-e', script,
                                     json.dumps([source, platform, route])],
                                    capture_output=True, text=True, check=True, timeout=10)
            return json.loads(result.stdout)

        patched = fullscreen_patch.patch_core(SOURCE)
        for platform in ('darwin', 'win32', 'linux'):
            for route in ('sts2', 'mtga', 'snap'):
                with self.subTest(platform=platform, route=route):
                    before = create(SOURCE, platform, route)
                    expected = create(SOURCE, platform, route)
                    if platform == 'darwin' and route == 'sts2':
                        expected['options']['type'] = 'panel'
                    self.assertEqual(create(patched, platform, route), expected)
                    self.assertEqual(before['options']['webPreferences'],
                                     {'nodeIntegration': False, 'contextIsolation': True, 'sandbox': True})
                    self.assertEqual(expected['calls'][-1], ['ignore', True, {'forward': True}])

    def test_missing_duplicate_and_already_patched_anchors_fail_closed(self):
        for source in ('', SOURCE + SOURCE,
                       SOURCE.replace('title: "Untapped.gg Overlay"', 'title: "Other"'),
                       SOURCE.replace('frame: false', 'frame: true')):
            with self.subTest(source=source[:40]), self.assertRaises(HarnessError):
                fullscreen_patch.patch_core(source)
        with self.assertRaises(HarnessError):
            fullscreen_patch.patch_core(fullscreen_patch.patch_core(SOURCE))

    def test_fresh_preparation_uses_the_same_single_option_patch(self):
        self.assertIn((fullscreen_patch.WINDOW_OLD, fullscreen_patch.WINDOW_NEW), patches.CORE_PATCHES)
        self.assertEqual(fullscreen_patch.patch_core(SOURCE),
                         SOURCE.replace(fullscreen_patch.WINDOW_OLD, fullscreen_patch.WINDOW_NEW, 1))
