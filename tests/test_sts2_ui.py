"""Synthetic checks for the pinned STS2 settings menu edit."""

import json
import shutil
import subprocess
import unittest

from harness.asar import HarnessError
from harness.sts2_ui import SETTINGS_UI_ENTRY, UI_NEW, UI_OLD, patch_settings_ui


OTHER_MENU = '''    content: OtherSettings,
    platforms: ["win32", "linux"],
    requireLogin: {
      franchise: "OTHER"
    },'''

SOURCE = '''const Sts2Settings = "sts2";
const OtherSettings = "other";
const menu = [
  {
    id: "sts2-settings",
''' + UI_OLD + '''
    packagedOnly: true
  },
  {
    id: "other-settings",
''' + OTHER_MENU + '''
    packagedOnly: true
  },
  {
    id: "common",
    content: "common",
    platforms: ["win32", "linux", "darwin"],
    packagedOnly: true
  },
  {
    id: "dev-only",
    content: "dev",
    platforms: ["darwin"],
    packagedOnly: false
  }
];
const visible = menu.filter(item =>
  item.platforms.includes(process.platform) &&
  (item.packagedOnly !== false || !app.metadata.isPackaged) &&
  (!item.requireLogin || loggedIn[item.requireLogin.franchise])
).map(item => item.id);
visible;
'''


class SettingsUiPatchTests(unittest.TestCase):
    def test_exact_single_literal_edit_preserves_other_menu_and_filters(self):
        self.assertEqual(SETTINGS_UI_ENTRY, "dist/renderer/assets/Main-DlHDXYoX.js")
        patched = patch_settings_ui(SOURCE)
        self.assertEqual(patched, SOURCE.replace(UI_OLD, UI_NEW, 1))
        self.assertEqual(patched.count(OTHER_MENU), 1)
        self.assertEqual(patched.count('requireLogin: {\n      franchise: "STS2"'), 1)
        self.assertEqual(patched.count("app.metadata.isPackaged"), 1)
        self.assertEqual(patched.count("menu.filter(item =>"), 1)

    def test_missing_duplicate_and_wrong_context_refused(self):
        wrong_contexts = (
            SOURCE.replace("content: Sts2Settings", "content: OtherSettings"),
            SOURCE.replace('franchise: "STS2"', 'franchise: "OTHER"'),
            SOURCE.replace('platforms: ["win32", "linux"]',
                           'platforms: ["linux", "win32"]', 1),
        )
        for source in ("", SOURCE + SOURCE, *wrong_contexts):
            with self.subTest(source=source[:50]), self.assertRaises(HarnessError):
                patch_settings_ui(source)

    @unittest.skipUnless(shutil.which("node"), "Node is required for synthetic menu behavior")
    def test_packaged_platform_filter_changes_only_sts2_on_darwin(self):
        script = '''const vm = require("node:vm");
const [source, platform, packaged, sts2LoggedIn] = JSON.parse(process.argv[1]);
const context = {
  process: { platform },
  app: { metadata: { isPackaged: packaged } },
  loggedIn: { STS2: sts2LoggedIn, OTHER: true }
};
console.log(JSON.stringify(vm.runInNewContext(source, context)));
'''

        def visible(source, platform, packaged=True, logged_in=True):
            result = subprocess.run(
                [shutil.which("node"), "-e", script,
                 json.dumps([source, platform, packaged, logged_in])],
                capture_output=True, text=True, check=True,
            )
            return json.loads(result.stdout)

        patched = patch_settings_ui(SOURCE)
        self.assertEqual(visible(SOURCE, "darwin"), ["common"])
        self.assertEqual(visible(patched, "darwin"), ["sts2-settings", "common"])
        for platform in ("win32", "linux"):
            with self.subTest(platform=platform):
                expected = ["sts2-settings", "other-settings", "common"]
                self.assertEqual(visible(SOURCE, platform), expected)
                self.assertEqual(visible(patched, platform), expected)
        self.assertEqual(visible(patched, "darwin", logged_in=False), ["common"])
        self.assertEqual(visible(patched, "darwin", packaged=False),
                         ["sts2-settings", "common", "dev-only"])


if __name__ == "__main__":
    unittest.main()
